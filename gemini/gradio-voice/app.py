import asyncio
import base64
import pathlib
from typing import AsyncGenerator

from google import genai
from google.genai.types import LiveConnectConfig
import gradio as gr
from gradio_webrtc import AsyncStreamHandler, WebRTC, async_aggregate_bytes_to_16bit
import numpy as np


current_dir = pathlib.Path(__file__).parent


def encode_audio(data: np.ndarray) -> str:
    """Encode Audio data to send to the server"""
    return base64.b64encode(data.tobytes()).decode("UTF-8")


class GeminiHandler(AsyncStreamHandler):
    """Handler for the Gemini API"""

    def __init__(
        self, expected_layout="mono", output_sample_rate=24000, output_frame_size=480
    ) -> None:
        super().__init__(
            expected_layout,
            output_sample_rate,
            output_frame_size,
            input_sample_rate=16000,
        )
        self.client: genai.Client | None = None
        self.input_queue: asyncio.Queue = asyncio.Queue()
        self.output_queue: asyncio.Queue = asyncio.Queue()
        self.quit: asyncio.Event = asyncio.Event()

    def copy(self) -> "GeminiHandler":
        """Required implementation of the copy method for AsyncStreamHandler"""
        return GeminiHandler(
            expected_layout=self.expected_layout,
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
        self, project_id: str, location: str
    ) -> AsyncGenerator[bytes, None]:
        """Connect to to genai server and start the stream"""
        client = genai.Client(vertexai=True, project=project_id, location=location)
        config = LiveConnectConfig(response_modalities=["AUDIO"])
        async with client.aio.live.connect(
            model="gemini-2.0-flash-exp", config=config
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
        audio_message = encode_audio(array)
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
            project_id_ = gr.Textbox(
                label="Project ID",
                placeholder="Enter your Google Cloud Project ID",
            )
            location_ = gr.Textbox(
                label="Location",
                placeholder="Enter the location of your project, e.g. us-central1",
            )
        with gr.Row():
            submit = gr.Button(value="Submit")
    with gr.Row(visible=False) as row:
        webrtc = WebRTC(
            label="Conversation",
            modality="audio",
            mode="send-receive",
            # See for changes needed to deploy behind a firewall
            # https://freddyaboulton.github.io/gradio-webrtc/deployment/
            rtc_configuration=None,
        )

        webrtc.stream(
            GeminiHandler(),
            inputs=[webrtc, project_id_, location_],
            outputs=[webrtc],
            time_limit=90,
            concurrency_limit=2,
        )
    submit.click(
        lambda: (gr.update(visible=False), gr.update(visible=True)),
        None,
        [api_key_row, row],
    )


if __name__ == "__main__":
    demo.launch()
