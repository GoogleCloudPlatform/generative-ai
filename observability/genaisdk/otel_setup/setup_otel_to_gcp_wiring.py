"""Configures Open Telemetry wiring to Google Cloud Observability.

Configuring observability for the Gen AI SDK involves two steps:

  1. Ensuring that data is written to Open Telemetry APIs when
     the Gen AI SDK is used.

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
import uuid

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
from opentelemetry.sdk._logs.export import (
    BatchLogRecordProcessor,
    ConsoleLogExporter,
    SimpleLogRecordProcessor,
)
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import (
    OsResourceDetector,
    OTELResourceDetector,
    ProcessResourceDetector,
    Resource,
    get_aggregated_resources,
)
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

# Replace this with a better default for your service.
_DEFAULT_SERVICE_NAMESPACE = "default"

# Replace this with a better default for your service.
_DEFAULT_SERVICE_NAME = "genaisdk-observability-sample"

# Replace this with a better default for your service.
_DEFAULT_LOG_NAME = "genaisdk-observability-sample"


# Allows the service name to be changed dynamically at runtime, using
# the standard Open Telemetry environment variable for setting it. This
# can be useful to support different deployments of your service using
# different names (e.g. to set a different service name in non-prod vs
# in production environments, for example, to differentiate them).
def _get_service_name() -> str:
    """Retrieve the service name for use in the 'service.name' resource attribute."""
    from_env = os.getenv("OTEL_SERVICE_NAME")
    if from_env:
        return from_env
    return _DEFAULT_SERVICE_NAME


def _compute_service_instance_id() -> str:
    """Determines the value to use for the 'service.instance.id' resource attribute."""
    # Implementation note: you may want to report something more meaningful, like the instance ID
    # of the host VM, the PID, or something else. Here we just use something random for expediency.
    # We need to supply something to provide this mandatory resource attribute, but there are
    # different ways that you could reasonably populate it, some more valuable than others.
    return uuid.uuid4().hex


# Used to cache the instance ID so that repeated calls to "_get_service_instance()" below
# return a consistent, predictable, stable output.
_SERVICE_INSTANCE_ID = _compute_service_instance_id()


def _get_service_instance() -> str:
    """Retrieve the instance ID value to use in the 'service.instance.id' resource attribute."""
    return _SERVICE_INSTANCE_ID


# Allows the default log name to be set dynamically.
def _get_default_log_name() -> str:
    """Retrieve the default log name to use with Cloud Logging.

    In Cloud Logging, every log has a "log name" which is part of the
    overall "LOG_ID", which identifies a stream of logs. The CloudLoggingExporter
    can derive the "log name" from a special "gcp.log_name" attribute if present.
    However, when there is no "gcp.log_name" on the LogRecord, the CloudLoggingExporter
    needs a value to use instead when writing the log. This is why there is a
    function to select the default log name to fallback on for that.
    """
    from_env = os.getenv("GCP_DEFAULT_LOG_NAME")
    if from_env:
        return from_env
    return _DEFAULT_LOG_NAME


# Attempts to infer the project ID to use for writing.
def _get_project_id() -> str:
    """Returns the project ID to which to write the telemetry data."""
    env_vars = ["GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT", "GCP_PROJECT"]
    for env_var in env_vars:
        from_env = os.getenv(env_var)
        if from_env:
            return from_env
    _, project = google.auth.default()
    assert project is not None
    assert project
    return project


# Creates an Open Telemetry resource that contains sufficient information
# to be able to successfully write to the Cloud Observability backends.
def _create_resource(project_id: str) -> Resource:
    """Creates an Open Telemetry resource for the given project ID.

    Args:
      project_id: the project ID detected from the environment.

    Returns:
      An Open Telemetry "Resource" that contains attributes representing
      various details about the source of the telemetry data. The resulting
      resource includes the mandatory resource attributes "gcp.project_id"
      and the various mandatory "service.*" resource attributes.
    """
    return get_aggregated_resources(
        detectors=[
            OTELResourceDetector(),
            ProcessResourceDetector(),
            OsResourceDetector(),
        ],
        initial_resource=Resource.create(
            attributes={
                "service.namespace.name": _DEFAULT_SERVICE_NAMESPACE,
                "service.name": _get_service_name(),
                "service.instance.id": _get_service_instance(),
                "gcp.project_id": project_id,
            }
        ),
    )


# [START create_otlp_creds_snippet]
# Creates gRPC channel credentials which can be supplied to the OTLP
# exporter classes provided by Open Telemetry. These build on top
# of the Google Application Default credentials. See also:
# https://cloud.google.com/docs/authentication/application-default-credentials
def _create_otlp_creds() -> grpc.ChannelCredentials:
    """Create gRPC credentials from Google Application Default credentials.

    This returns credentials which can be used with the OTLP exporter. It
    uses the Google Application Default credentials -- ambient credentials
    found in the environment -- to construct the gRPC credentials.
    """
    creds, _ = google.auth.default()
    request = google.auth.transport.requests.Request()
    auth_metadata_plugin = AuthMetadataPlugin(credentials=creds, request=request)
    return grpc.composite_channel_credentials(
        grpc.ssl_channel_credentials(),
        grpc.metadata_call_credentials(auth_metadata_plugin),
    )


# [END create_otlp_creds_snippet]


def _in_debug_mode() -> bool:
    """Returns whether to enable additional debugging."""
    debug_flag = os.getenv("VERBOSE_OTEL_SETUP_DEBUGGING") or ""
    return debug_flag == "true"


def _configure_tracer_provider_debugging(tracer_provider: TracerProvider) -> None:
    """Conditionally adds more debugging to the TracerProvider.

    When additional debugging is requested, the TracerProvider will be configured to
    also dump traces to STDOUT. This makes it possible to triangulate whether issues
    are due to the instrumentation (spans not getting written to the Open Telemetry
    library) or due to the wiring (e.g. failure to export to Cloud Trace).
    """
    if not _in_debug_mode():
        return
    tracer_provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))


def _configure_logger_provider_debugging(logger_provider: LoggerProvider) -> None:
    """Conditionally adds more debugging to the LoggerProvider.

    When additional debugging is requested, the LoggerProvider will be configured to
    also dump logs to STDOUT. This makes it possible to triangulate whether issues
    are due to the instrumentation (logs not getting written to the Open Telemetry library)
    or due to the wiring (e.g. failure to export to Cloud Logging).
    """
    if not _in_debug_mode():
        return
    logger_provider.add_log_record_processor(
        SimpleLogRecordProcessor(ConsoleLogExporter())
    )


# [START setup_cloud_trace_snippet]


# Wire up Open Telemetry's trace APIs to talk to Cloud Trace.
def _setup_cloud_trace(resource: Resource, otlp_creds: grpc.ChannelCredentials) -> None:
    """Configures Open Telemetry to route spans to Cloud Trace."""
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(credentials=otlp_creds))
    )
    _configure_tracer_provider_debugging(tracer_provider)
    trace.set_tracer_provider(tracer_provider)


# [END setup_cloud_trace_snippet]


# [START setup_cloud_monitoring_snippet]


# Wire up Open Telemetry's metric APIs to talk to Cloud Monitoring.
def _setup_cloud_monitoring(project_id: str, resource: Resource) -> None:
    """Configures Open Telemetry to route metrics to Cloud Monitoring."""
    metrics.set_meter_provider(
        MeterProvider(
            metric_readers=[
                PeriodicExportingMetricReader(
                    CloudMonitoringMetricsExporter(
                        project_id=project_id, add_unique_identifier=True
                    ),
                    export_interval_millis=5000,
                )
            ],
            resource=resource,
        )
    )


# [END setup_cloud_monitoring_snippet]


# [START setup_cloud_logging_snippet]
# Wire up Open Telemetry's logging APIs to talk to Cloud Logging.
def _setup_cloud_logging(project_id: str, resource: Resource) -> None:
    """Configures Open Telemetry to route logs and events to Cloud Logging."""
    # Set up the OTel "LoggerProvider" API
    logger_provider = LoggerProvider(resource=resource)
    exporter = CloudLoggingExporter(
        project_id=project_id, default_log_name=_get_default_log_name()
    )
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


def setup_otel_to_gcp_wiring() -> None:
    """Configures Open Telemetry to route telemetry to Cloud Observability."""
    project_id = _get_project_id()
    resource = _create_resource(project_id)
    otlp_creds = _create_otlp_creds()
    _setup_cloud_logging(project_id, resource)
    _setup_cloud_trace(resource, otlp_creds)
    _setup_cloud_monitoring(project_id, resource)


# [END setup_otel_to_gcp_wiring_snippet]
