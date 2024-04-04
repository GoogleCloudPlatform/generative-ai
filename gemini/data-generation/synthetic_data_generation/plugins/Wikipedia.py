"""
Implements the plugin for interacting with Wikipedia.
"""

import logging
import wikipediaapi
from slugify import slugify
from snowfakery.plugins import SnowfakeryPlugin, PluginResult


class WikiCore(PluginResult):
    """
    Class providing a Wikipedia page as a PluginResult
    """

    def __init__(self, title: str) -> None:
        logging.info("Parsing Wikipedia Page %s", title)
        page = wikipediaapi.Wikipedia("Snowfakery (DataGen@google.com)", "en").page(
            title
        )
        self.page = page
        self.title_url = page.title
        self.text = page.text
        self.title = page.title
        self.url = page.fullurl
        self.title_slug = slugify(self.title, separator="").upper()
        self.sections = {}
        results = [(s.title, s) for s in self.page.sections]
        while results:
            sec_title, sec_obj = results.pop()
            if sec_title not in [
                "External links",
                "References",
                "See also",
                "Further reading",
            ]:
                if len(sec_obj.text):
                    self.sections[sec_title] = sec_obj.text
                for sub_sec in sec_obj.sections:
                    results.append((f"{sec_title} - {sub_sec.title}", sub_sec))
        logging.info("Parsing Wikipedia Page %s Complete", title)
        super().__init__(None)

    def simplify(self):
        """
        Returns the URL of the current Page. Used as __repr__ by snowfakery
        """
        return self.url


class Wikipedia(SnowfakeryPlugin):
    """
    Plugin for interacting with Wikipedia.
    """

    class Functions:
        """
        Functions to implement field / object level data generation
        """

        def get_page(self, title):
            """
            A wrapper around Wikipedia plugin
            """
            return WikiCore(title)
