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
# - Activating that environment, pip install google-cloud-aiplatform==1.26
# - Install langchain

# ----------------------------------------
# Langchain Usage, needs google-cloud-aiplatform==1.26
# Ref https://python.langchain.com/docs/modules/model_io/models/llms/integrations/google_vertex_ai_palm

from langchain.llms import VertexAI
from langchain import PromptTemplate, LLMChain

template = """Question: {question}
Answer: Let's think step by step."""

prompt = PromptTemplate(template=template, input_variables=["question"])
llm = VertexAI()
llm_chain = LLMChain(prompt=prompt, llm=llm)
question = "What NFL team won the Super Bowl in the year Justin Beiber was born?"
response = llm_chain.run(question)
print(response)

llm = VertexAI(model_name="code-bison")
llm_chain = LLMChain(prompt=prompt, llm=llm)
question = "Write a python function that identifies if the number is a prime number?"
response = llm_chain.run(question)
print(response)
