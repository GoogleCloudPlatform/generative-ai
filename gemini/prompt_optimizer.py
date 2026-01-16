"""Gemini Prompt Optimizer - Utility for enhancing prompt quality.

This module provides utilities to optimize prompts for better Gemini API responses.
"""

import re
from typing import Dict, List, Optional


class PromptOptimizer:
    """Optimize prompts for Gemini models."""

    def __init__(self):
        """Initialize the prompt optimizer."""
        self.max_length = 2000
        self.min_length = 10

    def optimize(self, prompt: str) -> str:
        """Optimize a prompt for better results.

        Args:
            prompt: The input prompt to optimize.

        Returns:
            Optimized prompt string.
        """
        # Remove extra whitespace
        prompt = ' '.join(prompt.split())

        # Add context markers if missing
        if not prompt.endswith('?') and not prompt.endswith('.'):
            prompt += '.'

        return prompt

    def validate_prompt(self, prompt: str) -> Dict[str, any]:
        """Validate prompt quality.

        Args:
            prompt: Prompt to validate.

        Returns:
            Dictionary with validation results.
        """
        issues = []
        length = len(prompt)

        if length < self.min_length:
            issues.append(f'Prompt too short (min: {self.min_length})')
        if length > self.max_length:
            issues.append(f'Prompt too long (max: {self.max_length})')

        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'length': length,
        }


if __name__ == '__main__':
    optimizer = PromptOptimizer()
    test_prompt = 'Explain machine learning basics'
    optimized = optimizer.optimize(test_prompt)
    validation = optimizer.validate_prompt(optimized)
    print(f'Original: {test_prompt}')
    print(f'Optimized: {optimized}')
    print(f'Validation: {validation}')
