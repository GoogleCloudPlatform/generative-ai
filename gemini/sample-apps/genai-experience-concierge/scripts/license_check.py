# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import re
import sys
import argparse
import subprocess

_TF_FILE_PATTERN = r".*\.tf$"
_PY_FILE_PATTERN = r".*\.py$"
_HASH_LICENSE_HEADER = """
# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
""".strip()


def license_check(fix: bool = False):
    ps = subprocess.run(["git", "ls-files"], capture_output=True, text=True)

    found_invalid_file = False

    for line in ps.stdout.splitlines():
        file_path = line.strip().strip('"')

        maybe_py_match = re.match(_PY_FILE_PATTERN, file_path)
        maybe_tf_match = re.match(_TF_FILE_PATTERN, file_path)

        # skip this file if it didn't match any patterns
        if maybe_py_match is None and maybe_tf_match is None:
            continue

        # open file and strip leading empty lines
        with open(file_path, "r") as f:
            contents = f.read().lstrip()

        # check if file starts with license header.
        # note: if adding new file types that don't support hash-based comments, add additional cases.
        if contents.startswith(_HASH_LICENSE_HEADER):
            continue

        # mark that an invalid file was found for exit status.
        found_invalid_file = True

        if not fix:
            print("Missing license:", file_path)

        else:
            print("Adding license...", file_path)

            # update file with license inserted at the top
            # note: may need additional case handling if hash license can't be used.
            contents = _HASH_LICENSE_HEADER + "\n\n" + contents
            with open(file_path, "w") as f:
                f.write(contents)

    if found_invalid_file:
        sys.exit("Found at least one invalid line")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Checks all python files for license headers. Can optionally choose to warn or fix the offending files."
    )

    parser.add_argument("--fix", action=argparse.BooleanOptionalAction)

    args, unknown_args = parser.parse_known_args()

    license_check(fix=args.fix)
