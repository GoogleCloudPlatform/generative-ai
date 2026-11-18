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

import base64
import inspect
import json
import logging
import time
from collections.abc import Callable
from typing import Any

from websockets.exceptions import ConnectionClosed

from . import genmedia
from .agent import MODE_NOTES, PROACTIVE_NOTES
from .models import (
    FunctionCall,
    GeneratedMediaMessage,
    GenerationErrorMessage,
    GenerationStartedMessage,
    ModeRequest,
    PaperRequest,
    SceneEvent,
    UploadRemove,
    UploadRequest,
)
from .tools import TOOLS, SessionState, current_session

logger = logging.getLogger("voxplore.toolrunner")

TOOLS_BY_NAME: dict[str, Callable] = {tool.__name__: tool for tool in TOOLS}

SCENE_EVENT_INTERVAL_SECONDS = 1.5
SCENE_EVENT_MAX_CHARS = 300


def media_kind(tool_name: str) -> str:
    if tool_name in ("ask_paper", "find_paper", "prepare_questions"):
        return "paper"
    if "scene" in tool_name:
        return "scene"
    return "video" if "video" in tool_name else "image"


def media_model(kind: str) -> str:
    return {
        "image": genmedia.image_model,
        "video": genmedia.video_model,
        "scene": genmedia.scene_model,
        "paper": genmedia.paper_model,
    }[kind]()


def shown_prompt(tool_name: str, args: dict) -> str:
    text = str(
        args.get("instruction")
        or args.get("prompt")
        or args.get("description")
        or args.get("subject")
        or args.get("request")
        or args.get("question")
        or args.get("query")
        or args.get("role")
        or ""
    ).strip()
    return f"Edit: {text}" if tool_name.startswith("edit_") else text


async def send_tool_response(vertex_ws: Any, call: FunctionCall, response: dict):
    message = {
        "toolResponse": {
            "functionResponses": [
                {"id": call.id, "name": call.name, "response": response}
            ]
        }
    }
    await vertex_ws.send(json.dumps(message))


async def notify_model(vertex_ws: Any, text: str):
    """Tells the model as realtime text; clientContent only seeds history on this model."""
    await vertex_ws.send(json.dumps({"realtimeInput": {"text": text}}))


async def run_function_call(
    call: FunctionCall, state: SessionState, client_ws: Any, vertex_ws: Any
):
    """Runs one tool call in the background and streams the result to the browser and the model."""
    args = dict(call.args or {})
    kind = media_kind(call.name)
    prompt = shown_prompt(call.name, args)
    logger.info(f"Tool call {call.name} ({call.id}): {json.dumps(args)}")

    # answer now so the avatar keeps talking; the wording stops it announcing a result that is not there yet
    waiting = (
        f"The {kind} has only started generating. It is NOT ready and the user cannot see it yet. "
        "Say in one short sentence that you are working on it, then keep teaching the topic while "
        "it is being made. Do not say that it is ready, shown or done until you receive a message "
        "saying that it is displayed."
    )
    if kind == "paper":
        waiting = (
            "The paper is being consulted and the answer is NOT available yet. Say in one short sentence "
            "that you are checking the paper. Do not answer from memory: wait for the message that "
            "carries the answer."
        )
    if call.name == "show_paper_part":
        waiting = (
            "That part of the paper is being fetched and is NOT displayed yet. Say in one short sentence "
            "that you are opening it, and wait for the message that says it is displayed."
        )
    if call.name == "prepare_questions":
        waiting = (
            "The questions are being prepared from the paper and are NOT available yet. Say in one short "
            "sentence that you are getting ready, and ask the user to start with their one-minute "
            "summary of the paper meanwhile."
        )
    if call.name == "find_paper":
        waiting = (
            "The paper is being looked up and read. It is NOT loaded yet. Say in one short sentence that "
            "you are fetching it, and wait for the message that says it is loaded."
        )
    await send_tool_response(
        vertex_ws, call, {"status": "in_progress", "message": waiting}
    )
    if call.name == "find_paper":
        await load_paper(
            PaperRequest(query=str(args.get("query") or "")),
            state,
            client_ws,
            vertex_ws,
        )
        return

    model = media_model(kind)
    if call.name == "show_paper_part":
        model = genmedia.paper_model()
    if call.name == "generate_illustrated_scene":
        model = f"{genmedia.image_model()} + {genmedia.reader_model()}"
    started = GenerationStartedMessage(
        id=call.id or "", kind=kind, tool=call.name, model=model, prompt=prompt
    )
    try:
        await client_ws.send(json.dumps({"generationStarted": started.model_dump()}))
    except ConnectionClosed:
        return
    started_at = time.monotonic()

    tool = TOOLS_BY_NAME.get(call.name)
    token = current_session.set(state)
    try:
        if tool is None:
            raise ValueError(f"Unknown tool: {call.name}")
        accepted = {
            name: value
            for name, value in args.items()
            if name in inspect.signature(tool).parameters
        }
        media = await tool(**accepted)
    except Exception as e:
        logger.exception(f"{call.name} ({call.id}) failed")
        error = GenerationErrorMessage(id=call.id or "", kind=kind, message=str(e))
        try:
            await client_ws.send(json.dumps({"generationError": error.model_dump()}))
            failure = f"The {kind} generation failed with this error: {e}."
            if kind == "paper":
                failure = f"The paper could not be consulted: {e}."
            await notify_model(
                vertex_ws,
                f"{failure} Tell the user in one short sentence and offer to try again.",
            )
        except ConnectionClosed:
            pass
        return
    finally:
        current_session.reset(token)

    duration_ms = int((time.monotonic() - started_at) * 1000)
    if isinstance(media, str):
        # a text answer, not media: nothing to display, the avatar says it
        logger.info(f"{call.name} ({call.id}) done in {duration_ms} ms: {media}")
        try:
            await client_ws.send(
                json.dumps(
                    {"activityDone": {"id": call.id or "", "durationMs": duration_ms}}
                )
            )
            said = (
                f'Answer from the paper to "{prompt}": {media} '
                "Tell the user this in your own words, in a few short sentences."
            )
            if call.name == "prepare_questions":
                said = (
                    f"You now play {prompt}. These are your questions, each with what the paper says in "
                    f"brackets, which is for you only: {media} Ask one question at a time, in your own "
                    "words, and wait for the answer. After each answer react in one sentence, and say so "
                    "when it differs from what the paper says. After the last one, give two things they "
                    "did well and one to improve."
                )
            await notify_model(vertex_ws, said)
        except ConnectionClosed:
            pass
        return

    logger.info(
        f"{call.name} ({call.id}) done in {duration_ms} ms: {media.mime_type}, {len(media.data)} bytes"
    )
    ready = f'The {kind} for "{prompt}" is now displayed to the user. Tell them it is ready in one short sentence.'
    result_prompt = prompt
    if media.kind == "scene":
        description = str(args.get("description") or "")
        if call.name == "edit_interactive_scene":
            description = f"{state.last_scene_description} Then changed: {args.get('instruction', '')}".strip()
        state.last_scene_description = description
        state.last_scene_id = call.id
        state.scene_fix_used = False
        ready += " Invite them to click its parts or move its sliders."
        if call.name == "generate_illustrated_scene":
            ready = (
                f'The illustration of "{prompt}" is now displayed to the user, with its parts clickable. '
                "Tell them in one short sentence, and invite them to click a part or to press Quiz me."
            )
        if media.source:
            ready += (
                f" It was built from {media.source.label} on page {media.source.page} of the paper. Say that "
                "they can open that page next to it with the Show in paper button, to compare."
            )
    if call.name == "show_paper_part":
        ready = part_shown(media.source)
        result_prompt = f"{media.source.label}, page {media.source.page} of the paper"
    if media.note:
        ready = (
            f"The user's picture is now displayed with markings on it. This is what was found: {media.note} "
            "Explain it to the user in one or two short sentences."
        )
    result = GeneratedMediaMessage(
        id=call.id or "",
        kind=media.kind,
        mime_type=media.mime_type,
        data=media.base64,
        prompt=result_prompt,
        tool=call.name,
        model=model,
        duration_ms=duration_ms,
    )
    if media.source and media.kind == "scene":
        result.source_label, result.source_page = media.source.label, media.source.page
        result.source_image = base64.b64encode(media.source.image).decode("ascii")
    try:
        await client_ws.send(
            json.dumps(
                {"generatedMedia": result.model_dump(by_alias=True, exclude_none=True)}
            )
        )
        await notify_model(vertex_ws, ready)
    except ConnectionClosed:
        logger.info(f"Session closed before the {kind} ({call.id}) could be delivered.")


async def handle_scene_event(
    event: SceneEvent, state: SessionState, client_ws: Any, vertex_ws: Any
):
    """Relays what the user did in an interactive scene to the model, or repairs a scene that failed."""
    if event.type == "error":
        await repair_scene(event, state, client_ws)
        return

    now = time.monotonic()
    if now - state.last_scene_event_at < SCENE_EVENT_INTERVAL_SECONDS:
        return
    state.last_scene_event_at = now

    name = (event.name or "interaction")[:SCENE_EVENT_MAX_CHARS]
    detail = (
        json.dumps(event.detail)[:SCENE_EVENT_MAX_CHARS]
        if event.detail is not None
        else ""
    )
    logger.info(f"Scene event ({event.id}): {name} {detail}")
    try:
        await notify_model(
            vertex_ws,
            f"In the interactive scene the user just did this: {name} {detail}. "
            "React as a tutor in one or two short sentences.",
        )
    except ConnectionClosed:
        pass


async def repair_scene(event: SceneEvent, state: SessionState, client_ws: Any):
    """One automatic fix per scene; the corrected scene replaces the card with the same id."""
    if event.id != state.last_scene_id or state.scene_fix_used or not state.last_scene:
        return
    if state.last_scene_type != "code":
        logger.warning(f"Scene ({event.id}) reported an error: {event.message}")
        return
    state.scene_fix_used = True
    logger.warning(
        f"Scene ({event.id}) failed in the browser: {event.message}. Asking for a fix."
    )
    try:
        source = await genmedia.fix_scene(
            state.last_scene, event.message or "unknown error"
        )
    except Exception:
        logger.exception(f"Scene fix ({event.id}) failed")
        return
    state.last_scene = source
    media = genmedia.scene_media(source)
    result = GeneratedMediaMessage(
        id=event.id or "", kind=media.kind, mime_type=media.mime_type, data=media.base64
    )
    try:
        await client_ws.send(
            json.dumps({"generatedMedia": result.model_dump(by_alias=True)})
        )
    except ConnectionClosed:
        pass


def part_shown(page: Any) -> str:
    return (
        f"{page.label} from page {page.page} of the paper is now displayed to the user, as it appears in the "
        "paper. Say in one or two short sentences what it shows. Then ask what they would like to do with "
        "it: hear more about it, or try an interactive version, and in that case what they would like to be "
        "able to change. Do not build anything until they answer."
    )


async def load_paper(
    request: PaperRequest, state: SessionState, client_ws: Any, vertex_ws: Any
):
    """Reads a paper the user uploaded or linked, and gives the avatar a digest of it."""
    name = request.name or request.url or request.query or "paper"
    started_at = time.monotonic()
    found_with = ""
    try:
        await client_ws.send(
            json.dumps(
                {
                    "paperStatus": {
                        "state": "loading",
                        "name": name,
                        "model": genmedia.paper_model(),
                    }
                }
            )
        )
        await notify_model(
            vertex_ws,
            f"The user is loading a research paper ({name}). It is being read now and is "
            "NOT ready yet: you will be told its title and content in a few seconds. Do "
            "not ask the user for its title or its topic. If they speak about it before "
            "then, say in one short sentence that you are still reading it.",
        )
        if request.data:
            paper = (
                "application/pdf",
                genmedia.checked_pdf(base64.b64decode(request.data)),
            )
        else:
            reference = (request.url or request.query or "").strip()
            if not reference:
                raise ValueError("No paper was given")
            try:
                address = genmedia.paper_url(reference)
            except ValueError:
                if request.url:
                    raise
                # a title or a description: look it up
                address, found_with = await genmedia.find_paper(reference)
            try:
                paper = await genmedia.fetch_paper(address)
            except ValueError:
                raise
            except Exception as e:
                # this machine cannot download it (proxy, firewall): the model reads it from its address
                logger.warning(
                    f"Could not download {address} ({e}); passing the address to the model"
                )
                paper = ("application/pdf", address)
        digest = await genmedia.digest_paper(paper)
    except ConnectionClosed:
        return
    except Exception as e:
        logger.exception("Loading the paper failed")
        try:
            await client_ws.send(
                json.dumps(
                    {
                        "paperStatus": {
                            "state": "failed",
                            "name": name,
                            "message": str(e),
                        }
                    }
                )
            )
            await notify_model(
                vertex_ws,
                f"The user tried to load a research paper but it failed: {e}. "
                "Tell them in one short sentence.",
            )
        except ConnectionClosed:
            pass
        return

    state.paper = paper
    state.paper_title = digest["title"]
    status = {
        "state": "ready",
        "name": name,
        "title": digest["title"],
        "summary": digest["summary"],
        "keyPoints": digest["key_points"],
        "parts": digest["parts"],
        "figureCount": digest["figure_count"],
        "foundWith": found_with,
        "durationMs": int((time.monotonic() - started_at) * 1000),
    }
    points = " ".join(
        f"({i + 1}) {point}" for i, point in enumerate(digest["key_points"])
    )
    parts = (
        "; ".join(f"{part['label']}: {part['shows']}" for part in digest["parts"])
        or "not listed"
    )
    figures = (
        f"The paper has {digest['figure_count']} figures. "
        if digest["figure_count"]
        else ""
    )
    try:
        await client_ws.send(json.dumps({"paperStatus": status}))
        await notify_model(
            vertex_ws,
            f'The user loaded a research paper titled "{digest["title"]}". '
            f"Summary: {digest['summary']} Key points: {points} "
            f"Some of its parts: {parts}. {figures}"
            "This is a selection: the user can ask for any other figure, table, "
            "equation or section by its name, and you can show or build it. "
            "Tell the user you have read it, give the main idea in two short sentences, "
            "and ask openly what they would like to explore: how it works, what it "
            "found, or something to try themselves. Do not choose a part for them and "
            "do not list figure numbers.",
        )
    except ConnectionClosed:
        pass


async def set_mode(request: ModeRequest, vertex_ws: Any):
    """Tells the live model which mode the user switched to in the app."""
    notes = []
    if request.preset in MODE_NOTES:
        notes.append(MODE_NOTES[request.preset])
    if request.proactive is not None:
        notes.append(PROACTIVE_NOTES[request.proactive])
    if not notes:
        return
    try:
        await notify_model(
            vertex_ws,
            " ".join(notes) + " Do not announce this change; apply it from now on.",
        )
    except ConnectionClosed:
        pass


MAX_UPLOADS = 8


async def add_upload(request: UploadRequest, state: SessionState, vertex_ws: Any):
    """Keeps a picture the user uploaded as a reference for later generations, and shows it to the avatar."""
    if not request.mime_type.startswith("image/") or len(state.uploads) >= MAX_UPLOADS:
        return
    state.uploads.append((request.mime_type, base64.b64decode(request.data)))
    state.upload_names.append(request.name)
    number = len(state.uploads)
    try:
        await vertex_ws.send(
            json.dumps(
                {
                    "realtimeInput": {
                        "video": {"mimeType": request.mime_type, "data": request.data}
                    }
                }
            )
        )
        await notify_model(
            vertex_ws,
            f"The user uploaded a picture, which you have just been shown. It is image {number} "
            f"({request.name}) of {number} uploaded. Acknowledge it in one short sentence. "
            "Use the uploaded pictures as references when they ask for something made from them.",
        )
    except ConnectionClosed:
        pass


async def remove_upload(request: UploadRemove, state: SessionState, vertex_ws: Any):
    if not 0 <= request.index < len(state.uploads):
        return
    state.uploads.pop(request.index)
    name = state.upload_names.pop(request.index)
    try:
        await notify_model(
            vertex_ws,
            f"The user removed the uploaded picture {name}. {len(state.uploads)} remain, "
            "numbered again from 1 in upload order. Do not comment on this.",
        )
    except ConnectionClosed:
        pass
