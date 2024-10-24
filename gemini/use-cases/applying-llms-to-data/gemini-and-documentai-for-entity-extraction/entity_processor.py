import json
import mimetypes
from typing import Dict

from google.cloud import documentai
from vertexai.generative_models import GenerativeModel, Part


class EntityExtractor:
    """Abstract class representing an entity"""

    def extract_entities(self) -> Dict:
        """Abstract function"""
        raise NotImplementedError()


class DocumentAIEntityExtractor(EntityExtractor):
    """Class for Document AI entity extraction"""

    def __init__(self, document: documentai.Document) -> None:
        self.document = document

    def extract_entities(self) -> Dict:
        entities = {}
        for entity in self.document.entities:
            entities[entity.type_] = entity.mention_text
        return entities


class ModelBasedEntityExtractor(EntityExtractor):
    """Class for Gemini entity extraction"""

    def __init__(self, model_version: str, prompt: str, file_path: str) -> None:
        self.model = GenerativeModel(model_version)
        self.prompt = prompt
        mime_type = mimetypes.guess_type(file_path)[0]
        if (mime_type is None) or (mime_type != "application/pdf"):
            raise ValueError("Only PDF files are supported, aborting")
        self.file_path = file_path

    def extract_entities(self) -> Dict:
        pdf_file = Part.from_uri(self.file_path, mime_type="application/pdf")
        contents = [pdf_file, self.prompt]
        response = self.model.generate_content(contents)

        cleaned_string = response.text.replace("```json\n", "").replace("\n```", "")
        entities = json.loads(cleaned_string)
        return entities
