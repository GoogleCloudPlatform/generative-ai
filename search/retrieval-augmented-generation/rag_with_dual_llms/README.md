# This is a Vertex Search RAG Dual LLM comparison and evaluation demo built using streamlit 
This demo illustrates how to compare responses from two LLMs through a corpus of documents using Vertex AI Search 

Additional features include using a Judge model to evaluate the two responses and deliver a verdict on which model's response is better aligned with the query and the given context.

This is how your final demo will look like once it is running
![final_judge_comparator](https://storage.googleapis.com/github-repo/generative-ai/gemini/use-cases/retrieval-augmented-generation/rag_with_dual_llms/final_judge_comparator.png)

# Instructions to run the demo:

1. You need to have the latest google cloud SDK installed on your machine

Follow these intructions at: https://cloud.google.com/sdk/docs/install to install the google cloud SDK and gcloud CLI. 
    
2. Once the gcloud CLI is installed, test the gcloud cli using:
gcloud init

3. Authenticate using your Google Cloud auth as follows:
gloud auth login

4. In order to run apps, you need to authenticate at the app level:
gcloud auth application-default login

5. Set the default project as follows:
export GOOGLE_VERTEXAI="True"
export PROJECT_ID="intel-common-dev-us"
export LOCATION="us-central1"

6. Now install the requirements file:
pip install -r requirements.txt

7. change the directory to the source code:
cd src

7. Now you are ready to run the demo from the source code folder:
streamlit run vertex_rag_demo_dual_llms.py

If you want to run the demo with a judge model evaluating the two model responses, use this command:
streamlit run vertex_rag_demo_dual_llms_with_judge.py

8. To end the demo, press Control-C (^C) couple of times to kill it.

# How to customize the demo to your needs
This demo runs using prompts created for a fictional Asian Chef Advisor use case. In order to change the prompts to fit your use case, you need to navigate to the prompts folder:

9. Navigate to the prompts folder which is a sub folder under src folder:
cd prompts

10. You will see a list of prompts like this in text file format. Feel free to change them to suit your use case. 
system_instruction.txt
rephraser.txt
summarizer.txt

11. Let's say you want to change the use case to a Travel Agent. Here is how your prompt might change from:
"You are an AI chatbot for cooking assistance.

Your mission is to give harried family chefs great recipes that satisfy their family's needs for healthy and tasty dishes."

to this:
"You are an AI chatbot for travel assistance.

Your mission is to give prospective travelers great suggestions that would satisfy their needs for new and exciting travel destinations."

You need to change the system_instruction.txt and save the file in the same name.

12. You must then change the rephraser and summarizer prompts the same way to align with your new use case. Hope the above has given you a flavor for how to modify prompts.

13. (Optional) If your use case changes, rerun the demo by changing to the src folder and running streamlit again:
cd src
streamlit run vertex_rag_demo_dual_llms.py

Copyright 2023 Google LLC Author: Ram Seshadri @rseshadri
