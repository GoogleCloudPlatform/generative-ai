"""
🚀 ADK Migration Skill

Provides reusable context containing pre-configured Source and Target environments
as well as hardcoded/verified DataStore and Connector mappings using ADK models.Skill.
"""
import os
import json
import logging

try:
    from google.adk.skills import models
except ImportError:
    models = None

def load_metadata_from_skill_md() -> dict:
    """Dynamically parses and extracts metadata from the SKILL.md YAML frontmatter."""
    skill_md_path = os.path.join(os.path.dirname(__file__), "SKILL.md")
    if os.path.exists(skill_md_path):
        try:
            import yaml
            with open(skill_md_path, "r", encoding="utf-8") as f:
                content = f.read()
            parts = content.split("---")
            if len(parts) >= 3:
                frontmatter_str = parts[1]
                data = yaml.safe_load(frontmatter_str)
                if data and "metadata" in data:
                    return data["metadata"]
        except Exception as e:
            logging.warning(f"Failed to parse SKILL.md frontmatter at import: {e}")
    return {}

# Single source of truth dynamically loaded from SKILL.md
SKILL_METADATA = load_metadata_from_skill_md()

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
        self.config = SKILL_METADATA or self._load_fallback_config()

    def _load_fallback_config(self) -> dict:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

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
