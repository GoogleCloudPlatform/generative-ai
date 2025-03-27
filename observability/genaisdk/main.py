import logging
from dotenv import load_dotenv
from google.genai import Client
from otel_setup import setup_otel_instrumentation, setup_otel_to_gcp_wiring


# [START main_logic_support_snippet]
def setup_telemetry() -> None:
    """Initializes Open Telemetry instrumentation and wiring.

    This ensures that:

      1. The Gen AI SDK and its relevant dependencies collect and
         emit telemetry data to the Open Telemetry API (library).

      2. The Open Telemetry library is configured and initialized
         so that the API is wired up with the Google Cloud Observability
         suite rather than the default no-op implementation.
    """
    setup_otel_to_gcp_wiring()
    setup_otel_instrumentation()


def use_google_genai_sdk() -> None:
    """An example function using the Gen AI SDK."""
    client = Client()
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite-001",
        contents="Write a poem about the Google Gen AI SDK and observability.",
    )
    print(response.text)

# [END main_logic_support_snippet]


def main() -> None:
    """Main program entrypoint.
    
    This does the following:

      1. Loads relevant configuration, including
         initializing the environment from *.env
         files as needed. Some of these environment
         configurations affect telemetry behavior.

      2. Initializes the telemetry instrumentation.

      3. Actually does the core program logic (involving
         some use of the Google Gen AI SDK).
    """
    load_dotenv()
    # [START main_logic_snippet]
    setup_telemetry()
    use_google_genai_sdk()
    # [END main_logic_snippet]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
