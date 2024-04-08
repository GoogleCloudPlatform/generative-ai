"""
Implements the plugin for interacting with Gemini.
"""

import logging

import jinja2
from snowfakery.plugins import SnowfakeryPlugin
from vertexai.generative_models import GenerativeModel


class Gemini(SnowfakeryPlugin):
    """
    Plugin for interacting with Gemini.
    """

    class Functions:
        """
        Functions to implement field / object level data generation
        """

        def fill_prompt(self, prompt_name: str | jinja2.Template, **kwargs) -> str:
            """
            Returns a formatted prompt
            """
            return (
                jinja2.Environment(
                    loader=jinja2.FileSystemLoader(
                        searchpath="./synthetic_data_generation/prompts"
                    )
                )
                .get_template(prompt_name)
                .render(**kwargs)
            )

        def generate(
            self, prompt_name: str | jinja2.Template, temperature=0.9, top_p=1, **kwargs
        ) -> str | None:
            """
            A wrapper around Gemini plugin
            """
            logging.info("Preparing Prompt %s with %s", prompt_name, kwargs)
            prompt = self.fill_prompt(prompt_name, **kwargs)
            logging.info("Prompt %s Prepared", prompt_name)
            try:
                logging.info("Calling Gemini For %s", prompt_name)
                response = GenerativeModel("gemini-1.0-pro-001").generate_content(
                    [prompt],
                    generation_config={
                        "max_output_tokens": 8192,
                        "temperature": temperature,
                        "top_p": top_p,
                    },
                )
            except Exception as e:
                logging.error(
                    (
                        "Unable to generate text using %s.\n"
                        "Prepared Prompt: \n%s\n\nError: %s"
                    ),
                    prompt_name,
                    prompt,
                    e,
                )
                return None

            try:
                return response.text
            except Exception as e:
                logging.error(
                    (
                        "Unable to generate text using %s.\n"
                        "Prepared Prompt: \n%s\n\n"
                        "Received Response: \n%s\n\n"
                        "Error: %s"
                    ),
                    prompt_name,
                    prompt,
                    response,
                    e,
                )
                return None
