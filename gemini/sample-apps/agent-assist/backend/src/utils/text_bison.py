"""This is a python utility file."""

# pylint: disable=#E0401

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
    def __init__(
        self,
        PROJECT_ID=config["PROJECT_ID"],  # GCP Project ID
        LOCATION=config["LOCATION"],  # GCP Region
    ):
        """
        Initializes the TextBison class for text generation.

        Args:
            PROJECT_ID: GCP Project ID.
            LOCATION: GCP Region. Defaults to "us-central1".
        """
        self.PROJECT_ID = PROJECT_ID
        self.LOCATION = LOCATION
        self.parameters = config["text_bison_parameters"]
        # Initialize the Vertex AI client library
        vertexai.init(project=self.PROJECT_ID, location=self.LOCATION)

        # Load the pre-trained Text-Bison model
        self.model = TextGenerationModel.from_pretrained("text-bison")

    def generate_response(self, PROMPT: str) -> str:
        """
        Generates a text response using the Text-Bison model.

        Args:
            PROMPT (str): The input PROMPT for text generation.

        Returns:
            str: The generated text response.
        """
        print("running tb.generate_response")
        parameters = self.parameters
        response = self.model.predict(PROMPT, **parameters)
        return response.text
