import os

from google import genai
from google.api_core.client_options import ClientOptions
from google.cloud import texttospeech_v1beta1 as texttospeech
from google.genai.chats import Chat
from google.genai.types import GenerateContentConfig, Part
import streamlit as st

# Initialize session state for chat history
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION")

if PROJECT_ID and not LOCATION:
    LOCATION = "us-central1"

MODEL_ID = "gemini-2.0-flash-lite"

LANGUAGE_MAP = {
    "Spanish (Español)": {
        "language_code": "es-US",
        "voice_name": "es-US-Chirp3-HD-Puck",
    },
    "English (Inglés)": {
        "language_code": "en-US",
        "voice_name": "en-US-Chirp3-HD-Fenrir",
    },
}


@st.cache_resource
def load_chat() -> Chat:
    """Load Google Gen AI Client."""
    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    return client.chats.create(
        model=MODEL_ID,
        config=GenerateContentConfig(
            system_instruction="You are an assistant tasked with translating between languages. Only respond with the translation.",
        ),
    )


@st.cache_resource
def load_tts_client() -> texttospeech.TextToSpeechClient:
    """Load Text-to-Speech Client."""
    return texttospeech.TextToSpeechClient(
        client_options=ClientOptions(api_endpoint="us-texttospeech.googleapis.com")
    )


chat = load_chat()

tts_client = load_tts_client()


def play_audio(audio_bytes: bytes) -> None:
    """Plays the audio from a byte stream."""
    if audio_bytes is not None:
        try:
            st.audio(audio_bytes, format="audio/wav", autoplay=True)
        except Exception as e:  # pylint: disable=broad-except
            st.error(f"Error playing audio: {e}")


def generate_audio(text: str, voice_name: str, language_code: str) -> bytes:
    """Generates audio from text using Google Cloud Text-to-Speech."""
    # Perform the text-to-speech request on the text input with the selected
    # voice parameters and audio file type
    response = tts_client.synthesize_speech(
        input=texttospeech.SynthesisInput(text=text),
        voice=texttospeech.VoiceSelectionParams(
            language_code=language_code,
            name=voice_name,
        ),
        audio_config=texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3
        ),
    )
    return response.audio_content


def main() -> None:
    """Main function to run the Streamlit app."""
    st.title("HCA Translator")

    # Add radio button for language direction
    target_language = (
        st.radio(
            "**Output Language:**",
            ("Spanish (Español)", "English (Inglés)"),
        )
        or "Spanish (Español)"
    )

    audio_input = st.audio_input("Record a voice message")

    if audio_input:
        user_input = Part.from_bytes(data=audio_input.getvalue(), mime_type="audio/wav")

        instruction = f"Translate the audio into {target_language}."

        assistant_response = chat.send_message(message=[instruction, user_input]).text

        with st.chat_message("assistant"):
            st.markdown(assistant_response)

        output_audio_bytes = generate_audio(
            assistant_response,
            voice_name=LANGUAGE_MAP[target_language]["voice_name"],
            language_code=LANGUAGE_MAP[target_language]["language_code"],
        )

        if output_audio_bytes:
            play_audio(output_audio_bytes)

        audio_input = None


if __name__ == "__main__":
    main()
