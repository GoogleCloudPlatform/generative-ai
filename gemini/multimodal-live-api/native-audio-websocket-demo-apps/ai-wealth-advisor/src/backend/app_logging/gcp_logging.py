# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging
import sys

from typing import Optional

# import colorlog # Removed: Not used with JSON logging


# from opentelemetry import trace
# from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor  # type: ignore

# from opentelemetry.sdk.resources import Resource
# from opentelemetry.sdk.trace import TracerProvider
# from opentelemetry.sdk.trace.export import BatchSpanProcessor
from pythonjsonlogger import json as json_logger

from backend.app_settings import get_application_settings

app_settings = get_application_settings()


def setup_gcp_logging(log_level: str = "INFO", use_json_logging: bool = True) -> None:
    """
    Setup centralized logging configuration for GCP with appropriate formatting
    and OpenTelemetry instrumentation.

    This configures the root logger so that all other module loggers
    will inherit this configuration.

    Args:
        log_level: The log level to use (NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL)
        use_json_logging: When True, use JSON logging format; when False, use standard text logging
    """
    if app_settings.debug_logging:
        use_json_logging = False
        log_level = "DEBUG"

    # Get the numeric log level from the string
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    # Clear any existing handlers on the root logger
    root_logger = logging.getLogger()

    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create and configure handler
    log_handler = logging.StreamHandler(sys.stdout)

    if use_json_logging:
        # JSON formatter for production/cloud environments
        formatter = json_logger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(otelTraceID)s %(otelSpanID)s %(otelTraceSampled)s",
            rename_fields={
                "levelname": "severity",
                "asctime": "timestamp",
                "name": "logger",
                "otelTraceID": "logging.googleapis.com/trace",
                "otelSpanID": "logging.googleapis.com/spanId",
                "otelTraceSampled": "logging.googleapis.com/trace_sampled",
            },
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )
    else:
        # Standard formatter (without colorlog)
        formatter = logging.Formatter(
            fmt="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%SZ",
        )

    log_handler.setFormatter(formatter)

    # Mute google_adk, google_genai and httpx library logs to reduce noise
    google_adk_logger = logging.getLogger("google_adk")
    google_adk_logger.setLevel("WARNING")

    google_genai_logger = logging.getLogger("google_genai")
    google_genai_logger.setLevel("WARNING")

    httpx_logger = logging.getLogger("httpx")
    httpx_logger.setLevel("WARNING")

    # Configure the root logger
    root_logger.setLevel(numeric_level)
    root_logger.addHandler(log_handler)

    # Clear Uvicorn's default handlers and propagate their logs to the root logger
    # This ensures Uvicorn logs are formatted by the configured handler
    # for uvicorn_logger_name in ["uvicorn", "uvicorn.error", "uvicorn.access"]:
    #     uv_logger = logging.getLogger(uvicorn_logger_name)
    #     uv_logger.handlers.clear()
    #     uv_logger.propagate = True

    # Instrument logging with OpenTelemetry
    LoggingInstrumentor(log_level=logging.DEBUG).instrument()

    # Log a message to confirm setup
    format_type = "JSON" if use_json_logging else "standard text"
    root_logger.info(f"Centralized logging configured at level {log_level} using {format_type} format")


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    Get a logger with the specified name that inherits the centralized configuration.

    This is a convenience function to ensure all loggers use the same configuration.

    Args:
        name: The name of the logger, typically __name__ from the calling module

    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)
