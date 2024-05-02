"""This is a python utility file."""

# pylint: disable=#E0401

from config import config
import vertexai
from vertexai.preview.language_models import TextGenerationModel

# Parameters for text generation
parameters = {
    "max_output_tokens": 1024,  # Maximum number of tokens to generate
    "temperature": 0.05,  # Temperature controls the randomness of the generated text
    "top_p": 0.7,  # Top-p nucleus sampling
    "top_k": 20,  # Top-k nucleus sampling
}


class TextBison:
    """
    A class to interact with the Text Bison model from Vertex AI.

    Args:
        project_id (str): The project ID of the Vertex AI project.
        location (str): The location of the Vertex AI project.
        max_output_tokens (int): The maximum number of tokens to generate.
        temperature (float): The temperature controls the randomness of the generated text.
        top_p (float): Top-p nucleus sampling.
        top_k (int): Top-k nucleus sampling.
    """

    def __init__(
        self,
        project_id=config["PROJECT_ID"],
        location=config["LOCATION"],
        max_output_tokens: int = 8192,
        temperature: float = 0.1,
        top_p: float = 0.8,
        top_k: int = 40,
    ):
        """
        Initialize the TextBison class.

        Args:
            project_id (str): The project ID of the Vertex AI project.
            location (str): The location of the Vertex AI project.
            max_output_tokens (int): The maximum number of tokens to generate.
            temperature (float): The temperature controls the randomness of the generated text.
            top_p (float): Top-p nucleus sampling.
            top_k (int): Top-k nucleus sampling.
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

    def generate_response(self, prompt: str) -> str:
        """
        Generate a response using the Text Bison model.

        Args:
            PROMPT (str): The PROMPT to generate a response for.

        Returns:
            str: The generated response.
        """
        print("running tb.generate_response")
        inner_parameters = self.parameters
        response = self.model.predict(prompt, **inner_parameters)
        return response.text
