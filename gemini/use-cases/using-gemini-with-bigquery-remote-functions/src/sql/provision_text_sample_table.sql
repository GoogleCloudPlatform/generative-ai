# Copyright 2023 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

CREATE OR REPLACE TABLE
`${project_id}.${dataset_id}.sample_text_prompts`

(
  landmark_name STRING,
  text_prompt STRING,
  image_file STRING
)

AS

SELECT
  "Wasserturm Radebeul" AS landmark_name,
  """Describe the historic landmark
  Wasserturm Radebeul in 5 sentences or less""" AS text_prompt,
  "0015ff7be758af7f.jpg" AS image_file
UNION ALL
SELECT
  "USS Texas" AS landmark_name,
  """Describe the historic landmark
   USS Texas in 5 sentences or less""" AS text_prompt,
  "000952662701bc5d.jpg" AS image_file
UNION ALL
SELECT
  "Erzsebet Bridge" AS landmark_name,
  """Describe the historic landmark
  Erzsébet Bridge in 5 sentences or less""" AS text_prompt,
  "00454ad2434ee811.jpg" AS image_file
UNION ALL
SELECT
  "Post Office, Meriden, Conn." AS landmark_name,
  """Describe the historic landmark
  Post Office, Meriden, Conn. in 5 sentences or less""" AS text_prompt,
  "00041b7cefb3f517.jpg" AS image_file
UNION ALL
SELECT
  "Saxtead Green Windmill" AS landmark_name,
  """Describe the historic landmark
  Saxtead Green Windmill in 5 sentences or less""" AS text_prompt,
  "003ef0c91fa27a19.jpg" AS image_file
UNION ALL
SELECT
  "Double-Span Metal Pratt Truss Bridge" AS landmark_name,
  """Describe the historic landmark
  Double-Span Metal Pratt Truss Bridge in 5 sentences or less""" AS text_prompt,
  "0030d6b693209987.jpg" AS image_file
UNION ALL
SELECT
  "Grand Canyon" AS landmark_name,
  """Describe the historic landmark
  Grand Canyon in 5 sentences or less""" AS text_prompt,
  "004f71969864e68a.jpg" AS image_file
UNION ALL
SELECT
  "Bamburgh Castle" AS landmark_name,
  """Describe the historic landmark
  Bamburgh Castle in 5 sentences or less""" AS text_prompt,
  "004feb14c8606fd9.jpg" AS image_file
UNION ALL
SELECT
  "Alcatraz Island" AS landmark_name,
  """Describe the historic landmark
  Alcatraz Island in 5 sentences or less""" AS text_prompt,
  "000ded10aa81024f.jpg" AS image_file;
