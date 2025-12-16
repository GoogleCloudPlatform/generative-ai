#!/bin/bash

# Copyright 2024 Google LLC
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     https://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

credentials_file=${HOME}/.config/gcloud/application_default_credentials.json
if [ -f "$credentials_file" ]; then
    account_name=$(jq -r '.account' ${HOME}/.config/gcloud/application_default_credentials.json)
    if [[ "$account_name" == "$1" ]]; then
        exit 0
    else
        exit 1
    fi
else
    exit 1
fi