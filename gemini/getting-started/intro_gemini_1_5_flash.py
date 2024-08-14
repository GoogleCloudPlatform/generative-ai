# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.16.3
#   kernelspec:
#     display_name: Python 3
#     name: python3
# ---

# + id="bCIMTPB1WoTq"
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

# + [markdown] id="7yVV6txOmNMn"
# # Getting started with Vertex AI Gemini 1.5 Flash
#
#
# <table align="left">
#   <td style="text-align: center">
#     <a href="https://colab.research.google.com/github/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_1_5_flash.ipynb">
#       <img src="https://cloud.google.com/ml-engine/images/colab-logo-32px.png" alt="Google Colaboratory logo"><br> Open in Colab
#     </a>
#   </td>
#   <td style="text-align: center">
#     <a href="https://console.cloud.google.com/vertex-ai/colab/import/https:%2F%2Fraw.githubusercontent.com%2FGoogleCloudPlatform%2Fgenerative-ai%2Fmain%2Fgemini%2Fgetting-started%2Fintro_gemini_1_5_flash.ipynb">
#       <img width="32px" src="https://lh3.googleusercontent.com/JmcxdQi-qOpctIvWKgPtrzZdJJK-J3sWE1RsfjZNwshCFgE_9fULcNpuXYTilIR2hjwN" alt="Google Cloud Colab Enterprise logo"><br> Open in Colab Enterprise
#     </a>
#   </td>
#   <td style="text-align: center">
#     <a href="https://console.cloud.google.com/vertex-ai/workbench/deploy-notebook?download_url=https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/gemini/getting-started/intro_gemini_1_5_flash.ipynb">
#       <img src="https://lh3.googleusercontent.com/UiNooY4LUgW_oTvpsNhPpQzsstV5W8F7rYgxgGBD85cWJoLmrOzhVs_ksK_vgx40SHs7jCqkTkCk=e14-rj-sc0xffffff-h130-w32" alt="Vertex AI logo"><br> Open in Workbench
#     </a>
#   </td>
#   <td style="text-align: center">
#     <a href="https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/getting-started/intro_gemini_1_5_flash.ipynb">
#       <img src="https://cloud.google.com/ml-engine/images/github-logo-32px.png" alt="GitHub logo"><br> View on GitHub
#     </a>
#   </td>
# </table>
#

# + [markdown] id="1EExYZvij2ve"
# | | |
# |-|-|
# |Author(s) | [Eric Dong](https://github.com/gericdong), [Holt Skinner](https://github.com/holtskinner) |

# + [markdown] id="t1DnOs6rkbOy"
# ## Overview
# This notebook provides a practical introduction to Google's Gemini 1.5 Flash model, a powerful new AI model designed for fast and efficient processing of diverse data types.
#
# **What is Gemini 1.5 Flash?**
#
# Gemini 1.5 Flash is a large language model (LLM) from Google's Gemini family. It's built with a focus on speed and efficiency, while still maintaining the capabilities of its predecessors. Flash has the ability to understand and process various types of content, including text, images, audio, and video. This makes it a versatile tool for a wide range of tasks.
#
# **What you'll learn:**
#
# In this notebook, you'll learn how to use Gemini 1.5 Flash through the Vertex AI SDK to:
#
# - Analyze audio files and extract insights.
# - Understand video content, including spoken words.
# - Process PDF documents and extract information.
# - Process different types of data simultaneously (images, video, audio, and text).
#
# **Before you start:**
#
# 1. **Google Cloud Project:** Ensure you have a Google Cloud project set up. If you don't, create one at [https://console.cloud.google.com/](https://console.cloud.google.com/).
# 2. **Vertex AI API Enablement:** Enable the Vertex AI API in your Google Cloud project. You can do this in the Google Cloud Console at [https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com](https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com).
# 3. **Vertex AI SDK:** Install the Vertex AI SDK for Python using `pip3 install google-cloud-aiplatform`.
# ## Getting Started

# + [markdown] id="No17Cw5hgx12"
# ### Setting up Your Environment
#
# **Installing the Vertex AI SDK**
#
# Let's start by installing the Vertex AI SDK for Python, which provides the tools we'll use to interact with the Gemini model.

# + id="tFy3H3aPgx12"
# ! pip3 install --upgrade --user --quiet google-cloud-aiplatform

# + [markdown] id="R5Xep4W9lq-Z"
# **Restarting the Runtime (Colab)**
#
# If you're using Colab, you'll need to restart the runtime to make the newly installed packages available. Run the following cell to do so.

# + id="XRvKdaPDTznN"
import sys

if "google.colab" in sys.modules:
    import IPython

    app = IPython.Application.instance()
    app.kernel.do_shutdown(True)

# + [markdown] id="SbmM4z7FOBpM"
# <div class="alert alert-block alert-warning">
# <b>⚠️ The kernel is going to restart. Please wait until it is finished before continuing to the next step. ⚠️</b>
# </div>
#

# + [markdown] id="dmWOrTJ3gx13"
# **Authentication (Colab Only)**
#
# If you're running this notebook on Google Colab, authenticate your environment to connect to your Google Cloud project.

# + id="NyKGtVQjgx13"
import sys

if "google.colab" in sys.modules:
    from google.colab import auth

    auth.authenticate_user()

# + [markdown] id="DF4l8DTdWgPY"
# ### Project Setup and Initialization
#
# **Project ID and Location:**  Set your Google Cloud project ID and the location where you want to use Vertex AI. You'll need to replace `[your-project-id]` with your actual project ID.

# + id="Nqwi-5ufWp_B"
PROJECT_ID = "[your-project-id]"  # @param {type:"string"}
LOCATION = "us-central1"  # @param {type:"string"}

import vertexai

vertexai.init(project=PROJECT_ID, location=LOCATION)

# + [markdown] id="jXHfaVS66_01"
# ### Importing Libraries

from IPython.core.interactiveshell import InteractiveShell

# + id="lslYAvw37JGQ"
import IPython.display

InteractiveShell.ast_node_interactivity = "all"

from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
    Part,
)

# + [markdown] id="BY1nfXrqRxVX"
# ### Loading the Gemini 1.5 Flash Model
#
# Now, let's load the Gemini 1.5 Flash model using the Vertex AI SDK.  The `MODEL_ID` is set to the specific identifier for the Gemini 1.5 Flash model on Vertex AI.

# + id="U7ExWmuLBdIA"
MODEL_ID = "gemini-1.5-flash-001"  # @param {type:"string"}

model = GenerativeModel(MODEL_ID)

# + [markdown] id="l9OKM0-4SQf8"
# ## Basic Usage Example
#
# Here's a simple example to demonstrate how to use the Vertex AI SDK to interact with Gemini 1.5 Flash. We'll prompt the model to translate a sentence from English to French.

# + id="FhFxrtfdSwOP"
# Load a example model with system instructions
example_model = GenerativeModel(
    MODEL_ID,
    system_instruction=[
        "You are a helpful language translator.",
        "Your mission is to translate text in English to French.",
    ],
)

# Set model parameters
generation_config = GenerationConfig(
    temperature=0.9,
    top_p=1.0,
    top_k=32,
    candidate_count=1,
    max_output_tokens=8192,
)

# Set safety settings
safety_settings = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_LOW_AND_ABOVE,
}

prompt = """
 User input: I like bagels.
 Answer:
"""

# Set contents to send to the model
contents = [prompt]

# Counts tokens
print(example_model.count_tokens(contents))

# Prompt the model to generate content
response = example_model.generate_content(
    contents,
    generation_config=generation_config,
    safety_settings=safety_settings,
)

# Print the model response
print(f"\nAnswer:\n{response.text}")
print(f'\nUsage metadata:\n{response.to_dict().get("usage_metadata")}')
print(f"\nFinish reason:\n{response.candidates[0].finish_reason}")
print(f"\nSafety settings:\n{response.candidates[0].safety_ratings}")

# + [markdown] id="acRxKRA-sr0j"
# ## Audio Understanding
#
# Gemini 1.5 Flash can work directly with audio files, providing insights and summaries.

# + id="10hgCOIA4E5_"
audio_file_path = "cloud-samples-data/generative-ai/audio/pixel.mp3"
audio_file_uri = f"gs://{audio_file_path}"
audio_file_url = f"https://storage.googleapis.com/{audio_file_path}"

IPython.display.Audio(audio_file_url)

# + [markdown] id="9sXM19QQ4vj1"
# ### Example 1: Summarizing Audio
#
# Let's get a summary of the audio content. We'll ask Gemini 1.5 Flash to provide chapter titles, keeping it concise.

# + id="OPQ1fBk44E6L"
prompt = """
 Please provide a summary for the audio.
 Provide chapter titles, be concise and short, no need to provide chapter summaries.
 Do not make up any information that is not part of the audio and do not be verbose.
"""

audio_file = Part.from_uri(audio_file_uri, mime_type="audio/mpeg")
contents = [audio_file, prompt]

response = model.generate_content(contents)
print(response.text)

# + [markdown] id="dzA8vKgQATGL"
# ### Example 2: Transcription
#
# In this example, we'll have Gemini 1.5 Flash transcribe the audio, including timestamps and speaker identification.

# + id="buziSRMG-42a"
prompt = """
  Can you transcribe this interview, in the format of timecode, speaker, caption.
  Use speaker A, speaker B, etc. to identify the speakers.
"""

audio_file = Part.from_uri(audio_file_uri, mime_type="audio/mpeg")
contents = [audio_file, prompt]

responses = model.generate_content(contents, stream=True)

for response in responses:
    print(response.text)

# + [markdown] id="_U36v4TmswAG"
# ## Video with Audio Understanding
#
# Gemini 1.5 Flash can process videos along with their audio tracks, enabling you to understand the content of both.

# + id="EDswcPI0tSRk"
video_file_path = "cloud-samples-data/generative-ai/video/pixel8.mp4"
video_file_uri = f"gs://{video_file_path}"
video_file_url = f"https://storage.googleapis.com/{video_file_path}"

IPython.display.Video(video_file_url, width=450)

# + id="R9isZfjzCYxw"
prompt = """
 Provide a description of the video.
 The description should also contain anything important which people say in the video.
"""

video_file = Part.from_uri(video_file_uri, mime_type="video/mp4")
contents = [video_file, prompt]

response = model.generate_content(contents)
print(response.text)

# + [markdown] id="JcBZZ-bJe2yS"
# As you can see, the model is able to extract text and audio information from the video, showing its multimodal capabilities.

# + [markdown] id="3dTcKyoutS7U"
# ## PDF Document Analysis
#
# You can use Gemini 1.5 Flash to process PDF documents. This is useful for extracting information, summarizing content, and answering questions about the document.
#
# **Example: The Gemini 1.5 Paper**
#
# Let's try this out with the Gemini 1.5 research paper.

# + id="JgKDIZUstYwV"
pdf_file_uri = "gs://cloud-samples-data/generative-ai/pdf/2403.05530.pdf"

prompt = """
 You are a very professional document summarization specialist.
 Please summarize the given document.
"""

pdf_file = Part.from_uri(pdf_file_uri, mime_type="application/pdf")
contents = [pdf_file, prompt]

response = model.generate_content(contents)
print(response.text)

# + id="52ltdcv5EsaM"
image_file_path = "cloud-samples-data/generative-ai/image/cumulative-average.png"
image_file_url = f"https://storage.googleapis.com/{image_file_path}"
image_file_uri = f"gs://{image_file_path}"

IPython.display.Image(image_file_url, width=450)

# + id="EEmrMpRMHyel"
prompt = """
Task: Answer the following questions based on a PDF document and image file provided in the context.

Instructions:
- Look through the image and the PDF document carefully and answer the question.
- Give a short and terse answer to the following question.
- Do not paraphrase or reformat the text you see in the image.
- Cite the source of page number for the PDF document provided as context as "(Page X)".

  Questions:
  - What is in the given image?
  - Is there a similar graph in the given document?

Context:
"""

image_file = Part.from_uri(image_file_uri, mime_type="image/png")

contents = [
    pdf_file,
    image_file,
    prompt,
]

response = model.generate_content(contents)
print(response.text)

# + [markdown] id="RIwBUZTyLJh0"
# Gemini 1.5 Flash is capable of cross-referencing the image and the PDF document to identify the graph mentioned in the document.

# + [markdown] id="s3vu8ogWs7iZ"
# ## All Modalities at Once
#
# Gemini 1.5 Flash excels at handling various data types simultaneously. You can combine images, video, audio, and text in a single input sequence.

# + id="Gp216wxgiKg4"
video_file_path = "cloud-samples-data/generative-ai/video/behind_the_scenes_pixel.mp4"
video_file_uri = f"gs://{video_file_path}"
video_file_url = f"https://storage.googleapis.com/{video_file_path}"

IPython.display.Video(video_file_url, width=450)

# + id="qS7KSwvbjhFh"
image_file_path = "cloud-samples-data/generative-ai/image/a-man-and-a-dog.png"
image_file_uri = f"gs://{image_file_path}"
image_file_url = f"https://storage.googleapis.com/{image_file_path}"

IPython.display.Image(image_file_url, width=450)

# + id="pRdzwDi9iLGn"
video_file = Part.from_uri(video_file_uri, mime_type="video/mp4")
image_file = Part.from_uri(image_file_uri, mime_type="image/png")

prompt = """
  Look through each frame in the video carefully and answer the questions.
  Only base your answers strictly on what information is available in the video attached.
  Do not make up any information that is not part of the video and do not be too
  verbose, be to the point.

  Questions:
  - When is the moment in the image happening in the video? Provide a timestamp.
  - What is the context of the moment and what does the narrator say about it?
"""

contents = [video_file, image_file, prompt]

response = model.generate_content(contents)
print(response.text)

# + [markdown] id="b3iovYxOwOT7"
# ## Conclusion
#
# In this tutorial, you've explored the capabilities of Gemini 1.5 Flash and learned how to use it through the Vertex AI SDK. With its speed, efficiency, and multimodal understanding, Gemini 1.5 Flash opens up exciting possibilities for building innovative AI applications.
