package com.cpet.fixmycarbackend;

import com.google.cloud.discoveryengine.v1.SearchRequest;
import com.google.cloud.discoveryengine.v1.SearchResponse;
import com.google.cloud.discoveryengine.v1.SearchResponse.SearchResult;
import com.google.cloud.discoveryengine.v1.SearchServiceClient;
import com.google.cloud.discoveryengine.v1.SearchServiceSettings;
import com.google.cloud.discoveryengine.v1.ServingConfigName;
import com.google.cloud.vertexai.VertexAI;
import com.google.cloud.vertexai.api.GenerateContentResponse;
import com.google.cloud.vertexai.generativeai.ChatSession;
import com.google.cloud.vertexai.generativeai.GenerativeModel;
import com.google.cloud.vertexai.generativeai.ResponseHandler;
import com.google.protobuf.ListValue;
import com.google.protobuf.Struct;
import com.google.protobuf.Value;
import java.util.List;
import java.util.Map;
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

  @Autowired
  private FixMyCarConfiguration config;
  private String projectId;
  private String datastoreId;

  // Get config values from application.properties
  @PostConstruct
  public void init() {
    projectId = config.getProjectId();
    datastoreId = config.getVertexDataStoreId();
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

  // Chat Endpoint - uses one of two helper functions based on vector DB choice
  @PostMapping(value = "/chat", consumes = "application/json", produces = "application/json")
  public ChatMessage message(@RequestBody ChatMessage message) {
    return ragVertexAISearch(message);
  }

  public ChatMessage ragVertexAISearch(ChatMessage message) {
    // ⭐ Step 1 - Search
    logger.info("⭐ project Id: " + projectId);
    String location = "global";
    String collectionId = "default_collection";
    logger.info("⭐ Datastore ID is: " + datastoreId);
    String servingConfigId = "default_search";
    String searchQuery = message.getPrompt();
    logger.info("⭐ Datastore query: " + searchQuery);
    // Note - discoveryengine is the underlying API for Vertex AI Agent Builder
    String endpoint = String.format("discoveryengine.googleapis.com:443", location);
    String vectorSearchResults = "";
    try {
      SearchServiceSettings settings = SearchServiceSettings.newBuilder().setEndpoint(endpoint).build();
      SearchServiceClient searchServiceClient = SearchServiceClient.create(settings);
      SearchRequest request = SearchRequest.newBuilder()
          .setServingConfig(
              ServingConfigName.formatProjectLocationCollectionDataStoreServingConfigName(
                  projectId, location, collectionId, datastoreId, servingConfigId))
          .setQuery(searchQuery)
          .setPageSize(10)
          .build();
      SearchResponse response = searchServiceClient.search(request).getPage().getResponse();
      // Note - the Vertex AI Agent Builder API response is tricky to parse because
      // it's a
      // proto-based object (not JSON / REST response)
      List<SearchResult> resultsList = response.getResultsList();
      logger.info("🔍 Found " + resultsList.size() + " results.");
      for (SearchResponse.SearchResult element : resultsList) {
        Struct derivedStructData = element.getDocument().getDerivedStructData();
        Map<String, Value> fields = derivedStructData.getFieldsMap();
        Value extractiveAnswersValue = fields.get("extractive_answers");
        ListValue listValue = extractiveAnswersValue.getListValue();
        Value firstValue = listValue.getValues(0);
        Struct structValue = firstValue.getStructValue();
        Map<String, Value> innerFields = structValue.getFieldsMap();
        Value contentValue = innerFields.get("content");
        String stringValue = contentValue.getStringValue();
        vectorSearchResults += stringValue;
      }
    } catch (Exception e) {
      logger.error("⚠️ Vertex AI Agent Builder Error: " + e);
    }

    // ⭐ Step 2 - Inference w/ augmented prompt
    logger.info("🔍 Vertex AI Agent Builder results: " + vectorSearchResults);
    String result = geminiInference(message.getPrompt(), vectorSearchResults);
    message.setResponse(result);
    return message;
  }

  // Helper function - calls Gemini to generate a response based on the augmented
  // user prompt.
  public String geminiInference(String userPrompt, String vectorSearchResults) {
    String geminiPrompt = "You are a helpful car manual chatbot. Answer the car owner's question about their car."
        + " Human prompt: "
        + userPrompt
        + ",\n"
        + " Use the following grounding data as context. This came from the relevant vehicle"
        + " owner's manual: "
        + vectorSearchResults;
    logger.info("🔮 Gemini Prompt: " + geminiPrompt);

    String geminiLocation = "us-central1";
    String modelName = "gemini-1.5-flash-001";
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
