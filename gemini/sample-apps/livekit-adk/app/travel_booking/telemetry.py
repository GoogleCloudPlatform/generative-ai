import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.resources import Resource

def init_telemetry():
    # Check if we should enable cloud tracing
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project_id:
        print("GOOGLE_CLOUD_PROJECT environment variable not set. Cloud Tracing disabled.")
        return

    service_name = os.environ.get("OTEL_SERVICE_NAME", "shopify-agent-bidi")
    print(f"Initializing Cloud Tracing for project: {project_id}, service: {service_name}")
    
    # Set up the Resource with service name
    resource = Resource.create({"service.name": service_name})
    
    # Configure the Cloud Trace exporter
    try:
        cloud_trace_exporter = CloudTraceSpanExporter(project_id=project_id)
        span_processor = BatchSpanProcessor(cloud_trace_exporter)
        
        current_provider = trace.get_tracer_provider()
        
        # Try to add the span processor to the existing provider
        try:
            current_provider.add_span_processor(span_processor)
            print("Successfully added Cloud Trace span processor to existing TracerProvider.")
        except AttributeError:
            print("Current TracerProvider does not support adding span processors.")
            print("Attempting to set global TracerProvider...")
            try:
                # Create a new provider with resource and processor
                new_provider = TracerProvider(resource=resource)
                new_provider.add_span_processor(span_processor)
                trace.set_tracer_provider(new_provider)
                print("Successfully set global TracerProvider.")
            except Exception as e:
                print(f"Warning: Failed to set global TracerProvider: {e}")
                print("Traces may not be sent to Cloud Trace.")
    except Exception as e:
        print(f"Warning: Failed to initialize Cloud Trace exporter: {e}")
        print("Cloud Tracing disabled.")
