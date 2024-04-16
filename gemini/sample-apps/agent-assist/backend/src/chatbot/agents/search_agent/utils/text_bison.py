import vertexai
from vertexai.preview.language_models import TextGenerationModel

from config import config

parameters = {
    "max_output_tokens": 1024,
    "temperature": 0.05,
    "top_p": 0.7,
    "top_k": 20,
}


class TextBison:
    def __init__(
        self,
        PROJECT_ID=config["PROJECT_ID"],
        LOCATION=config["LOCATION"],
        max_output_tokens=2048,
        temperature=0.05,
        top_p=0.8,
        top_k=40,
    ):
        """Initializes the TextBison class.

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

        self.model = TextGenerationModel.from_pretrained(config["text_bison_model"])

    def generate_response(self, prompt):
        """Generates a response to a given prompt.

        Args:
            prompt (str): The prompt to generate a response for.

        Returns:
            str: The generated response.
        """
        parameters = self.parameters
        response = self.model.predict(prompt, **parameters)
        return response.text
