import os

# Get all top-level directories
top_level_dirs = [
    d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")
]

for directory in top_level_dirs:
    readme_path = os.path.join(directory, "README.md")
    mode = "w+" if not os.path.exists(readme_path) else "a+"

    with open(readme_path, mode, encoding="utf-8") as f:
        f.seek(0)  # Move to the beginning of the file for 'a+' mode
        content = f.read()

        # Check if content exists, otherwise add default content
        if not content:
            f.write(f"# {directory}\n\nA brief description of this directory.")
        else:
            # You could add logic here to update existing READMEs if needed
            pass
