# pylint: disable=E0401

from os import environ

import vertexai
import vertexai.preview.generative_models as generative_models
from vertexai.preview.generative_models import GenerativeModel

generation_config = {
    "max_output_tokens": 2048,
    "temperature": 1,
    "top_p": 1,
}

safety_settings = {
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}


class Gemini:
    """
    A class to interact with the Gemini text generation model from Vertex AI.

    Args:
        project_id (str): The Google Cloud project ID.
        location (str): The Google Cloud region where the model is deployed.
    """

    def __init__(
        self,
        model: str = "gemini-1.0-pro-002",
    ):
        """
        Initializes the class.

        Args:
            model (str): The name of the model to use.
        """

        self.project_id = environ.get("PROJECT_ID")
        self.location = "us-central1"

        vertexai.init(project=self.project_id, location=self.location)

        self.model = GenerativeModel(model)

    def generate_response(self, prompt: str) -> str:
        """
        Generates a response to a given PROMPT.

        Args:
            PROMPT (str): The PROMPT to generate a response for.

        Returns:
            str: The generated response.
        """

        response = self.model.predict(
            prompt, generation_config=generation_config, safety_settings=safety_settings
        )

        final_response = ""
        for response in response:
            final_response += response.text

        return final_response
