# Copyright 2023 Google LLC
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

# Prerequisites
# - Select or create a Google Cloud project.
# - Make sure that billing is enabled for your project.
# - Enable the Vertex AI API
# - Create credentials json (Ref https://www.youtube.com/watch?v=rWcLDax-VmM)
# - Set Environment variable GOOGLE_APPLICATION_CREDENTIALS as the above created json
# - Create conda environment with python=3.10 (?)
# - Activating that environment, pip install google-cloud-aiplatform==1.27

# ----------------------------------------
# Text generation with text-bison@001

import pandas as pd
import seaborn as sns
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt

from vertexai.preview.language_models import (ChatModel, InputOutputTextPair,
                                              TextEmbeddingModel,
                                              TextGenerationModel)

generation_model = TextGenerationModel.from_pretrained("text-bison@001")
prompt = "What is a large language model?"
response = generation_model.predict(prompt=prompt)
print(response.text)


prompt = "What are the top 5 trends in the tech industry?" # try your own prompt
response = generation_model.predict(prompt=prompt)
print(response.text)

my_industry = "tech" # try changing this to a different industry
response = generation_model.predict(prompt=f"What are the top 10 trends in the {my_industry} industry?")
print(response.text)

# Model parameters for text-bison@001
temp_val = 0.0
prompt_temperature = "Complete the sentence: As I prepared the picture frame, I reached into my toolkit to fetch my:"

response = generation_model.predict(
    prompt=prompt_temperature,
    temperature=temp_val,
)

print(f"[temperature = {temp_val}]")
print(response.text)

# If you run the following cell multiple times, it may return different responses,
temp_val = 1.0

response = generation_model.predict(
    prompt=prompt_temperature,
    temperature=temp_val,
)

print(f"[temperature = {temp_val}]")
print(response.text)

# The max_output_tokens parameter (range: 1 - 1024, default 128)
max_output_tokens_val = 5

response = generation_model.predict(
    prompt="List ten ways that generative AI can help improve the online shopping experience for users",
    max_output_tokens=max_output_tokens_val,
)

print(f"[max_output_tokens = {max_output_tokens_val}]")
print(response.text)
max_output_tokens_val = 500

response = generation_model.predict(
    prompt="List ten ways that generative AI can help improve the online shopping experience for users",
    max_output_tokens=max_output_tokens_val,
)

print(f"[max_output_tokens = {max_output_tokens_val}]")
print(response.text)

# The top_p parameter (range: 0.0 - 1.0, default 0.95)
top_p_val = 0.0
prompt_top_p_example = (
    "Create a marketing campaign for jackets that involves blue elephants and avocados."
)

response = generation_model.predict(
    prompt=prompt_top_p_example, temperature=0.9, top_p=top_p_val
)

print(f"[top_p = {top_p_val}]")
print(response.text)
top_p_val = 1.0

response = generation_model.predict(
    prompt=prompt_top_p_example, temperature=0.9, top_p=top_p_val
)

print(f"[top_p = {top_p_val}]")
print(response.text)

# The top_k parameter (range: 0.0 - 40, default 40)
prompt_top_k_example = "Write a 2-day itinerary for France."
top_k_val = 1

response = generation_model.predict(
    prompt=prompt_top_k_example, max_output_tokens=300, temperature=0.9, top_k=top_k_val
)

print(f"[top_k = {top_k_val}]")
print(response.text)
top_k_val = 40

response = generation_model.predict(
    prompt=prompt_top_k_example,
    max_output_tokens=300,
    temperature=0.9,
    top_k=top_k_val,
)

print(f"[top_k = {top_k_val}]")
print(response.text)

# Chat model with chat-bison@001
chat_model = ChatModel.from_pretrained("chat-bison@001")

chat = chat_model.start_chat()

print(
    chat.send_message(
        """
Hello! Can you write a 300 word abstract for a research paper I need to write about the impact of generative AI on society?
"""
    )
)

print(
    chat.send_message(
        """
Could you give me a catchy title for the paper?
"""
    )
)

# Advanced Chat model with the SDK
hat = chat_model.start_chat(
    context="My name is Ned. You are my personal assistant. My favorite movies are Lord of the Rings and Hobbit.",
    examples=[
        InputOutputTextPair(
            input_text="Who do you work for?",
            output_text="I work for Ned.",
        ),
        InputOutputTextPair(
            input_text="What do I like?",
            output_text="Ned likes watching movies.",
        ),
    ],
    temperature=0.3,
    max_output_tokens=200,
    top_p=0.8,
    top_k=40,
)
print(chat.send_message("Are my favorite movies based on a book series?"))
print(chat.send_message("When where these books published?"))

# Embedding model with textembedding-gecko@001
embedding_model = TextEmbeddingModel.from_pretrained("textembedding-gecko@001")

embeddings = embedding_model.get_embeddings(["What is life?"])

for embedding in embeddings:
    vector = embedding.values
    print(f"Length = {len(vector)}")
    print(vector)

# Embeddings and Pandas DataFrames
text = [
    "i really enjoyed the movie last night",
    "so many amazing cinematic scenes yesterday",
    "had a great time writing my Python scripts a few days ago",
    "huge sense of relief when my .py script finally ran without error",
    "O Romeo, Romeo, wherefore art thou Romeo?",
]

df = pd.DataFrame(text, columns=["text"])
print(df.head())

df["embeddings"] = [
    emb.values for emb in embedding_model.get_embeddings(df.text.values)
]
print(df.head())

# Comparing similarity of text examples using cosine similarity
cos_sim_array = cosine_similarity(list(df.embeddings.values))

# display as DataFrame
df = pd.DataFrame(cos_sim_array, index=text, columns=text)
print(df.head())

ax = sns.heatmap(df, annot=True, cmap="crest")
ax.xaxis.tick_top()
ax.set_xticklabels(text, rotation=90)
plt.show()

