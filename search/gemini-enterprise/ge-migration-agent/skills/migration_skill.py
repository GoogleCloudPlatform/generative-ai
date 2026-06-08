"""
🚀 ADK Migration Skill

Provides reusable context containing pre-configured Source and Target environments
as well as hardcoded/verified DataStore and Connector mappings using ADK models.Skill.
"""
import os
import json
try:
    from google.adk.skills import models
except ImportError:
    models = None

SKILL_METADATA = {
    "environments": {
        "source": {
            "project_number": "<SOURCE_PROJECT_NUMBER>",
            "project_id": "<SOURCE_PROJECT_ID>",
            "region": "global",
            "engine_id": "<SOURCE_ENGINE_ID>"
        },
        "target": {
            "project_number": "<TARGET_PROJECT_NUMBER>",
            "project_id": "<TARGET_PROJECT_ID>",
            "region": "global",
            "engine_id": "<TARGET_ENGINE_ID>"
        }
    },
    "datastores_mapping": {
        "snowflake-mcp-may29_1780067471814_mcp_data": "snowflake-mcp-may29_1780829795319_mcp_data",
        "ge-drive-all_1776953145638_google_drive": "ge-drive-all_1780835769760_google_drive"
    },
    "connectors_mapping": {
        "Snowflake Mcp May29": "custom_mcp",
        "ge-drive-all": "Drive",
        "Ge Gmail": "geGmail",
        "googleSearch": "googleSearch",
        "urlContext": "urlContext"
    }
}

if models:
    migration_config_skill = models.Skill(
        frontmatter=models.Frontmatter(
            name="migration-config-skill",
            description="Holds canonical source and target environment parameters and verified DataStore mappings.",
            metadata=SKILL_METADATA
        ),
        instructions="Reference SKILL.md for complete administrative setup guides covering environments, grounding datastores_mapping, and visual connectors_mapping.",
        resources=models.Resources(references={})
    )
else:
    migration_config_skill = None

class MigrationConfigSkill:
    """Skill holding pre-verified source/target configurations and datastore mappings."""
    
    def __init__(self, config_path: str = "migration_skill.json"):
        self.config_path = os.path.join(os.path.dirname(__file__), config_path)
        self._load_config()

    def _load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r") as f:
                self.config = json.load(f)
        else:
            self.config = SKILL_METADATA

    def get_source_env(self) -> dict:
        """Returns source environment configuration."""
        return self.config.get("environments", {}).get("source", {})

    def get_target_env(self) -> dict:
        """Returns target environment configuration."""
        return self.config.get("environments", {}).get("target", {})

    def get_datastores_mapping(self) -> dict:
        """Returns verified mappings between source and target DataStores."""
        return self.config.get("datastores_mapping", {})

    def get_connectors_mapping(self) -> dict:
        """Returns verified mappings between source and target Connectors."""
        return self.config.get("connectors_mapping", {})
