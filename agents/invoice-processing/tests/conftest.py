"""Pytest configuration for invoice_processing tests."""

import sys
from pathlib import Path

# Ensure the agent package is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
