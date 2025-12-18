"""Gemini Model Configuration Validator.

Validates and manages model configurations for Gemini API calls.
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Gemini model configuration."""
    model_name: str
    temperature: float = 0.7
    top_p: float = 0.9
    top_k: int = 40
    max_output_tokens: int = 2048

    def validate(self) -> tuple[bool, List[str]]:
        """Validate configuration parameters.

        Returns:
            Tuple of (is_valid, error_messages).
        """
        errors = []

        if not self.model_name:
            errors.append('model_name is required')

        if not 0 <= self.temperature <= 2:
            errors.append('temperature must be between 0 and 2')

        if not 0 <= self.top_p <= 1:
            errors.append('top_p must be between 0 and 1')

        if self.top_k < 1:
            errors.append('top_k must be >= 1')

        if self.max_output_tokens < 1 or self.max_output_tokens > 32768:
            errors.append('max_output_tokens must be between 1 and 32768')

        return len(errors) == 0, errors

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            'model_name': self.model_name,
            'temperature': self.temperature,
            'top_p': self.top_p,
            'top_k': self.top_k,
            'max_output_tokens': self.max_output_tokens,
        }


class ConfigValidator:
    """Validates Gemini model configurations."""

    VALID_MODELS = [
        'gemini-pro',
        'gemini-pro-vision',
        'gemini-1.5-pro',
        'gemini-1.5-flash',
    ]

    @classmethod
    def validate_model_name(cls, model_name: str) -> bool:
        """Check if model name is valid."""
        return model_name in cls.VALID_MODELS

    @classmethod
    def validate_config(cls, config: ModelConfig) -> tuple[bool, List[str]]:
        """Comprehensive configuration validation."""
        is_valid, errors = config.validate()

        if not cls.validate_model_name(config.model_name):
            errors.append(f'Unknown model: {config.model_name}')
            is_valid = False

        return is_valid, errors

    @classmethod
    def create_default_config(cls, model_name: str) -> Optional[ModelConfig]:
        """Create a default config for a model."""
        if not cls.validate_model_name(model_name):
            return None
        return ModelConfig(model_name=model_name)
