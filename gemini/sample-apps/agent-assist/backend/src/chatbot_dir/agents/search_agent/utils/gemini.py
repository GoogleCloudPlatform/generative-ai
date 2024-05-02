"""This is a python utility file."""

# pylint: disable=all

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
    def __init__(
        self,
        PROJECT_ID=config["PROJECT_ID"],
        LOCATION=config["LOCATION"],
        max_output_tokens=2048,
        temperature=0.05,
        top_p=0.8,
        top_k=40,
    ):
        """Initializes the GeminiText class.

        Args:
            PROJECT_ID (str): The Google Cloud project ID.
            LOCATION (str): The Google Cloud region where the model is deployed.
            max_output_tokens (int): The maximum number of tokens to generate.
            temperature (float): The temperature to use for sampling.
            top_p (float): The top-p value to use for sampling.
            top_k (int): The top-k value to use for sampling.
        """
        self.PROJECT_ID = PROJECT_ID
        self.LOCATION = LOCATION
        self.parameters = {
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }

        vertexai.init(project=self.PROJECT_ID, location=self.LOCATION)

        self.model = GenerativeModel(config["gemini_model"])
        self.chat = self.model.start_chat()

    def generate_response(self, PROMPT):
        """Generates a response to a PROMPT.

        Args:
            PROMPT (str): The PROMPT to generate a response to.

        Returns:
            str: The generated response.
        """
        parameters = self.parameters
        response = self.chat.send_message(PROMPT, generation_config=parameters)
        return response.text


if __name__ == "__main__":
    gemini = GeminiText()
