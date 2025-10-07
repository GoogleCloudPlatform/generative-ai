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

"""
This is a set of prompts used in the Mesop app
"""

# video

VIDEO_TAGS_PROMPT = """Answer the following questions using the video only:
1. What is in the video? 
2. What objects are in the video? 
3. What is the action in the video? 
4. Provide 5 best tags for this video? 

Give the answer in the table format with question and answer as columns.
"""  # noqa: E261, W291


VIDEO_GEOLOCATION_PROMPT = """Answer the following questions using the video only:

What is this video about? 
How do you know which city it is? 
What street is this? 
What is the nearest intersection? 

Answer the questions in a table format with question and answer as columns.
"""  # noqa: E261, W291
