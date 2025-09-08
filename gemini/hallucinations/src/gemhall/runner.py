from typing import Optional
from google import genai
from google.genai import types

class GeminiRunner:
    def __init__(self, model: str = "gemini-2.5-flash", *, temperature: float = 0.0, thinking_budget: int = 0, seed: Optional[int] = 1234):
        self.client = genai.Client()
        self.model = model
        self.temperature = temperature
        self.thinking_budget = thinking_budget
        self.seed = seed

    def generate(self, prompt: str) -> str:
        cfg = types.GenerateContentConfig(
            temperature=self.temperature,
            seed=self.seed,
            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget) if self.thinking_budget is not None else None,
            max_output_tokens=128,
        )
        resp = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=cfg,
        )
        return (resp.text or "").strip()


class AsyncGeminiRunner:
    def __init__(self, model: str = "gemini-2.5-flash", *, temperature: float = 0.0, thinking_budget: int = 0, seed: Optional[int] = 1234):
        self.client = genai.Client()
        self.model = model
        self.temperature = temperature
        self.thinking_budget = thinking_budget
        self.seed = seed

    async def generate(self, prompt: str) -> str:
        cfg = types.GenerateContentConfig(
            temperature=self.temperature,
            seed=self.seed,
            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget) if self.thinking_budget is not None else None,
            max_output_tokens=128,
        )
        resp = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=cfg,
        )
        return (resp.text or "").strip()
