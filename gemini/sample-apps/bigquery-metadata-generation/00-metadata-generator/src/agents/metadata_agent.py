from configparser import ConfigParser

from google.cloud import aiplatform
from google.oauth2 import service_account
from llama_index.core import PromptTemplate
from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.llms.vertex import Vertex
from models import BQTable
from vertexai.generative_models._generative_models import (
    HarmBlockThreshold,
    HarmCategory,
)

config = ConfigParser()
config.read("src/config.ini")
aiplatform.init(location=config["GENERIC"]["REGION"])


class MetadataAgent:
    def __init__(self):
        credentials = service_account.Credentials.from_service_account_file(
            config["GCP_JSON_CREDS_PATH"]
        )
        aiplatform.init(
            project=config["PROJECT_ID"],
            location=config["REGION"],
            credentials=credentials,
        )

        self.llm = self._get_llm
        self.prompt_template_oneshot_interaction = config["METADATA_AGENT"][
            "BASE_PROMPT"
        ]

    def _get_llm(self):
        """
        The `_get_llm` function returns a `Vertex` object with specific model, project, and location
        configurations.
        :return: An instance of the Vertex class with the specified model, project, and location parameters.
        """
        return Vertex(
            model=config["METADATA_AGENT"]["MODEL"],
            temperature=config["METADATA_AGENT"]["TEMPERATURE"],
            max_retries=config["METADATA_AGENT"]["MAX_RETRIES"],
            max_tokens=config["METADATA_AGENT"]["MAX_TOKENS"],
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            },
        )

    def generate_metadata(self, metadata_example, table_data) -> BQTable:
        """ """
        try:
            llm = self._get_llm()
            parser = PydanticOutputParser(output_cls=BQTable)

            prompt_template = PromptTemplate(
                template=(self.prompt_template_oneshot_interaction),
            )

            pydantic_llm_assistant = LLMTextCompletionProgram.from_defaults(
                output_cls=BQTable,
                output_parser=parser,
                prompt=prompt_template,
                llm=llm,
                verbose=True,
            )

            output = pydantic_llm_assistant(
                query=config["METADATA_AGENT"]["BASE_PROMPT"],
                metadata_example=metadata_example,
                input_table=table_data,
            )

            return BQTable(
                description=output.description,
                overview=output.overview,
                tags=output.tags,
                schema=output.schema,
            )

        except Exception as e:
            print(e)
            return BQTable(description="error", overview="", tags="", schema=None)
