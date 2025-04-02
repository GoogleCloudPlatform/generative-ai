# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Utilities to check if an exception is retryable for Gen AI SDK generation."""

from google.genai import errors as genai_errors
import requests


def is_retryable_error(exception: BaseException) -> bool:
    """
    Determines if a given exception is considered retryable.

    This function checks if the provided exception is an API error with a retryable HTTP status code
    (429, 502, 503, 504) or a connection error.

    Args:
        exception: The exception to evaluate.

    Returns:
        True if the exception is retryable, False otherwise.
    """

    if isinstance(exception, genai_errors.APIError):
        return exception.code in [429, 502, 503, 504]
    if isinstance(exception, requests.exceptions.ConnectionError):
        return True
    return False
