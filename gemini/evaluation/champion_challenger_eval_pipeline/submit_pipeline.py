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

""" Submit Vertex Pipeline run"""

from google.cloud import aiplatform

PROJECT_ID = "YOUR_PROJECT_ID"
REGION = "PIPELINE_REGION"
PIPELINE_TEMPLATE = "champion_challenger_pipeline.yaml"
PIPELINE_BUCKET_URI = "gs://genops-eval-pipelines"
PIPELINE_NAME = "champion-challenger-evaluation"

""" Submit compiled pipeline """


def submit_pipeline():
    aiplatform.init(
        project=PROJECT_ID, staging_bucket=PIPELINE_BUCKET_URI, location=REGION
    )
    PIPELINE_ROOT = PIPELINE_BUCKET_URI

    job = aiplatform.PipelineJob(
        display_name=PIPELINE_NAME,
        template_path=PIPELINE_TEMPLATE,
        pipeline_root=PIPELINE_ROOT,
    )

    job.submit()


if __name__ == "__main__":
    submit_pipeline()
