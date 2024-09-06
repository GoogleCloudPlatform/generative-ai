# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

""" Submit Vertex AI Pipeline run"""

from google.cloud import aiplatform

project_id = "YOUR_PROJECT_ID"
region = "PIPELINE_REGION"
PIPELINE_TEMPLATE = "champion_challenger_pipeline.yaml"
pipeline_bucket_uri = "gs://genops-eval-pipelines"
PIPELINE_NAME = "champion-challenger-evaluation"

""" Submit compiled pipeline """


def submit_pipeline():
    aiplatform.init(
        project=project_id, staging_bucket=pipeline_bucket_uri, location=region
    )
    PIPELINE_ROOT = pipeline_bucket_uri

    job = aiplatform.PipelineJob(
        display_name=PIPELINE_NAME,
        template_path=PIPELINE_TEMPLATE,
        pipeline_root=PIPELINE_ROOT,
    )

    job.submit()


if __name__ == "__main__":
    submit_pipeline()
