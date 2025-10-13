#  Copyright 2025 Google LLC
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

import asyncio
import os

from google import genai
from google.genai.types import (
    ComputerUse,
    Content,
    Environment,
    FunctionResponse,
    FunctionResponseBlob,
    GenerateContentConfig,
    Part,
    Tool,
)
from playwright.async_api import Page, async_playwright

# --- CONFIGURATION ---
# Load configuration from environment variables for best practice.
PROJECT_ID = os.environ.get("GOOGLE_PROJECT_ID")
LOCATION = os.environ.get("GOOGLE_LOCATION", "global")
MODEL_ID = os.environ.get("MODEL_ID", "gemini-2.5-computer-use-preview-10-2025")


# --- HELPER FUNCTIONS  ---


def normalize_x(x: int, screen_width: int) -> int:
    """Convert normalized x coordinate (0-1000) to actual pixel coordinate."""
    return int(x / 1000 * screen_width)


def normalize_y(y: int, screen_height: int) -> int:
    """Convert normalized y coordinate (0-1000) to actual pixel coordinate."""
    return int(y / 1000 * screen_height)


async def execute_function_calls(
    response, page: Page, screen_width: int, screen_height: int
) -> tuple[str, list[tuple[str, str]]]:
    """Extracts and executes function calls from the model response."""
    await asyncio.sleep(0.1)

    function_calls = [
        part.function_call
        for part in response.candidates[0].content.parts
        if hasattr(part, "function_call") and part.function_call
    ]

    thoughts = [
        part.text
        for part in response.candidates[0].content.parts
        if hasattr(part, "text") and part.text
    ]

    if thoughts:
        print(f"🤔 Model Reasoning: {' '.join(thoughts)}")

    if not function_calls:
        return "NO_ACTION", []

    results = []
    for function_call in function_calls:
        result = None
        print(f"⚡ Executing Action: {function_call.name}")
        try:
            if function_call.name == "open_web_browser":
                result = "success"  # The browser is already open
            elif function_call.name == "navigate":
                await page.goto(function_call.args["url"])
                result = "success"
            elif function_call.name == "click_at":
                actual_x = normalize_x(function_call.args["x"], screen_width)
                actual_y = normalize_y(function_call.args["y"], screen_height)
                await page.mouse.click(actual_x, actual_y)
                result = "success"
            elif function_call.name == "type_text_at":
                text_to_type = function_call.args["text"]
                print(f'[DEBUG] Typing text: "{text_to_type}"')
                actual_x = normalize_x(function_call.args["x"], screen_width)
                actual_y = normalize_y(function_call.args["y"], screen_height)
                await page.mouse.click(actual_x, actual_y)
                await asyncio.sleep(0.1)
                await page.keyboard.type(text_to_type)
                if function_call.args.get("press_enter", False):
                    await page.keyboard.press("Enter")
                result = "success"
            else:
                result = "unknown_function"
        except Exception as e:
            print(f"❗️ Error executing {function_call.name}: {e}")
            result = f"error: {e!s}"
        results.append((function_call.name, result))
    return "CONTINUE", results


# --- THE AGENT LOOP ---


async def agent_loop(initial_prompt: str, max_turns: int = 5) -> None:
    """Main agent loop for local execution with a browser."""
    if not PROJECT_ID:
        raise ValueError("GOOGLE_PROJECT_ID environment variable not set.")

    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    browser = None
    try:
        async with async_playwright() as p:
            # MODIFIED: Launch browser in a try...finally block
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            sw, sh = 960, 1080
            await page.set_viewport_size({"width": sw, "height": sh})

            print(f"🎬 Starting Agent Loop with prompt: '{initial_prompt}'")
            # ... (rest of the loop is fine and remains the same) ...
            config = GenerateContentConfig(
                tools=[
                    Tool(
                        computer_use=ComputerUse(
                            environment=Environment.ENVIRONMENT_BROWSER,
                        )
                    )
                ],
            )
            screenshot = await page.screenshot()
            contents = [
                Content(
                    role="user",
                    parts=[
                        Part(text=initial_prompt),
                        Part.from_bytes(data=screenshot, mime_type="image/png"),
                    ],
                )
            ]
            for turn in range(max_turns):
                print(f"\n--- 🔁 Turn {turn + 1} ---")
                print(f"[DEBUG] Current URL: {page.url}")

                response = client.models.generate_content(
                    model=MODEL_ID, contents=contents, config=config
                )

                if not response.candidates:
                    print("❗️ Model returned no candidates. Terminating loop.")
                    print("Full Response:", response)
                    break

                print(
                    f"[DEBUG] Model Finish Reason: {response.candidates[0].finish_reason}"
                )
                contents.append(response.candidates[0].content)
                print("[DEBUG] Appended model response to history.")

                if not any(
                    hasattr(part, "function_call")
                    for part in response.candidates[0].content.parts
                ):
                    final_text = "".join(
                        part.text
                        for part in response.candidates[0].content.parts
                        if hasattr(part, "text") and part.text is not None
                    )
                    if final_text:
                        print(f"✅ Agent Finished: {final_text}")
                        break

                status, execution_results = await execute_function_calls(
                    response, page, sw, sh
                )
                print(
                    f"[DEBUG] Execution Results: status='{status}', results={execution_results}"
                )

                if status == "NO_ACTION":
                    continue

                function_response_parts = []
                for name, result in execution_results:
                    screenshot = await page.screenshot()
                    current_url = page.url
                    function_response_parts.append(
                        FunctionResponse(
                            name=name,
                            response={"url": current_url},
                            parts=[
                                Part(
                                    inline_data=FunctionResponseBlob(
                                        mime_type="image/png", data=screenshot
                                    )
                                )
                            ],
                        )
                    )
                contents.append(Content(role="user", parts=function_response_parts))
                print(f"📝 State captured. History now has {len(contents)} messages.")

    finally:
        if browser:
            await browser.close()
            print("\n--- Browser closed. ---")


# --- SCRIPT ENTRY POINT ---
if __name__ == "__main__":
    prompt = "Navigate to the Google Store and find the page of 'Pixel 10'."

    asyncio.run(agent_loop(prompt))
