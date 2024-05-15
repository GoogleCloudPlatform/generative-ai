package com.cpet.fixmycarbackend;

import com.google.cloud.aiplatform.util.ValueConverter;
import com.google.cloud.aiplatform.v1beta1.EndpointName;
import com.google.cloud.aiplatform.v1beta1.PredictResponse;
import com.google.cloud.aiplatform.v1beta1.PredictionServiceClient;
import com.google.cloud.aiplatform.v1beta1.PredictionServiceSettings;
import com.google.cloud.vertexai.VertexAI;
import com.google.cloud.vertexai.api.GenerateContentResponse;
import com.google.cloud.vertexai.generativeai.preview.ChatSession;
import com.google.cloud.vertexai.generativeai.preview.GenerativeModel;
import com.google.cloud.vertexai.generativeai.preview.ResponseHandler;
import com.google.protobuf.ListValue;
import com.google.protobuf.Struct;
import com.google.protobuf.Value;
import com.google.protobuf.util.JsonFormat;
import java.util.ArrayList;
import java.util.List;
import javax.annotation.PostConstruct;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class FixMyCarBackendController {
  private static final Logger logger = LoggerFactory.getLogger(FixMyCarBackendController.class);

  @Autowired private FixMyCarConfiguration config;
  private String projectId;

  // Get config values from application.properties
  @PostConstruct
  public void init() {
    projectId = config.getProjectId();
  }

  @GetMapping("/")
  public String index() {
    logger.info("🚗 GET /");
    return "Welcome to the FixMyCar Backend API!";
  }

  @GetMapping("/health")
  public String health() {
    logger.info("✅ GET /health");
    return "ok";
  }

  @Autowired private EmbeddingRowRepository embeddingRowRepository;

  // Chat Endpoint - uses one of two helper functions based on vector DB choice
  @PostMapping(value = "/chat", consumes = "application/json", produces = "application/json")
  public ChatMessage message(@RequestBody ChatMessage message) {
    return ragCloudSQL(message);
  }

  public ChatMessage ragCloudSQL(ChatMessage message) {
    // ⭐ Step 1 - Convert user's text prompt into embeddings
    List<Float> queryEmb = generatePromptEmbeddings(projectId, message.getPrompt());

    // ⭐ Step 2 - Vector Search (Cloud SQL) using vectorized user prompt as the
    // query
    String value = queryEmb.toString();
    logger.info("⭐ Query: " + value);
    final List<EmbeddingRow> items = embeddingRowRepository.findNearestNeighbors(value);
    String vectorSearchResults = "";
    logger.info("🔍 Found " + items.size() + " nearest neighbors");
    for (EmbeddingRow item : items) {
      logger.info("🔍 Neighbor: " + item.getText());
      vectorSearchResults += item.getText() + "\n";
    }

    // ⭐ Step 3 - Inference w/ augmented prompt
    String result = geminiInference(message.getPrompt(), vectorSearchResults);
    message.setResponse(result);
    return message;
  }

  // Helper function - Generate embeddings from the user's prompt in order to
  // perform vector search
  public List<Float> generatePromptEmbeddings(String projectId, String userPrompt) {
    String instance = "{ \"content\": \"" + userPrompt + "\" }";
    String location = "us-central1";
    String publisher = "google";
    // Note - you can update this to use any model version listed here:
    // https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/text-embeddings#model_versions
    String embModel = "textembedding-gecko@003";
    String endpoint = String.format("%s-aiplatform.googleapis.com:443", location);
    List<Float> queryEmb = new ArrayList<>();
    try {
      PredictionServiceSettings predictionServiceSettings =
          PredictionServiceSettings.newBuilder().setEndpoint(endpoint).build();
      PredictionServiceClient predictionServiceClient =
          PredictionServiceClient.create(predictionServiceSettings);
      EndpointName endpointName =
          EndpointName.ofProjectLocationPublisherModelName(
              projectId, location, publisher, embModel);
      Value.Builder instanceValue = Value.newBuilder();
      JsonFormat.parser().merge(instance, instanceValue);
      List<Value> instances = new ArrayList<>();
      instances.add(instanceValue.build());
      PredictResponse resp =
          predictionServiceClient.predict(endpointName, instances, ValueConverter.EMPTY_VALUE);

      // Process struct response to extract vectors
      List<Value> emb = resp.getPredictionsList();
      Struct embeddings = emb.get(0).getStructValue();
      Value embeddingsValue = embeddings.getFieldsOrThrow("embeddings");
      Struct innerStruct = embeddingsValue.getStructValue();
      Value valuesValue = innerStruct.getFieldsOrThrow("values");
      ListValue listValue = valuesValue.getListValue();
      for (Value v : listValue.getValuesList()) {
        queryEmb.add((float) v.getNumberValue());
      }
      logger.info("🤖 Generated prompt embeddings of length: " + queryEmb.size());

    } catch (Exception e) {
      logger.error("⚠️ Vertex AI Embeddings error: " + e);
    }
    return queryEmb;
  }

  // Helper function - calls Gemini to generate a response based on the augmented
  // user prompt.
  public String geminiInference(String userPrompt, String vectorSearchResults) {
    String geminiPrompt =
        "You are a helpful car manual chatbot. Answer the car owner's question about their car."
            + " Human prompt: "
            + userPrompt
            + ",\n"
            + " Use the following grounding data as context. This came from the relevant vehicle"
            + " owner's manual: "
            + vectorSearchResults;
    logger.info("🔮 Gemini Prompt: " + geminiPrompt);

    String geminiLocation = "us-central1";
    String modelName = "gemini-pro";
    try {
      VertexAI vertexAI = new VertexAI(projectId, geminiLocation);
      GenerateContentResponse response;
      GenerativeModel model = new GenerativeModel(modelName, vertexAI);
      ChatSession chatSession = new ChatSession(model);
      response = chatSession.sendMessage(geminiPrompt);
      String strResp = ResponseHandler.getText(response);
      logger.info("🔮 Gemini Response: " + strResp);
      return strResp;
    } catch (Exception e) {
      logger.error("⚠️ Gemini Error: " + e);
      return e.getMessage();
    }
  }
}
