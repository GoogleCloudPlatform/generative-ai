from vertexai.preview.language_models import TextGenerationModel
import vertexai
import streamlit as st
import os

PROJECT_ID = os.environ.get("GCP_PROJECT")  # Your Google Cloud Project ID
LOCATION = os.environ.get("GCP_REGION")  # Your Google Cloud Project Region
vertexai.init(project=PROJECT_ID, location=LOCATION)


@st.cache_resource
def get_model():
    generation_model = TextGenerationModel.from_pretrained("text-bison@002")
    return generation_model


def get_text_generation(prompt="", **parameters):
    generation_model = get_model()
    response = generation_model.predict(prompt=prompt, **parameters)

    return response.text
