"""This is a python utility file."""

# pylint: disable=#E0401

from config import config
import vertexai
from vertexai.preview.language_models import TextGenerationModel

parameters = {
    "max_output_tokens": 1024,
    "temperature": 0.05,
    "top_p": 0.7,
    "top_k": 20,
}


class TextBison:
    """
    Initializes the TextBison class for text generation.

    Args:
        PROJECT_ID: GCP Project ID.
        LOCATION: GCP Region. Defaults to "us-central1".
    """

    def __init__(
        self,
        project_id=config["PROJECT_ID"],
        location=config["LOCATION"],
        max_output_tokens=2048,
        temperature=0.05,
        top_p=0.8,
        top_k=40,
    ):
        """Initializes the TextBison class.

        Args:
            project_id (str): The Google Cloud project ID.
            location (str): The Google Cloud region where the model is deployed.
            max_output_tokens (int): The maximum number of tokens to generate.
            temperature (float): The temperature to use for sampling.
            top_p (float): The top-p value to use for sampling.
            top_k (int): The top-k value to use for sampling.
        """
        self.project_id = project_id
        self.location = location
        self.parameters = {
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }

        vertexai.init(project=self.project_id, location=self.location)

        self.model = TextGenerationModel.from_pretrained(config["text_bison_model"])

    def generate_response(self, prompt):
        """Generates a response to a given PROMPT.

        Args:
            PROMPT (str): The PROMPT to generate a response for.

        Returns:
            str: The generated response.
        """
        inner_parameters = self.parameters
        response = self.model.predict(prompt, **inner_parameters)
        return response.text
