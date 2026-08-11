# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Resilient Google Cloud wrapper with retry and model fallback."""

import asyncio

import config as cfg
from google import genai
from google.genai import errors as genai_errors

# ANSI colours
YELLOW = "\033[93m"
DIM = "\033[2m"
RESET = "\033[0m"

DEFAULT_FALLBACK_MODELS = cfg.ANALYSIS_FALLBACKS

RETRY_DELAYS = [30, 60]  # seconds between retries for each model


async def generate_with_fallback(
    client: genai.Client,
    model: str,
    contents,
    config: genai.types.GenerateContentConfig | None = None,
    fallback_models: list[str] | None = None,
):
    """Call generate_content with retry on 429 and model downgrade fallback.

    Tries ``model`` first with up to 2 retries (30s, 60s backoff).
    If all retries are exhausted, moves to the next model in
    ``fallback_models`` and repeats.  Re-raises if every model fails.
    """
    if fallback_models is None:
        fallback_models = list(DEFAULT_FALLBACK_MODELS)

    models_to_try = [model] + fallback_models

    last_error = None
    for idx, current_model in enumerate(models_to_try):
        for attempt in range(1 + len(RETRY_DELAYS)):
            try:
                kwargs = {"model": current_model, "contents": contents}
                if config is not None:
                    kwargs["config"] = config
                return await client.aio.models.generate_content(**kwargs)
            except genai_errors.ClientError as exc:
                last_error = exc
                if exc.code == 404:
                    # Model not found in this region — skip retries,
                    # fall through to next model immediately
                    if idx + 1 < len(models_to_try):
                        next_model = models_to_try[idx + 1]
                        print(
                            f"  {YELLOW}⬇ {current_model} not available"
                            f" — falling back to {next_model}{RESET}"
                        )
                    break  # move to next model
                if exc.code != 429:
                    raise  # non-quota error — propagate immediately

                if attempt < len(RETRY_DELAYS):
                    delay = RETRY_DELAYS[attempt]
                    print(
                        f"  {YELLOW}⏳ 429 quota exceeded on {current_model}"
                        f" — retrying in {delay}s"
                        f" (attempt {attempt + 2}/{1 + len(RETRY_DELAYS)}){RESET}"
                    )
                    await asyncio.sleep(delay)
                else:
                    # Retries exhausted for this model
                    if idx + 1 < len(models_to_try):
                        next_model = models_to_try[idx + 1]
                        print(
                            f"  {YELLOW}⬇ Falling back from {current_model}"
                            f" → {next_model}{RESET}"
                        )
                    break  # move to next model

    # All models exhausted
    raise last_error  # type: ignore[misc]
