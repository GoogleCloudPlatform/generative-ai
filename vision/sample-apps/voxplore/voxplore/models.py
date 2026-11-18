# Copyright 2026 Google LLC
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

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SystemInstructionPart(BaseModel):
    text: str


class SystemInstruction(BaseModel):
    parts: list[SystemInstructionPart]


class PrebuiltVoiceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    voice_name: str = Field(default="puck", alias="voiceName")


class VoiceConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    prebuilt_voice_config: PrebuiltVoiceConfig = Field(
        default_factory=PrebuiltVoiceConfig, alias="prebuiltVoiceConfig"
    )


class SpeechConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    voice_config: VoiceConfig = Field(default_factory=VoiceConfig, alias="voiceConfig")


class AvatarConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    avatar_name: str | None = Field(
        default="Kira",
        alias="avatarName",
        description="Jay, Paul, Sam, Ingrid, Kira, Vera, Ben, Kai, Leo, Carmen, Piper",
    )
    customized_avatar: dict[str, Any] | None = Field(
        default=None, alias="customizedAvatar"
    )


class GenerationConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    response_modalities: list[str] = Field(
        default=["VIDEO"], alias="responseModalities"
    )
    enable_affective_dialog: bool | None = Field(
        default=None, alias="enableAffectiveDialog"
    )
    speech_config: SpeechConfig | None = Field(
        default_factory=SpeechConfig, alias="speechConfig"
    )


class AutomaticActivityDetection(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    disabled: bool | None = False
    start_of_speech_sensitivity: str | None = "START_SENSITIVITY_HIGH"
    end_of_speech_sensitivity: str | None = "END_SENSITIVITY_HIGH"
    prefix_padding_ms: int | None = 20
    silence_duration_ms: int | None = 100


class RealtimeInputConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    automatic_activity_detection: AutomaticActivityDetection | None = Field(
        default_factory=AutomaticActivityDetection
    )


class ProactivityConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    proactive_audio: bool | None = True


class FunctionDeclaration(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    description: str | None = None
    parameters: dict[str, Any] | None = None


class Tool(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    function_declarations: list[FunctionDeclaration] | None = Field(
        default=None, alias="functionDeclarations"
    )


class SetupDetails(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    system_instruction: SystemInstruction | None = Field(
        default=None, alias="systemInstruction"
    )
    model: str = Field(default="gemini-3.8-live")
    generation_config: GenerationConfig = Field(
        default_factory=GenerationConfig, alias="generationConfig"
    )
    avatar_config: AvatarConfig | None = Field(default=None, alias="avatarConfig")
    realtime_input_config: RealtimeInputConfig | None = Field(
        default=None, alias="realtimeInputConfig"
    )
    proactivity: ProactivityConfig | None = Field(default=None)
    tools: list[Tool] | None = None
    input_audio_transcription: dict[str, Any] = Field(
        default_factory=dict, alias="inputAudioTranscription"
    )
    output_audio_transcription: dict[str, Any] = Field(
        default_factory=dict, alias="outputAudioTranscription"
    )


class SetupMessage(BaseModel):
    setup: SetupDetails


class InlineData(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    mime_type: str = Field(alias="mimeType")
    data: str  # Base64 encoded string


class Part(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    text: str | None = None
    inline_data: InlineData | None = Field(default=None, alias="inlineData")


class Content(BaseModel):
    parts: list[Part]
    role: str | None = None


class RealtimeInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    audio: InlineData | None = None
    video: InlineData | None = None
    text: str | None = None


class ClientContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    turns: list[Content]
    turn_complete: bool | None = Field(default=None, alias="turnComplete")


class FunctionResponse(BaseModel):
    id: str | None = None
    name: str
    response: dict[str, Any]
    scheduling: str | None = None


class ToolResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    function_responses: list[FunctionResponse] = Field(alias="functionResponses")


class SceneEvent(BaseModel):
    id: str | None = None
    type: str = (
        "event"  # "event" for a user action, "error" for a script error in the scene
    )
    name: str | None = None
    detail: Any | None = None
    message: str | None = None


class PaperRequest(BaseModel):
    url: str | None = None  # an arXiv identifier or a link to the paper
    query: str | None = None  # a title or a description, looked up with Google Search
    name: str | None = None
    data: str | None = None  # an uploaded PDF, Base64 encoded


class ModeRequest(BaseModel):
    preset: str | None = None  # learning or research
    proactive: bool | None = None


class UploadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    name: str
    mime_type: str = Field(alias="mimeType")
    data: str  # Base64 encoded bytes


class UploadRemove(BaseModel):
    index: int  # position in upload order, from 0


class ClientMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    setup: SetupDetails | None = None
    realtime_input: RealtimeInput | None = Field(default=None, alias="realtimeInput")
    client_content: ClientContent | None = Field(default=None, alias="clientContent")
    tool_response: ToolResponse | None = Field(default=None, alias="toolResponse")
    scene_event: SceneEvent | None = Field(
        default=None, alias="sceneEvent"
    )  # browser to backend only
    paper_request: PaperRequest | None = Field(
        default=None, alias="paperRequest"
    )  # browser to backend only
    mode_request: ModeRequest | None = Field(
        default=None, alias="modeRequest"
    )  # browser to backend only
    upload_request: UploadRequest | None = Field(
        default=None, alias="uploadRequest"
    )  # browser to backend only
    upload_remove: UploadRemove | None = Field(
        default=None, alias="uploadRemove"
    )  # browser to backend only


class ModelTurn(BaseModel):
    parts: list[Part]


class Transcription(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    text: str | None = None
    finished: bool | None = None
    language_code: str | None = Field(default=None, alias="languageCode")


class ServerContent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    model_turn: ModelTurn | None = Field(default=None, alias="modelTurn")
    turn_complete: bool | None = Field(default=None, alias="turnComplete")
    interrupted: bool | None = None
    input_transcription: Transcription | None = Field(
        default=None, alias="inputTranscription"
    )
    output_transcription: Transcription | None = Field(
        default=None, alias="outputTranscription"
    )


class SetupComplete(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class FunctionCall(BaseModel):
    id: str | None = None
    name: str
    args: dict[str, Any] | None = None


class ToolCall(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    function_calls: list[FunctionCall] = Field(
        default_factory=list, alias="functionCalls"
    )


class ToolCallCancellation(BaseModel):
    ids: list[str] = Field(default_factory=list)


class ErrorDetails(BaseModel):
    code: int | None = None
    message: str | None = None
    status: str | None = None


class UsageMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    prompt_token_count: int | None = Field(default=None, alias="promptTokenCount")
    response_token_count: int | None = Field(default=None, alias="responseTokenCount")
    thoughts_token_count: int | None = Field(default=None, alias="thoughtsTokenCount")
    total_token_count: int | None = Field(default=None, alias="totalTokenCount")


class ServerMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    server_content: ServerContent | None = Field(default=None, alias="serverContent")
    setup_complete: SetupComplete | None = Field(default=None, alias="setupComplete")
    tool_call: ToolCall | None = Field(default=None, alias="toolCall")
    tool_call_cancellation: ToolCallCancellation | None = Field(
        default=None, alias="toolCallCancellation"
    )
    usage_metadata: UsageMetadata | None = Field(default=None, alias="usageMetadata")
    error: ErrorDetails | None = None


# Messages from the backend to the browser, in addition to the forwarded Live API messages


class GeneratedMediaMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    id: str
    kind: str  # "image", "video" or "scene" (an HTML document)
    mime_type: str = Field(alias="mimeType")
    data: str  # Base64 encoded bytes
    prompt: str | None = None
    tool: str | None = None
    model: str | None = None
    duration_ms: int | None = Field(default=None, alias="durationMs")
    source_label: str | None = Field(
        default=None, alias="sourceLabel"
    )  # what a scene was built from
    source_page: int | None = Field(default=None, alias="sourcePage")
    source_image: str | None = Field(
        default=None, alias="sourceImage"
    )  # that page of the paper, Base64 JPEG


class GenerationStartedMessage(BaseModel):
    id: str
    kind: str
    tool: str
    model: str | None = None
    prompt: str | None = None


class GenerationErrorMessage(BaseModel):
    id: str
    kind: str
    message: str
