"""Configures Open Telemetry instrumentation for GenAI SDK.

Configuring observability for the GenAI SDK involves two steps:

  1. Ensuring that data is written to Open Telemetry APIs when
     the GenAI SDK is used.
 
  2. Ensuring that the Open Telemetry APIs route data to some
     observability backend(s) for storing the data.

This file addresses #1. This also means that this file can be used
for observability of the GenAI SDK in cases where you choose an
observability backend other than those of Google Cloud Observability.\

See also:
 - https://github.com/open-telemetry/opentelemetry-python-contrib/
      - /instrumentation-genai/opentelemetry-instrumentation-google-genai
         - /examples/manual
"""

from opentelemetry.instrumentation.google_genai import GoogleGenAiSdkInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor


def setup_otel_instrumentation():
   # Instrument the GenAI SDK library (PyPi: "google-genai"). This
   # monkey-patches that library to inject Open Telemetry instrumentation.
   GoogleGenAiSdkInstrumentor().instrument()

   # Instrument the Python Requests library (PyPi: "requests"). This
   # monkey-patches that library to inject Open Telemetry instrumentation.
   # The requests library is a dependency of the GenAI SDK library; it is
   # used to invoke the Vertex API or the Gemini API. Instrumenting this
   # lower-level dependency of the GenAI SDK provides more information
   # about the timing and operation at lower layers of the stack.
   RequestsInstrumentor().instrument()
