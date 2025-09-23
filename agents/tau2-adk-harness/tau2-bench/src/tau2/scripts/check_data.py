#!/usr/bin/env python3
"""
Script to check if the tau2 data directory is properly configured.
"""

import sys
from pathlib import Path

from tau2.utils.utils import DATA_DIR


def main():
    """Main function to check data directory."""
    print("tau2 Data Directory Checker")
    print("=" * 40)

    print(f"Data directory: {DATA_DIR}")

    if DATA_DIR.exists():
        print("✅ Data directory exists")
        print("You can now run tau2 commands.")
    else:
        print("❌ Data directory does not exist!")
        print("\nTo fix this, you can:")
        print("1. Set the TAU2_DATA_DIR environment variable:")
        print("   export TAU2_DATA_DIR=/path/to/your/tau2-bench/data")
        print("2. Or ensure the data directory exists in the expected location")
        sys.exit(1)


if __name__ == "__main__":
    main()
