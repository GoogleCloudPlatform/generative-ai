"""Invoice Processing -- Unified inference and learning agent for invoice processing."""

from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

from .agent import root_agent as root_agent  # noqa: E402
