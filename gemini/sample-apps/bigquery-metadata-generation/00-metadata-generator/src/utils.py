import os
import zipfile

def zip_all_files(dataset:str, directory="src/_out/"):
    """Zips all files in the specified directory and deletes the original files after zipping."""

    if not os.path.exists(directory):
        print(f"Directory '{directory}' does not exist. Nothing to zip.")
        return None

    zip_filename = os.path.join(directory, f"{dataset}.zip")

    files_to_zip = [os.path.join(directory, f) for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]

    if not files_to_zip:
        print("No files found to zip.")
        return None

    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file in files_to_zip:
            zipf.write(file, os.path.basename(file))  # Add file to zip archive

    for file in files_to_zip:
        os.remove(file)

    return zip_filename
