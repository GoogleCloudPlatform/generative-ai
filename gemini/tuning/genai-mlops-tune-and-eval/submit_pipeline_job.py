from google.cloud import aiplatform

aiplatform.init(
    project="[your-project-id]", location="us-central1"
)  # Initialize the Vertex AI SDK

job = aiplatform.PipelineJob(
    display_name="tuned-gemini-2.0-flash",  # Give your run a name
    template_path="pipeline.json",  # Path to the compiled pipeline JSON
    pipeline_root="gs://vertex-ai-pipeline-root-20250116",  # Cloud Storage location for pipeline artifacts
    parameter_values={
        "project": "[your-project-id]",
        "location": "us-central1",
        "source_model_name": "gemini-2.0-flash",
        "train_data_uri": "gs://github-repo/generative-ai/gemini/tuning/mlops-tune-and-eval/patient_1_glucose_examples.jsonl",
    },  # Pass pipeline parameter values here
)

job.run()  # Submit the pipeline for execution
