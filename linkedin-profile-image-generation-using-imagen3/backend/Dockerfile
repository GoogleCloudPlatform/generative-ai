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

FROM python:3.12.8

# Upgrade pip! Is a MUST for opencv-python to work properly
RUN pip install --upgrade pip

# Install cv2 dependencies that are normally present on any local machine
# Important, never put RUN apt-get update alone, that causes a cache issue
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y

# Install opencv-python separately, it DOES NOT WORK if installed with
# the rest of the dependencies directly from requirements.txt
RUN pip install opencv-python

# Copy requirements.txt and install other dependencies
COPY requirements.txt /tmp/
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Create working directory
RUN mkdir -p /app
WORKDIR /app

# Copy the rest of the application code
COPY . /app/

# Set the environment variable
ENV ENVIRONMENT="development"
ENV FRONTEND_URL="http://localhost:4200"

# Expose the port
EXPOSE 8080

# Define the command to run your application
ENTRYPOINT ["gunicorn", "main:app", "--workers=2", "--worker-class=uvicorn.workers.UvicornWorker", "--timeout=36000", "--bind=0.0.0.0:8080"]