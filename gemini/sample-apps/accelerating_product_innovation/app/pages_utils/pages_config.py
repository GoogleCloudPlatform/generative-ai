"""
Utility module to work with app config.
"""

from os.path import isfile

import pytomlpp as config_loader

APP_TOML = "./app/app_config.toml"
OVERRIDE_TOML = "./override.toml"

assert isfile(APP_TOML), f"The file {APP_TOML} should exist"

with open(APP_TOML, "rb") as f:
    try:
        data = config_loader.load(f)
    except config_loader.DecodeError as e:
        print("Invalid App Configuration TOML file.")
        print(str(e))
        raise


def merge(a: dict, b: dict) -> None:
    """
    merge dictionaries a and b.
    """
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                merge(a[key], b[key])
            elif a[key] != b[key]:
                a[key] = b[key]
        else:
            a[key] = b[key]


if isfile(OVERRIDE_TOML):
    with open(OVERRIDE_TOML, "rb") as f:
        try:
            data_override = config_loader.load(f)
            merge(data, data_override)
        except config_loader.DecodeError as e:
            print("Invalid Override TOML File")
            print(str(e))
        except Exception as e:
            print("Unexpected error")
            print(str(e))
            raise

assert "translate_api" in data, "No translation options in the config"
assert "pages" in data, "No page configurations found in the config"


TRANSLATE_CFG = data["translate_api"]
PAGES_CFG = data["pages"]
GLOBAL_CFG = data["global"]
