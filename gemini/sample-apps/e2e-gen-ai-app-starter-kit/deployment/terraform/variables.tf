variable "prod_project_id" {
  type        = string
  description = "**Production** Google Cloud Project ID for resource deployment."
}

variable "staging_project_id" {
  type        = string
  description = "**Staging** Google Cloud Project ID for resource deployment."
}

variable "cicd_runner_project_id" {
  type        = string
  description = "Google Cloud Project ID where CI/CD pipelines will execute."
}

variable "region" {
  type        = string
  description = "Google Cloud region for resource deployment."
  default     = "us-central1"
}

variable "host_connection_name" {
  description = "Name of the host connection you created in Cloud Build"
  type        = string
}

variable "repository_name" {
  description = "Name of the repository you'd like to connect to Cloud Build"
  type        = string
}

variable "telemetry_bigquery_dataset_id" {
  type        = string
  description = "BigQuery dataset ID for telemetry data export."
  default     = "telemetry_genai_app_sample_sink"
}

variable "feedback_bigquery_dataset_id" {
  type        = string
  description = "BigQuery dataset ID for feedback data export."
  default     = "feedback_genai_app_sample_sink"
}

variable "telemetry_logs_filter" {
  type        = string
  description = "Log Sink filter for capturing telemetry data. Captures logs with the `traceloop.association.properties.log_type` attribute set to `tracing`."
  default     = "jsonPayload.attributes.\"traceloop.association.properties.log_type\"=\"tracing\" jsonPayload.resource.attributes.\"service.name\"=\"Sample Chatbot Application\""
}

variable "feedback_logs_filter" {
  type        = string
  description = "Log Sink filter for capturing feedback data. Captures logs where the `log_type` field is `feedback`."
  default     = "jsonPayload.log_type=\"feedback\""
}

variable "telemetry_sink_name" {
  type        = string
  description = "Name of the telemetry data Log Sink."
  default     = "telemetry_logs_genai_app_sample"
}

variable "feedback_sink_name" {
  type        = string
  description = "Name of the feedback data Log Sink."
  default     = "feedback_logs_genai_app_sample"
}

variable "cicd_runner_sa_name" {
  description = "Service account name to be used for the CICD processes"
  type        = string
  default     = "cicd-runner"
}

variable "cloud_run_app_sa_name" {
  description = "Service account name to be used for the Cloud Run service"
  type        = string
  default     = "genai-app-sample-cr-sa"
}

variable "suffix_bucket_name_load_test_results" {
  description = "Suffix Name of the bucket that will be used to store the results of the load test. Prefix will be project id."
  type        = string
  default     = "cicd-load-test-results"
}


variable "artifact_registry_repo_name" {
  description = "Name of the Artifact registry repository to be used to push containers"
  type        = string
  default     = "genai-containers"
}



variable "cloud_run_app_roles" {
  description = "List of roles to assign to the Cloud Run app service account"
  type        = list(string)
  default = [
    "roles/aiplatform.user",
    "roles/discoveryengine.editor",
    "roles/logging.logWriter",
    "roles/cloudtrace.agent",
    "roles/storage.admin"
  ]
}

variable "cicd_roles" {
  description = "List of roles to assign to the CICD runner service account in the CICD project"
  type        = list(string)
  default = [
    "roles/storage.admin",
    "roles/run.invoker",
    "roles/aiplatform.user",
    "roles/discoveryengine.editor",
    "roles/logging.logWriter",
    "roles/artifactregistry.writer",
    "roles/cloudbuild.builds.builder"
  ]
}

variable "cicd_sa_deployment_required_roles" {
  description = "List of roles to assign to the CICD runner service account for the Staging and Prod projects."
  type        = list(string)
  default     = ["roles/run.developer", "roles/iam.serviceAccountUser"]
}
