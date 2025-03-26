from dotenv import load_dotenv
from google.genai import Client
from otel_setup import setup_otel_instrumentation, setup_otel_to_gcp_wiring


def setup_telemetry():
    setup_otel_to_gcp_wiring()
    setup_otel_instrumentation()


def use_google_genai_sdk():
    client = Client()
    response = client.models.generate_content(
        model="gemini-2.0-flash-lite-001",
        contents="Write a poem about Google GenAI SDK and observability.",
    )
    print(response.text)


def main():
    load_dotenv()
    setup_telemetry()
    use_google_genai_sdk()


if __name__ == "__main__":
    main()
