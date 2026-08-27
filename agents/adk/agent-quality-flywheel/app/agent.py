# ruff: noqa
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
"""fx-agent: a one-tool currency converter used to demonstrate the agent
quality flywheel with agents-cli.

To reproduce the before/after in the blog post, flip INSTRUCTION between
BASELINE_INSTRUCTION (the seeded bug: no tools-used footer -> 0/6) and
FIXED_INSTRUCTION (footer made mandatory -> 6/6), then re-run the eval.
"""

from google.adk.agents import Agent
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types


MODEL = "gemini-3.7-flash"

# A tiny, deterministic, offline currency rate table so the eval is cheap and
# reproducible (no external network call). Rates are illustrative fixtures.
_RATES = {
    ("USD", "EUR"): 0.92,
    ("USD", "JPY"): 156.0,
    ("USD", "GBP"): 0.79,
    ("USD", "INR"): 83.2,
    ("EUR", "USD"): 1.09,
    ("GBP", "USD"): 1.27,
    ("JPY", "USD"): 0.0064,
    ("INR", "USD"): 0.012,
}


def get_exchange_rate(base: str, target: str) -> dict:
    """Look up the exchange rate to convert one currency into another.

    Args:
        base: The 3-letter ISO currency code to convert FROM (e.g. "USD").
        target: The 3-letter ISO currency code to convert TO (e.g. "EUR").

    Returns:
        A dict with the base code, target code, and the numeric rate
        (1 unit of base in target). Returns an error message if the pair
        is not supported.
    """
    b = base.strip().upper()
    t = target.strip().upper()
    rate = _RATES.get((b, t))
    if rate is None:
        return {
            "base": b,
            "target": t,
            "error": f"No exchange rate available for {b}->{t}.",
        }
    return {"base": b, "target": t, "rate": rate}


# BASELINE (buggy) instruction: never asks for a tool-usage footer, so the
# model never writes one. Reproduces the 0/6 baseline on the custom metric.
BASELINE_INSTRUCTION = (
    "You are a currency conversion assistant. When the user asks to convert an "
    "amount from one currency to another, call the get_exchange_rate tool to "
    "look up the rate, then multiply the amount by the rate and give the user "
    "the converted amount. Keep your answer short and conversational, just "
    "state the converted amount."
)

# FIXED (candidate) instruction: makes the "Tools used" footer MANDATORY, so
# the model produces it. Reproduces 6/6 on the custom metric.
FIXED_INSTRUCTION = (
    "You are a currency conversion assistant. When the user asks to convert an "
    "amount from one currency to another, call the get_exchange_rate tool to "
    "look up the rate, then multiply the amount by the rate and give the user "
    "the converted amount. You MUST end EVERY response with a footer on its "
    "own final line in exactly this format: 'Tools used: <comma-separated tool "
    "names>'. For a conversion this is 'Tools used: get_exchange_rate'. Never "
    "omit this footer line."
)

# Flip this between FIXED_INSTRUCTION and BASELINE_INSTRUCTION to reproduce
# the before/after from the blog post.
INSTRUCTION = FIXED_INSTRUCTION

root_agent = Agent(
    name="root_agent",
    model=Gemini(model=MODEL, retry_options=types.HttpRetryOptions(attempts=3)),
    instruction=INSTRUCTION,
    tools=[get_exchange_rate],
)

app = App(root_agent=root_agent, name="app")
