from abc import ABC, abstractmethod
import json
import mimetypes
from typing import Dict

from google.cloud import documentai
from vertexai.generative_models import GenerationConfig, GenerativeModel, Part


class EntityExtractor(ABC):
    """Abstract Base Class for entity extraction."""

    @abstractmethod
    def extract_entities(self) -> Dict:
        """Abstract method to extract entities."""


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
        self.config = GenerationConfig(
            temperature=0.0,
            top_p=0.8,
            top_k=32,
            candidate_count=1,
            max_output_tokens=2048,
            response_mime_type="application/json",
        )
        self.model = GenerativeModel(model_version, generation_config=self.config)
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
