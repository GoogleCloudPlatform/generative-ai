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

logger = logging.getLogger(__name__)

def save_transcription(user_text, gemini_text):
    """
    Appends a formatted transcription of a single conversational turn to a text file.

    This function takes the transcribed text from the user and the generated text from
    the Gemini model and appends them to 'transcription.txt'. Each turn is separated
    by '---' for readability. This file is used to maintain conversation history
    for the duration of a single call.

    Args:
        user_text (str): The transcribed text from the user's speech.
        gemini_text (str): The transcribed text from the Gemini model's speech.
    """
    print(f"--- save_transcription called ---")
    logger.info(f"Saving transcription: user_text='{user_text}', gemini_text='{gemini_text}'")
    if not user_text and not gemini_text:
        logger.warning("Both user_text and gemini_text are empty. Nothing to save.")
        return
    with open("transcription.txt", "a", encoding="utf-8") as f:
        if user_text:
            f.write(f"User: {user_text}\n")
        if gemini_text:
            f.write(f"Gemini: {gemini_text}\n")
        f.write("---\n")
    logger.info("Transcription saved successfully.")
    print("--- transcription saved ---")
