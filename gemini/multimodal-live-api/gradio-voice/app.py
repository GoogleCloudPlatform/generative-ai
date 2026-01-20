import asyncio
import pathlib
from typing import AsyncGenerator, Literal, cast

from fastrtc import AsyncStreamHandler, WebRTC, async_aggregate_bytes_to_16bit
from google import genai
from google.genai.types import (
    Content,
    LiveConnectConfig,
    Part,
    PrebuiltVoiceConfig,
    SpeechConfig,
    VoiceConfig,
)
import gradio as gr
import numpy as np

current_dir = pathlib.Path(__file__).parent


class GeminiHandler(AsyncStreamHandler):
    """Handler for the Gemini API"""

    def __init__(
        self,
        expected_layout: Literal["mono"] = "mono",
        output_sample_rate: int = 24000,
        output_frame_size: int = 480,
        input_sample_rate: int = 16000,
    ) -> None:
        super().__init__(
            expected_layout,
            output_sample_rate,
            output_frame_size,
            input_sample_rate=input_sample_rate,
        )
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.quit: asyncio.Event = asyncio.Event()

    def copy(self) -> "GeminiHandler":
        """Required implementation of the copy method for AsyncStreamHandler"""
        return GeminiHandler(
            expected_layout=cast(Literal["mono"], self.expected_layout),
            output_sample_rate=self.output_sample_rate,
            output_frame_size=self.output_frame_size,
        )

    async def stream(self) -> AsyncGenerator[bytes, None]:
        """Helper method to stream input audio to the server. Used in start_stream."""
        while not self.quit.is_set():
            audio = await self.input_queue.get()
            yield audio
        return

    async def connect(
        self,
        project_id: str,
        location: str,
        voice_name: str | None = None,
        system_instruction: str | None = None,
    ) -> AsyncGenerator[bytes, None]:
        """Connect to the Gemini server and start the stream."""
        client = genai.Client(vertexai=True, project=project_id, location=location)
        config = LiveConnectConfig(
            response_modalities=["AUDIO"],
            speech_config=SpeechConfig(
                voice_config=VoiceConfig(
                    prebuilt_voice_config=PrebuiltVoiceConfig(
                        voice_name=voice_name,
                    )
                )
            ),
            system_instruction=Content(
                parts=[
                    Part.from_text(
                        text=system_instruction or "You are a helpful assistant."
                    )
                ]
            ),
        )
        async with client.aio.live.connect(
            model="gemini-2.0-flash-live-preview-04-09", config=config
        ) as session:
            async for audio in session.start_stream(
                stream=self.stream(), mime_type="audio/pcm"
            ):
                if audio.data:
                    yield audio.data

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        """Receive audio from the user and put it in the input stream."""
        _, array = frame
        array = array.squeeze()
        audio_message = array.tobytes()
        self.input_queue.put_nowait(audio_message)

    async def generator(self) -> None:
        """Helper method for placing audio from the server into the output queue."""
        async for audio_response in async_aggregate_bytes_to_16bit(
            self.connect(*self.latest_args[1:])
        ):
            self.output_queue.put_nowait(audio_response)

    async def emit(self) -> tuple[int, np.ndarray]:
        """Required implementation of the emit method for AsyncStreamHandler"""
        if not self.args_set.is_set():
            await self.wait_for_args()
            asyncio.create_task(self.generator())

        array = await self.output_queue.get()
        return (self.output_sample_rate, array)

    def shutdown(self) -> None:
        """Stop the stream method on shutdown"""
        self.quit.set()


css = (current_dir / "style.css").read_text()
header = (current_dir / "header.html").read_text()

with gr.Blocks(css=css) as demo:
    gr.HTML(header)
    with gr.Group(visible=True, elem_id="api-form") as api_key_row:
        with gr.Row():
            _project_id = gr.Textbox(
                label="Project ID",
                placeholder="Enter your Google Cloud Project ID",
            )
            _location = gr.Dropdown(
                label="Location",
                choices=[
                    "us-central1",
                ],
                value="us-central1",
                info="You can find additional locations [here](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations#united-states)",
            )
            _voice_name = gr.Dropdown(
                label="Voice",
                choices=[
                    "Puck",
                    "Charon",
                    "Kore",
                    "Fenrir",
                    "Aoede",
                ],
                value="Puck",
            )
            _system_instruction = gr.Textbox(
                label="System Instruction",
                placeholder="Talk like a pirate.",
            )
        with gr.Row():
            submit = gr.Button(value="Submit")
    with gr.Row(visible=False) as row:
        webrtc = WebRTC(
            label="Conversation",
            modality="audio",
            mode="send-receive",
            # See for changes needed to deploy behind a firewall
            # https://fastrtc.org/deployment/
            rtc_configuration={},
        )

        webrtc.stream(
            GeminiHandler(),
            inputs=[webrtc, _project_id, _location, _voice_name, _system_instruction],
            outputs=[webrtc],
            time_limit=90,
            concurrency_limit=2,
            send_input_on="submit",
        )
    submit.click(
        lambda: (gr.update(visible=False), gr.update(visible=True)),
        None,
        [api_key_row, row],
    )


if __name__ == "__main__":
    demo.launch()
