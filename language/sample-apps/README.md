# Sample Applications to accelerate your Gen AI Applications on Google Cloud

Looking to build Gen AI applications that integrate with Vertex AI PaLM Foundational models? Would you like to use utilize standard frameworks like Python Flask, Streamlit, Gradio to host these applications on Google Cloud? You have come to the right place.  

The Sample Applications listed are provided as application templates that you can use. The key goal of these applications is to get you started quickly and help you understand how you can integrate the Vertex PaLM API and the necessary commands to deploy these applications to Google Cloud.

You can go through the various applications and pick an application or two that interests you. Click on any of the applications to see detailed documentation, sample template and instructions to deploy on Google Cloud.

## Environment Setup

We provide instructions for setting up your environment in [Cloud Shell](https://cloud.google.com/shell). Before you run any of the sample applications, ensure that you have followed the instructions in [SETUP.md](SETUP.md).

## Sample Applications

| Requirement | Application Name | Technologies Used |
|---|---|---|
|Develop a chat application using Python Flask framework and Vertex AI PaLM API model. |[chat-flask-cloudrun](chat-flask-cloudrun)|Cloud Run, Python Flask|
|Develop a chat application using [Gradio](https://www.gradio.app/) framework and Vertex AI PaLM API model.|[chat-gradio](chat-gradio)|Cloud Run, Gradio, Python|
|Develop a chat application using [Streamlit](https://streamlit.io/) framework and Vertex AI PaLM API model.|[chat-streamlit](chat-streamlit)|Cloud Run, Streamlit, Python|
|Provide an API for the Vertex AI PaLM Code Model for your client applications.|[code-predict-cloudfunction](code-predict-cloudfunction)|Cloud Functions v2, Python|
|Provide an API for the Vertex AI PaLM Text Model for your client applications.|[text-predict-cloudfunction](text-predict-cloudfunction)|Cloud Functions v2, Python|
|Develop an Event-Driven application that processes uploaded files and summarizes their content. If you are looking for a detailed summarization solution with reference architecture, refer to our [Jump Start Solution - Generative AI Document Summarization](https://cloud.google.com/architecture/ai-ml/generative-ai-document-summarization).|[summarization-gcs-cloudfunction](summarization-gcs-cloudfunction) |Cloud Functions v2, Cloud Storage, Python|

## (Optional) Using the Custom Samples via Cloud Code for VS Code plugin

If you would prefer not to use Cloud Shell and would like to utilize a Developer IDE like VS Code, we are provided support for importing and running/deploying these applications within your IDE environment.

[Cloud Code for VS Code](https://cloud.google.com/code/docs/vscode) provides IDE support for the full development cycle of Kubernetes and Cloud Run applications, from creating a cluster to running your finished application. We are providing the entire list of applications in the form of custom applications that you can import directly into VS Code in which you have configured Cloud Code.

Assuming that you have Visual Studio Code and the Cloud Code plugin setup, click on the Cloud Code link in the status bar.

- Click on New Application
- Select Custom Application
- When asked for the Git Repository URL, enter the URL of this repository: [https://github.com/GoogleCloudPlatform/generative-ai/language/sample-apps](https://github.com/GoogleCloudPlatform/generative-ai/language/sample-apps)
- You will shown all the projects. Select one of your choice.
- Complete the rest of the steps to import the projects into Visual Studio Code.

Check the screencast below:
<img src="assets/import-apps-into-cloudcode.gif" alt="Importing Custom Applications into Cloud Code"/>
