import os
import zipfile
import json
from configparser import ConfigParser

from dependencies.metadata.metadata import update_descriptions

config = ConfigParser()
config.read("src/config.ini")

DATA_DIR = "src/data/"

if __name__ == "__main__":
    zip_files = [filename for filename in os.listdir(DATA_DIR) if filename.endswith(".zip")]

    for zip_filename in zip_files:
        zip_path = os.path.join(DATA_DIR, zip_filename)

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            #1 Extract
            temp_dir = os.path.join(DATA_DIR, "_temp")
            os.makedirs(temp_dir, exist_ok=True)
            zip_ref.extractall(temp_dir)

            #2 Update
            for file in os.listdir(temp_dir):
                if file.endswith(".json"):
                    json_path = os.path.join(temp_dir, file)
                    print(json_path)
                    with open(json_path, "r", encoding="utf-8") as json_file:
                        update_descriptions(file.replace(".json", ""), json.load(json_file))
                        os.remove(os.path.join(temp_dir, file))


