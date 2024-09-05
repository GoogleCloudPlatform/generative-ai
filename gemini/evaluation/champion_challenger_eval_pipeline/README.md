# [GenOps](https://cloud.google.com/blog/products/devops-sre/genops-learnings-from-microservices-and-traditional-devops?e=48754805) Champion Challenger Pipelines 

Leverage Vertex AI pipeline and [Auto SxS](https://cloud.google.com/vertex-ai/generative-ai/docs/models/side-by-side-eval) to automate the process of evaluating and deploying new challenger candidate models against an existing GenAI champion model, ensuring a controlled and efficient model update GenOps CI/CD workflow. 

## Key Benefits:

- Controlled Model Deployment: Reduces risks associated with model updates by automating the evaluation and deployment process.
- Model Version Control & Lineage Tracking: Maintains a clear history of model versions and their performance. Enables rollback to previous model versions if needed.
- Vertex Pipelines Integration: Provides a visual representation of the workflow, facilitating monitoring and troubleshooting.
- Automation with Cloud Trigger: Eliminates manual intervention and allows for frequent, efficient model updates.
- Introduce HITL: Add a HITL component for human supervised model deployment

Google Cloud Services Used: Cloud Build, Vertex Pipelines, Auto SxS, Google Cloud Storage, BigQuery 

## Workflow:
- Prompt & Parameter Config: Prompt templates (including system instructions) along with model parameters are tracked in a 'config.json' file in a GCS bucket which can be used by dependant apps and also tracks model config.
- Evaluation Dataset: The ground truth eval dataset is stored in BigQuery, serving as the ground truth for comparing current champion and challenger model predictions.
- Vertex Pipeline orchestrates Kubeflow components to retrieve the champion/ challenger model configs from GCS bucket, run current and champion LLM responses against BQ ground truth dataset for Auto SxS to evaluate the champion and challenger responses 
- Auto SxS wrapped Kubeflow Pipeline step: Judges champion model and challenger model responses against Input Instructions and creates judgement metrics and summary metrics with corresponding win rates for models.
- DSL Control Flow: Checks if the candidate challenger model win rate is greater than current champion model then:
- Before promoting the challenger model config, the champion model config is version controlled and then updated with winning model config params 
- Cloud Build: Configure the Vertex Pipeline with Cloud Build
- Trigger Champion Challenger Vertex Pipeline with ([Git triggers](https://cloud.google.com/build/docs/triggers#github)) or trigger manually with

Run following in terminal/ [add triggers](https://cloud.google.com/build/docs/triggers):
- `!gcloud builds submit evaluation_pipelines --config=genops_champion_challenger_eval_pipeline/pipelinebuild.yaml` 

- Add GCS [Pub Sub triggers](https://cloud.google.com/build/docs/automate-builds-pubsub-events#gcs_build_trigger) so that whenever challenger model config is updated, associated cloud build trigger can kickstart evaluation pipeline to evaluate whether the new candidate model is better and if champion model needs updating 

### Champion Challenger Pipeline

![# Chamion Challenger - evaluation pipelines](images/champion-challenger-eval.gif)


### Pre-Requisites / Background

This champion challenger pipeline is built in context of a Summarisation app.

Current champion model for summarisation leverages `gemini_1.5_pro` and the config parameters is stored in `summarization.json` with following schema: 
```
 {
    "model": "MODEL_NAME",
    "system_instruction": "Your system isntructions. ",
    "prompt_template": "Prompt template",
    "temperature": TEMPERATURE,
    "max_output_tokens": OUTPUT_TOKENS,
    "top_p": TOP_P
}
```

After further exploration, if data scientists make a new  `challenger_summarization.json` file available in the GCS Bucket, the  config params for candidate models also follow the above schema; the above pipeline can be triggered.

You can use the following ddl to create BQ schema pipeline expects:

-- Ground Truth Dataset table summarizer_data containing raw text articles and golden summaries

CREATE TABLE `{YOUR_PROJECT_ID}.summarizer_data`
(
  id INT64,
  article STRING,
  golden_summary STRING
);

-- Champion model response against summarizer_data articles

CREATE TABLE `genops.summarizer_champion_model`
(
  id INT64,
  prompt STRING,
  model_summary STRING
);

-- Challenger model response against summarizer_data articles

CREATE TABLE `{YOUR_PROJECT_ID}.genops.summarizer_challenger_model`
(
  id INT64,
  prompt STRING,
  model_summary STRING
);

-- Champion Challenger response evaluation set for AutoSxS pipelines

CREATE TABLE `{YOUR_PROJECT_ID}.summarizer_champion_challenger_eval`
(
  id INT64,
  article STRING,
  current_model_summary STRING,
  challenger_model_summary STRING
);