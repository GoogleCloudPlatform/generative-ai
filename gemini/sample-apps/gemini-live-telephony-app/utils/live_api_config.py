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

from google.genai import types
from utils.prompt import BASE_SYSTEM_INSTRUCTION

def get_live_connect_config(session_handle=None):
    """Loads all parameters for the Gemini Live connection."""
    return types.LiveConnectConfig(
        system_instruction=types.Content(parts=[types.Part(text=BASE_SYSTEM_INSTRUCTION)]),
        response_modalities=["AUDIO"],
        session_resumption=types.SessionResumptionConfig(handle=session_handle),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name="Achird",
                )
            ),
            language_code="en-US",
        ),
        realtime_input_config=types.RealtimeInputConfig(
            automatic_activity_detection=types.AutomaticActivityDetection(
                disabled=False,
                start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                prefix_padding_ms=20,
                silence_duration_ms=150,
            )
        )
    )
