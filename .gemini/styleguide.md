# GoogleCloudPlatform/generative-ai Style Guide

The current year is 2026.

## Markdown Style (For `.md` files and `.ipynb` Markdown Cells)

- Use single backticks ( ` ` ) to format inline code elements, such as variable names, function names, enum names, and brief code snippets.
- Add documentation links to the appropriate Vertex AI pages when describing product features. e.g. https://cloud.google.com/vertex-ai/generative-ai/docs
  - Do not reference documentation from the Gemini Developer API, e.g. https://ai.google.dev/ unless there is not a suitable page in the Vertex AI documentation.

The Author block in Notebooks and Markdown should be in a format like this:

For one author:

| Author |
| --- |
| [Firstname Lastname](https://github.com/username) |

For multiple authors

| Authors |
| --- |
| [Firstname Lastname](https://github.com/username) |
| [Firstname Lastname](https://github.com/username) |

## Code Requirements

- Don't include hard-coded Google Cloud project IDs, always use a placeholder like `[your-project-id]`

**Correct**

```py
PROJECT_ID = "[your-project-id]"
```

***Incorrect**

```py
PROJECT_ID = "actual-projectid-1234"
```

## Golden Rule: Use the Correct and Current SDK

Always use the **Google GenAI SDK** (`google-genai`), which is the unified
standard library for all Gemini API requests (AI Studio/Gemini Developer API
and Vertex AI) as of 2025. Do not use legacy libraries and SDKs.

-   **Library Name:** Google GenAI SDK
-   **Python Package:** `google-genai`
-   **Legacy Library**: (`google-generativeai`) is deprecated.

**Installation:**

-   **Incorrect:** `pip install google-generativeai`
-   **Incorrect:** `pip install google-ai-generativelanguage`
-   **Correct:** `pip install google-genai`

**APIs and Usage:**

-   **Incorrect:** `import google.generativeai as genai`-> **Correct:** `from
    google import genai`
-   **Incorrect:** `from google.ai import generativelanguage_v1`  ->
    **Correct:** `from google import genai`
-   **Incorrect:** `from google.generativeai` -> **Correct:** `from google
    import genai`
-   **Incorrect:** `from google.generativeai import types` -> **Correct:** `from
    google.genai import types`
-   **Incorrect:** `import google.generativeai as genai` -> **Correct:** `from
    google import genai`
-   **Incorrect:** `genai.configure(api_key=...)` -> **Correct:** `client =
    genai.Client(api_key='...')`
-   **Incorrect:** `model = genai.GenerativeModel(...)`
-   **Incorrect:** `model.generate_content(...)` -> **Correct:**
    `client.models.generate_content(...)`
-   **Incorrect:** `response = model.generate_content(..., stream=True)` ->
    **Correct:** `client.models.generate_content_stream(...)`
-   **Incorrect:** `genai.GenerationConfig(...)` -> **Correct:**
    `types.GenerateContentConfig(...)`
-   **Incorrect:** `safety_settings={...}` -> **Correct:** Use `safety_settings`
    inside a `GenerateContentConfig` object.
-   **Incorrect:** `from google.api_core.exceptions import GoogleAPIError` ->
    **Correct:** `from google.genai.errors import APIError`
-   **Incorrect:** `types.ResponseModality.TEXT`

## Models

-   By default, use the following models when using `google-genai`:
    -   **General Text & Multimodal Tasks:** `gemini-3-flash-preview`
    -   **Coding and Complex Reasoning Tasks:** `gemini-3-pro-preview`
    -   **Low Latency & High Volume Tasks:** `gemini-2.5-flash-lite`
    -   **Fast Image Generation and Editing:** `gemini-2.5-flash-image` (aka Nano Banana)
    -   **High-Quality Image Generation and Editing:** `gemini-3-pro-image-preview` (aka Nano Banana Pro)
    -   **High-Fidelity Video Generation:** `veo-3.0-generate-001` or `veo-3.1-generate-preview`
    -   **Fast Video Generation:** `veo-3.0-fast-generate-001` or `veo-3.1-fast-generate-preview`
    -   **Advanced Video Editing Tasks:** `veo-3.1-generate-preview`

-   It is also acceptable to use following models if explicitly requested by the
    user:
    -   **Gemini 2.0 Series**: `gemini-2.0-flash`, `gemini-2.0-flash-lite`
    -   **Gemini 2.5 Series**: `gemini-2.5-flash`, `gemini-2.5-pro`

-   Do not use the following deprecated models (or their variants like
    `gemini-1.5-flash-latest`):
    -   **Prohibited:** `gemini-1.5-flash`
    -   **Prohibited:** `gemini-1.5-pro`
    -   **Prohibited:** `gemini-pro`
