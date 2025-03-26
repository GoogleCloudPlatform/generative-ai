"""Configures Open Telemetry wiring to Google Cloud Observability.

Configuring observability for the GenAI SDK involves two steps:

  1. Ensuring that data is written to Open Telemetry APIs when
     the GenAI SDK is used.
 
  2. Ensuring that the Open Telemetry APIs route data to some
     observability backend(s) for storing the data.

This file addresses #2, for the specific case where the observability
backend(s) of interest are the Google Cloud Observability suite,
consisting of Cloud Trace, Cloud Logging, and Cloud Monitoring.

Note that recommended procedures for integrating with Google Cloud
Observability do change from time to time. For example, this sample
was written shortly after the launch of OTLP-based ingestion for
Cloud Trace (and corresponding sample "samples/otlptrace" in the
github.com/GoogleCloudPlatform/opentelemetry-operations-python repo).
For best practices on integration with Cloud Observability, see:
https://cloud.google.com/stackdriver/docs/instrumentation/setup/python
"""

import os

import google.auth
import google.auth.transport.grpc
from google.auth.transport.grpc import AuthMetadataPlugin
import google.auth.transport.requests
import google.cloud.logging
import grpc
from opentelemetry import metrics, trace
from opentelemetry._events import set_event_logger_provider
from opentelemetry._logs import set_logger_provider
from opentelemetry.exporter.cloud_logging import CloudLoggingExporter
from opentelemetry.exporter.cloud_monitoring import CloudMonitoringMetricsExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._events import EventLoggerProvider
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor, ConsoleLogExporter, SimpleLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, get_aggregated_resources, OTELResourceDetector, OsResourceDetector, ProcessResourceDetector
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, ConsoleSpanExporter

# Replace this with a better default for your service.
_DEFAULT_SERVICE_NAME = "genaisdk-observability-sample"

# Replace this with a better default for your service.
_DEFAULT_LOG_NAME = "genaisdk-observability-sample"


# Allows the service name to be changed dynamically at runtime, using
# the standard Open Telemetry environment variable for setting it. This
# can be useful to support different deployments of your service using
# different names (e.g. to set a different service name in non-prod vs
# in production environments, for example, to differentiate them).
def _get_service_name():
    from_env = os.getenv("OTEL_SERVICE_NAME")
    if from_env:
        return from_env
    return _DEFAULT_SERVICE_NAME


# Allows the default log name to be set dynamically.
def _get_default_log_name():
    from_env = os.getenv("GCP_DEFAULT_LOG_NAME")
    if from_env:
        return from_env
    return _DEFAULT_LOG_NAME


# Attempts to infer the project ID to use for writing.
def _get_project_id():
    env_vars = ["GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GCP_PROJECT"]
    for env_var in env_vars:
        from_env = os.getenv(env_var)
        if from_env:
            return from_env
    _, project = google.auth.default()
    return project


# Creates an Open Telemetry resource that contains sufficient information
# to be able to successfully write to the Cloud Observability backends.
def _create_resource(project_id):
    # A valid project is required for the resource.
    assert project_id is not None
    assert isinstance(project_id, str)
    assert len(project_id) > 0

    # A valid service name is also required for the resource.
    service_name = _get_service_name()
    assert service_name is not None
    assert isinstance(service_name, str)
    assert len(service_name) > 0

    return get_aggregated_resources(
        detectors=[
            OTELResourceDetector(),
            ProcessResourceDetector(),
            OsResourceDetector(),
        ],
        initial_resource=Resource.create(attributes={
            "service.name": service_name,
            "gcp.project_id": project_id,
        })
    )

# [START create_otlp_creds_snippet]

# Creates gRPC channel credentials which can be supplied to the OTLP
# exporter classes provided by Open Telemetry. These build on top
# of the Google Application Default credentials. See also:
# https://cloud.google.com/docs/authentication/application-default-credentials
def _create_otlp_creds():
    creds, _ = google.auth.default()
    request = google.auth.transport.requests.Request()
    auth_metadata_plugin = AuthMetadataPlugin(credentials=creds, request=request)
    return grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.metadata_call_credentials(auth_metadata_plugin),
    )

# [END create_otlp_creds_snippet]


def _in_debug_mode():
    debug_flag = os.getenv('VERBOSE_OTEL_SETUP_DEBUGGING') or ''
    return debug_flag == 'true'


def _configure_tracer_provider_debugging(tracer_provider):
    if not _in_debug_mode():
        return
    tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))


def _configure_logger_provider_debugging(logger_provider):
    if not _in_debug_mode():
        return
    logger_provider.add_log_record_processor(SimpleLogRecordProcessor(ConsoleLogExporter()))


# [START setup_cloud_trace_snippet]

# Wire up Open Telemetry's trace APIs to talk to Cloud Trace.
def _setup_cloud_trace(resource, otlp_creds):
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(credentials=otlp_creds))
    )
    _configure_tracer_provider_debugging(tracer_provider)
    trace.set_tracer_provider(tracer_provider)

# [END setup_cloud_trace_snippet]


# [START setup_cloud_monitoring_snippet]

# Wire up Open Telemetry's metric APIs to talk to Cloud Monitoring.
def _setup_cloud_monitoring(project_id, resource):
    metrics.set_meter_provider(
        MeterProvider(
            metric_readers=[
                PeriodicExportingMetricReader(
                    CloudMonitoringMetricsExporter(
                        project_id=project_id,
                        add_unique_identifier=True),
                    export_interval_millis=5000,
                )
            ],
            resource=resource,
        )
    )

# [END setup_cloud_monitoring_snippet]

# [START setup_cloud_logging_snippet]

# Wire up Open Telemetry's logging APIs to talk to Cloud Logging.
def _setup_cloud_logging(project_id, resource):
    # Set up the OTel "LoggerProvider" API
    logger_provider = LoggerProvider(resource=resource)
    exporter = CloudLoggingExporter(
        project_id=project_id,
        default_log_name=_get_default_log_name())
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(exporter))
    _configure_logger_provider_debugging(logger_provider)
    set_logger_provider(logger_provider)

    # Set up the OTel "EventLoggerProvider" API
    set_event_logger_provider(EventLoggerProvider(logger_provider=logger_provider))

    # Set up the Python "logging" API
    logging_client = google.cloud.logging.Client(project=project_id)
    logging_client.setup_logging()

# [END setup_cloud_logging_snippet]


# [START setup_otel_to_gcp_wiring_snippet]

def setup_otel_to_gcp_wiring():
    project_id = _get_project_id()
    resource = _create_resource(project_id)
    otlp_creds = _create_otlp_creds()
    _setup_cloud_logging(project_id, resource)
    _setup_cloud_trace(resource, otlp_creds)
    _setup_cloud_monitoring(project_id, resource)

# [END setup_otel_to_gcp_wiring_snippet]