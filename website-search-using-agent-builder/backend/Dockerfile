# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM python:3.11
COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt
RUN mkdir -p /code
WORKDIR /code
COPY . /code/

ENV ENVIRONMENT="development"
ENV BIG_QUERY_DATASET=""
ENV FRONTEND_URL=""

EXPOSE 8080
ENTRYPOINT ["gunicorn", "main:app", "--workers=4", "--worker-class=uvicorn.workers.UvicornWorker", "--timeout=36000", "--bind=0.0.0.0:8080"]