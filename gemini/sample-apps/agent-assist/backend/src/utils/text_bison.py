"""This is a python utility file."""

# pylint: disable=E0401

from config import config
import vertexai
from vertexai.preview.language_models import TextGenerationModel

# Define the default parameters for text generation
parameters = {
    "max_output_tokens": 1024,  # Maximum number of tokens to generate
    "temperature": 0.05,  # Temperature parameter for sampling
    "top_p": 0.7,  # Top-p parameter for sampling
    "top_k": 20,  # Top-k parameter for sampling
}


class TextBison:
    """This class provides a simple interface to the Text-Bison generative language model."""

    def __init__(
        self,
        project_id=config["PROJECT_ID"],  # GCP Project ID
        location=config["LOCATION"],  # GCP Region
    ):
        """
        Initializes the TextBison class for text generation.

        Args:
            project_id: GCP Project ID.
            location: GCP Region. Defaults to "us-central1".
        """
        self.project_id = project_id
        self.location = location
        self.parameters = config["text_bison_parameters"]
        # Initialize the Vertex AI client library
        vertexai.init(project=self.project_id, location=self.location)

        # Load the pre-trained Text-Bison model
        self.model = TextGenerationModel.from_pretrained("text-bison")

    def generate_response(self, prompt: str) -> str:
        """
        Generates a text response using the Text-Bison model.

        Args:
            PROMPT (str): The input PROMPT for text generation.

        Returns:
            str: The generated text response.
        """
        print("running tb.generate_response")
        inner_parameters = self.parameters
        response = self.model.predict(prompt, **inner_parameters)
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
        response = self.model.predict(
            f"SUMMARISE THIS PASSAGE: {passage}", **inner_parameters
        )
        return response
