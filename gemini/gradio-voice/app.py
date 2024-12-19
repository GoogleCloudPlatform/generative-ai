import asyncio
import base64

import gradio as gr
from gradio_webrtc import AsyncStreamHandler, WebRTC, async_aggregate_bytes_to_16bit
import numpy as np
from google import genai


def encode_audio(data: np.ndarray, sample_rate: int) -> str:
    """Encode Audio data to send to the server"""
    return base64.b64encode(data.tobytes()).decode("UTF-8")


class GeminiHandler(AsyncStreamHandler):
    def __init__(
        self, expected_layout="mono", output_sample_rate=24000, output_frame_size=480
    ) -> None:
        super().__init__(
            expected_layout,
            output_sample_rate,
            output_frame_size,
            input_sample_rate=16000,
        )
        self.all_output_data = None
        self.client: genai.Client | None = None
        self.input_queue = asyncio.Queue()
        self.output_queue = asyncio.Queue()
        self.quit = asyncio.Event()

    def copy(self) -> "GeminiHandler":
        return GeminiHandler(
            expected_layout=self.expected_layout,
            output_sample_rate=self.output_sample_rate,
            output_frame_size=self.output_frame_size,
        )

    async def stream(self):
        while not self.quit.is_set():
            audio = await self.input_queue.get()
            yield audio

    async def connect(self, api_key: str):
        client = genai.Client(api_key=api_key)
        config = {"response_modalities": ["AUDIO"]}
        async with client.aio.live.connect(
            model="models/gemini-2.0-flash-exp", config=config
        ) as session:
            async for audio in session.start_stream(
                stream=self.stream(), mime_type="audio/pcm"
            ):
                if audio.data:
                    yield audio.data

    async def receive(self, frame: tuple[int, np.ndarray]) -> None:
        _, array = frame
        array = array.squeeze()
        auio_message = encode_audio(array, self.output_sample_rate)
        self.input_queue.put_nowait(auio_message)

    async def generator(self):
        async for audio_response in async_aggregate_bytes_to_16bit(
            self.connect(self.latest_args[1])
        ):
            self.output_queue.put_nowait(audio_response)

    async def emit(self):
        if not self.args_set.is_set():
            if not self.channel:
                return
            await self.wait_for_args()
            asyncio.create_task(self.generator())

        array = await self.output_queue.get()
        return (self.output_sample_rate, array)

    def reset(self) -> None:
        if hasattr(self, "_generator"):
            delattr(self, "_generator")
        self.all_output_data = None

    def shutdown(self) -> None:
        self.quit.set()


with gr.Blocks() as demo:
    gr.HTML(
        """
        <div style='text-align: center'>
            <h1>Gemini 2.0 Voice Chat</h1>
            <p>Speak with Gemini using real-time audio streaming</p>
            <p>Get a Gemini API key from <a href="https://ai.google.dev/gemini-api/docs/api-key">Google</a></p>
        </div>
    """
    )

    with gr.Row(visible=True) as api_key_row:
        api_key = gr.Textbox(
            label="Gemini API Key",
            placeholder="Enter your Gemini API Key",
            type="password",
        )
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
            inputs=[webrtc, api_key],
            outputs=[webrtc],
            time_limit=90,
            concurrency_limit=2,
        )
    api_key.submit(
        lambda: (gr.update(visible=False), gr.update(visible=True)),
        None,
        [api_key_row, row],
    )


if __name__ == "__main__":
    demo.launch()
