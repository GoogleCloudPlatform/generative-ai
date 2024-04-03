# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Get LLM Error Codes"""


def check_exact_error_code_match(error_code, config):
    for code in config["error_codes"]:
        if code == error_code:
            return True
    return False


def get_llm_error_and_category(error_codes, config):
    llm_error_msgs = {}
    for error_code in error_codes:
        error_code = str(int(error_code))
        error_msg = ""

        if check_exact_error_code_match(error_code, config):
            error_msg = config["error_codes"][error_code]
        elif len(error_code) == 3:
            for _ in config["error_codes"]:
                if error_code.startswith("1"):
                    error_msg = config["error_codes"]["1xx"]
                elif error_code.startswith("2"):
                    error_msg = config["error_codes"]["2xx"]
                elif error_code.endswith("00"):
                    error_msg = config["error_codes"]["x00"]
                elif error_code.endswith("20"):
                    error_msg = config["error_codes"]["x20"]
                elif error_code.endswith("30"):
                    error_msg = config["error_codes"]["x30"]
                elif error_code.endswith("31"):
                    error_msg = config["error_codes"]["x31"]
                elif error_code.endswith("40"):
                    error_msg = config["error_codes"]["x40"]
                elif error_code.endswith("50"):
                    error_msg = config["error_codes"]["x50"]
                elif error_code.endswith("51"):
                    error_msg = config["error_codes"]["x51"]
                elif error_code.endswith("52"):
                    error_msg = config["error_codes"]["x52"]
                elif error_code.endswith("53"):
                    error_msg = config["error_codes"]["x53"]
                elif error_code.endswith("54"):
                    error_msg = config["error_codes"]["x54"]
                else:
                    error_msg = "Not Available"
            else:
                error_msg = "Not Available"

        llm_error_msgs[error_code] = error_msg
    return llm_error_msgs
