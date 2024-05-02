"""This is a python utility file."""

# pylint: disable=#E0401

from config import config
import vertexai
from vertexai.preview.generative_models import GenerativeModel

parameters = {
    "max_output_tokens": 1024,
    "temperature": 0.05,
    "top_p": 0.7,
    "top_k": 20,
}


class GeminiText:
    """This class provides a simple interface to the Gemini generative language model."""

    def __init__(
        self,
        project_id=config["PROJECT_ID"],
        location=config["LOCATION"],
        max_output_tokens=2048,
        temperature=0.05,
        top_p=0.8,
        top_k=40,
    ):
        """Initializes the GeminiText class.

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

        self.model = GenerativeModel(config["gemini_model"])
        self.chat = self.model.start_chat()

    def generate_response(self, prompt):
        """Generates a response to a PROMPT.

        Args:
            PROMPT (str): The PROMPT to generate a response to.

        Returns:
            str: The generated response.
        """
        inner_parameters = self.parameters
        response = self.chat.send_message(prompt, generation_config=inner_parameters)
        return response.text


if __name__ == "__main__":
    gemini = GeminiText()
