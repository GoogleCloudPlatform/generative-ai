import json
import mimetypes
from typing import Dict, List

from vertexai.generative_models import GenerativeModel, Part


class EntityExtractor:
    def extract_entities(self) -> List[Dict]:
        raise NotImplementedError()


class DocumentAIEntityExtractor(EntityExtractor):
    def __init__(self, document):
        self.document = document

    def extract_entities(self) -> Dict:
        entities = {}
        for entity in self.document.entities:
            entities[entity.type_] = entity.mention_text
        return entities


class ModelBasedEntityExtractor(EntityExtractor):
    def __init__(self, model_version, prompt, file_path):
        self.model = GenerativeModel(model_version)
        self.prompt = prompt
        mime_type = mimetypes.guess_type(file_path)[0]
        if (mime_type is None) or (mime_type != "application/pdf"):
            raise ValueError("Only PDF files are supported, aborting")
        self.file_path = file_path

    def extract_entities(self) -> List[Dict]:
        pdf_file = Part.from_uri(self.file_path, mime_type="application/pdf")
        contents = [pdf_file, self.prompt]
        response = self.model.generate_content(contents)

        cleaned_string = response.text.replace("```json\n", "").replace("\n```", "")
        entities = json.loads(cleaned_string)
        return entities
