"""This is a python utility file."""

# pylint: disable=E0401

from config import config
import vertexai
from vertexai.preview.generative_models import GenerativeModel

parameters = {
    "max_output_tokens": 1024,
    "temperature": 0,
    "top_p": 0.7,
    "top_k": 20,
}


class GeminiText:
    """
    A class to interact with the Gemini text generation model from Vertex AI.

    Args:
        project_id (str): The Google Cloud project ID.
        location (str): The Google Cloud region where the model is deployed.
        max_output_tokens (int): The maximum number of tokens to generate.
        temperature (float): The temperature to use for sampling.
        top_p (float): The top-p value to use for sampling.
        top_k (int): The top-k value to use for sampling.
    """

    def __init__(
        self,
        max_output_tokens=2048,
        temperature=0,
        top_p=0.8,
        top_k=40,
    ):
        """
        Initializes the class.

        Args:
            project_id (str): The Google Cloud project ID.
            location (str): The Google Cloud region where the model is deployed.
            max_output_tokens (int): The maximum number of tokens to generate.
            temperature (float): The temperature to use for sampling.
            top_p (float): The top-p value to use for sampling.
            top_k (int): The top-k value to use for sampling.
        """
        self.project_id = config["PROJECT_ID"]
        self.location = config["LOCATION"]
        self.parameters = {
            "max_output_tokens": max_output_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }

        vertexai.init(project=self.project_id, location=self.location)

        self.model = GenerativeModel(config["gemini_model"])
        self.chat = self.model.start_chat()

    def generate_response(self, prompt: str) -> str:
        """
        Generates a response to a given PROMPT.

        Args:
            PROMPT (str): The PROMPT to generate a response for.

        Returns:
            str: The generated response.
        """
        print("running tb.generate_response")
        inner_parameters = self.parameters
        # response =self.model.predict(PROMPT,**parameters)
        response = self.chat.send_message(prompt, generation_config=inner_parameters)
        return response.text

    def summarise(self, passage: str) -> str:
        """
        Generates a summary for the given passage.

        Args:
            passage (str): The input passage to be summarised

        Returns:
            str: The summary
        """
        inner_parameters = self.parameters
        response = self.chat.send_message(
            f"SUMMARISE THIS PASSAGE: {passage}", generation_config=inner_parameters
        )
        return response


if __name__ == "__main__":
    gemini = GeminiText()
