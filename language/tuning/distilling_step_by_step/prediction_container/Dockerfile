# Copyright 2024 Google LLC
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

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.9

LABEL com.nvidia.volumes.needed=nvidia_driver

# ENV PATH=/opt/conda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility
ENV LD_LIBRARY_PATH=/usr/local/nvidia/lib:/usr/local/nvidia/lib64

# hadolint ignore=DL3013
RUN python3 -m pip install --upgrade --no-cache-dir pip

COPY ./app /app
RUN pip3 --timeout=300 --no-cache-dir install -r /app/requirements-torch.txt \
 && pip3 --timeout=300 --no-cache-dir install -r /app/requirements.txt

EXPOSE 7080

# Start the app
CMD ["gunicorn", "-b", "0.0.0.0:7080", "main:app","--workers","1","--timeout","180","-k","uvicorn.workers.UvicornWorker"]
