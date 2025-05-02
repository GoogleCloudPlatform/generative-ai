"""Defines custom HTTP exception classes for the FastAPI application.

This module provides reusable exception classes that inherit from FastAPI's
HTTPException, allowing for standardized error responses with specific
status codes and detail messages.
"""

from fastapi import HTTPException


class ResourceAlreadyExists(HTTPException):
    """
    Custom exception for HTTP 400 Bad Request errors.

    Used specifically when an attempt is made to create a resource that
    already exists (e.g., creating a duplicate configuration).
    Defaults to status code 400.
    """

    def __init__(self, detail="Resource already exists"):
        """Initializes the exception with a default detail message."""
        super().__init__(status_code=400, detail=detail)


class BadRequest(HTTPException):
    """
    Custom exception for general HTTP 400 Bad Request errors.

    Can be used for various client-side errors like invalid input,
    missing required data, or violating business logic rules before
    processing. Defaults to status code 400.

    Note: The default detail message "Resource already exists" seems
    inconsistent with a general BadRequest. Consider changing it to
    a more generic message like "Bad Request" or requiring a specific
    detail message upon instantiation.
    """
    def __init__(self, detail="Resource already exists"):
        super().__init__(status_code=400, detail=detail)
