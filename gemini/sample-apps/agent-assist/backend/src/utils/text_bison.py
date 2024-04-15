import vertexai
from vertexai.preview.language_models import TextGenerationModel

from config import config

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

    def generate_response(self, prompt: str) -> str:
        """
        Generates a text response using the Text-Bison model.

        Args:
            prompt (str): The input prompt for text generation.

        Returns:
            str: The generated text response.
        """
        print("running tb.generate_response")
        parameters = self.parameters
        response = self.model.predict(prompt, **parameters)
        return response.text
