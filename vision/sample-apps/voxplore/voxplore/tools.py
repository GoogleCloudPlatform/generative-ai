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

import asyncio
import contextvars
import inspect
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Literal, Optional

from google.genai import types

from . import genmedia
from .genmedia import GeneratedMedia

Frame = Optional[tuple[str, bytes]]


@dataclass
class SessionState:
    last_frame: Frame = None  # latest camera or screen frame sent by the browser
    last_image: Frame = None  # latest generated or edited image
    last_video_interaction: str | None = (
        None  # Omni interaction of the latest video, for edits
    )
    last_scene: str | None = (
        None  # HTML source of the latest interactive scene, for edits and fixes
    )
    last_scene_id: str | None = None
    scene_fix_used: bool = False
    last_scene_event_at: float = 0.0
    last_scene_description: str = ""
    last_scene_type: str = "code"  # code or illustrated
    last_scene_source: Any = None  # the page of the paper the last scene was built from
    paper: Frame = None  # the research paper the user loaded, as a PDF
    paper_title: str = ""
    uploads: list[tuple[str, bytes]] = field(
        default_factory=list
    )  # pictures the user uploaded, in order
    upload_names: list[str] = field(default_factory=list)


# Set by the tool runner around each call, so the tool functions keep model-facing signatures
current_session: contextvars.ContextVar[SessionState] = contextvars.ContextVar(
    "current_session"
)


async def generate_image(
    prompt: str,
    aspect_ratio: Literal["16:9", "9:16", "1:1", "4:3", "3:4"] = "16:9",
    use_current_view: bool = False,
    use_uploads: bool = False,
) -> GeneratedMedia:
    """Generate an image with Nano Banana from a text description. Use it whenever the user asks to
    see, draw, show, sketch, create, make or generate any visual: a picture, photo, illustration,
    diagram, chart, infographic, schema, flowchart, mockup, poster, logo, icon, map or scene. Write
    the prompt in English and describe the subject, setting, style, lighting and composition. For
    diagrams, charts and infographics describe the layout, every element, the labels and the exact
    text to render. Each call creates a new image, so call it again if the user wants another one
    or a variation.

    Args:
        prompt: Detailed description of the image to generate.
        aspect_ratio: Aspect ratio of the image. Use 16:9 unless the user asks otherwise.
        use_current_view: Set to true when the user refers to what they are showing on their camera
            or screen (this object, what you see, my screen, this design). The current frame is
            then used as a reference image.
        use_uploads: Set to true to use the pictures the user uploaded as references. Refer to
            them in the prompt as image 1, image 2, in upload order.
    """
    state = current_session.get()
    references = list(state.uploads) if use_uploads else []
    if use_current_view and state.last_frame:
        references.append(state.last_frame)
    media = await genmedia.generate_image(prompt, aspect_ratio, references or None)
    state.last_image = (media.mime_type, media.data)
    return media


async def generate_video(
    prompt: str,
    aspect_ratio: Literal["16:9", "9:16"] = "16:9",
    use_last_image: bool = False,
    use_current_view: bool = False,
    use_uploads: bool = False,
) -> GeneratedMedia:
    """Generate a short video clip with sound using Gemini Omni from a text description. Use it
    whenever the user asks for a video, clip, animation or something in motion. Write the prompt
    in English and describe the scene, camera movement, lighting, mood and audio. To animate the
    image that was just generated (make a video from it, bring it to life, animate this) set
    use_last_image: the image becomes the first frame, so describe the motion and the camera move
    rather than the scene. Generation takes about a minute, so tell the user you are working on it
    and keep the conversation going. Each call creates a new video, so call it again if the user
    wants another one or a variation.

    Args:
        prompt: Detailed description of the video to generate.
        aspect_ratio: Aspect ratio of the video. Use 16:9 unless the user asks for a vertical video.
        use_last_image: Set to true to animate the most recently generated image: it is used as
            the first frame of the video.
        use_current_view: Set to true when the user refers to what they are showing on their camera
            or screen and wants it in the video. The current frame is then used as a reference.
        use_uploads: Set to true to use the pictures the user uploaded as references. Refer to
            them in the prompt as image 1, image 2, in upload order.
    """
    state = current_session.get()
    reference = None
    if use_last_image and state.last_image:
        reference = state.last_image
        prompt = f"<FIRST_FRAME> {prompt}"
    elif use_uploads and state.uploads:
        reference = list(state.uploads)
    elif use_current_view:
        reference = state.last_frame
    media = await genmedia.generate_video(prompt, aspect_ratio, reference)
    state.last_video_interaction = media.interaction_id
    return media


async def edit_image(instruction: str) -> GeneratedMedia:
    """Edit the most recently generated image (or its latest edit) following the user's instruction:
    change colors, add or remove elements, change the style, the background, the lighting or the
    text. Use it when the user refers to the image that was just made (this image, the picture,
    make it, change it, add, remove). Keep the instruction short, in English, and end it with
    'Keep everything else the same' unless the user wants a big change.

    Args:
        instruction: What to change in the image.
    """
    state = current_session.get()
    if not state.last_image:
        raise RuntimeError("There is no generated image to edit yet")
    media = await genmedia.edit_image(instruction, state.last_image)
    state.last_image = (media.mime_type, media.data)
    return media


async def edit_video(instruction: str) -> GeneratedMedia:
    """Edit or extend the most recently generated video (or its latest edit) following the user's
    instruction. Use it when the user refers to the video that was just made. Simple instructions
    in English work best, for example 'Make the car red. Keep everything else the same.' or
    'Extend this video: the camera pans up to the sky.' Generation takes about a minute, so tell
    the user you are working on it and keep the conversation going.

    Args:
        instruction: What to change in the video, or how to extend it.
    """
    state = current_session.get()
    if not state.last_video_interaction:
        raise RuntimeError("There is no generated video to edit yet")
    media = await genmedia.edit_video(instruction, state.last_video_interaction)
    state.last_video_interaction = media.interaction_id or state.last_video_interaction
    return media


async def generate_interactive_scene(
    description: str,
    topic: str = "",
    use_current_view: bool = False,
    use_paper: bool = False,
) -> GeneratedMedia:
    """Build an interactive 3D scene or 2D simulation that the user can explore, click and adjust
    with sliders. Use it when the user asks for something in 3D, a model to explore or a simulation
    to try: a molecule, the solar system, a geometric solid, a neural network, a pendulum, a graph
    with parameters, gradient descent. Prefer it over generate_image when exact structure matters
    or when the user should experiment. Scenes are built from simple shapes, so do not use it for anatomy,
    animals, plants, places or anything that has to be drawn to look right: use
    generate_illustrated_scene when the user wants to explore such a subject, and generate_image
    or generate_video when they only want to see it. You are told what
    the user clicks and changes in the scene, so you can comment on it. Generation takes a little
    while, so tell the user you are building it and keep the conversation going.

    Args:
        description: In English, what to show, the named parts the user can click and the
            parameters they can change with sliders.
        topic: The subject in two or three lowercase words, for example 'water molecule' or
            'gradient descent'. Leave it empty when the user asks for something specific beyond
            the plain subject.
        use_current_view: Set to true when the scene should be based on what the user is showing
            on their camera or screen, such as a figure, a paper or a poster.
        use_paper: Set to true when the scene should be an interactive version of a part of the
            research paper the user loaded. The description must name the part the user chose,
            such as its figure, equation or section. If they have not chosen one, ask them
            before calling.
    """
    state = current_session.get()
    if use_paper and not state.paper:
        raise RuntimeError(
            "No paper is loaded. The user can load one with the paper button or an arXiv link"
        )
    source = None if use_current_view or use_paper else genmedia.library_scene(topic)
    page = None
    if source is None and use_paper:
        source, page = await asyncio.gather(
            genmedia.generate_scene(description, None, state.paper),
            genmedia.paper_page(description, state.paper),
        )
    elif source is None:
        source = await genmedia.generate_scene(
            description, state.last_frame if use_current_view else None
        )
    state.last_scene = source
    state.last_scene_type = "code"
    state.last_scene_source = page
    media = genmedia.scene_media(source)
    media.source = page
    return media


async def generate_illustrated_scene(
    subject: str, language: str = "English"
) -> GeneratedMedia:
    """Draw a subject and make its parts clickable, so that the user can explore it and be quizzed
    on it. Use it when the user wants to explore or interact with something that has to be drawn
    to look right: the human body, an organ, a cell, an animal, a plant, a machine, a building, a
    landscape, a map-like view of a city with its landmarks, a historical scene. You are told
    which part the user clicks and when they find the part a quiz asked for. Nothing moves in it:
    for something to rotate in 3D or a simulation with parameters, use
    generate_interactive_scene. It takes a little while, so say that you are drawing it.

    Args:
        subject: What to draw, in English, in one detailed sentence: the subject, the view, and
            the parts that must be visible.
        language: The language the user is speaking, in English, for example 'French'. The names
            and explanations of the parts are written in it.
    """
    state = current_session.get()
    page, picture = await genmedia.generate_illustrated_scene(subject, language)
    state.last_scene = page
    state.last_scene_type = "illustrated"
    state.last_scene_source = None
    state.last_image = (picture.mime_type, picture.data)
    return genmedia.scene_media(page)


async def edit_interactive_scene(instruction: str) -> GeneratedMedia:
    """Change the most recent interactive scene following the user's instruction: add or remove
    parts, add a slider, change colors, labels or behavior. Use it when the user refers to the
    scene or simulation that was just made.

    Args:
        instruction: What to change in the scene, in English.
    """
    state = current_session.get()
    if not state.last_scene:
        raise RuntimeError("There is no interactive scene to edit yet")
    if state.last_scene_type == "illustrated":
        raise RuntimeError(
            "An illustrated scene cannot be edited. Call generate_illustrated_scene again with "
            "the subject and the change the user wants"
        )
    source = await genmedia.edit_scene(instruction, state.last_scene)
    state.last_scene = source
    media = genmedia.scene_media(source)
    media.source = state.last_scene_source
    return media


async def annotate_current_view(request: str) -> GeneratedMedia:
    """Check what the user is showing on their camera or screen and mark it up: circle a mistake,
    point at something, write a short correction next to it. Use it when the user shows handwritten
    work, notes, a diagram or their screen and asks you to check it, correct it or point at
    something in it. The result is their own picture with the markings on it, and you are told
    what was found so you can explain it.

    Args:
        request: In English, what the user wants checked or pointed at, in their own words.
    """
    state = current_session.get()
    if not state.last_frame:
        raise RuntimeError("The user is not sharing their camera or screen")
    reading = await genmedia.read_frame(request, state.last_frame)
    prompt = (
        f"Annotate this picture like a teacher marking a student's work with a red pen: {reading['markup']} "
        "Draw only the markings. Keep the picture itself exactly the same."
    )
    media = await genmedia.edit_image(prompt, state.last_frame)
    media.note = reading["finding"]
    state.last_image = (media.mime_type, media.data)
    return media


async def ask_paper(question: str) -> str:
    """Look up the answer to a question in the research paper the user loaded. Use it for any
    detailed question about the paper: its method, results, numbers, figures, limitations, or how
    it differs from other work. Do not answer such questions from memory. The answer is sent to
    you a few seconds later.

    Args:
        question: The user's question about the paper, in English, as a full sentence.
    """
    state = current_session.get()
    if not state.paper:
        raise RuntimeError(
            "No paper is loaded. The user can load one with the paper button or an arXiv link"
        )
    return await genmedia.ask_paper(question, state.paper)


async def show_paper_part(part: str) -> GeneratedMedia:
    """Show the user a figure, a table, an equation or a section of the research paper they
    loaded, as it appears in the paper. Use it only when they ask to see or look at a part of
    the paper.

    Args:
        part: The part to show, by the name the paper uses, for example 'Figure 3' or 'Table 2',
            or a short description of it in English.
    """
    state = current_session.get()
    if not state.paper:
        raise RuntimeError(
            "No paper is loaded. The user can load one with the paper button or an arXiv link"
        )
    return await paper_part_media(part, state)


async def paper_part_media(
    part: str, state: SessionState, page: int | None = None, label: str = ""
) -> GeneratedMedia:
    if not isinstance(state.paper[1], bytes):
        raise RuntimeError(
            "This paper was read from its address, so its pages cannot be shown. Upload the PDF instead"
        )
    found = await genmedia.paper_page(part, state.paper, page, label, crop=True)
    if not found:
        raise RuntimeError(f"{part} could not be found in the paper")
    return GeneratedMedia(
        kind="image", mime_type="image/jpeg", data=found.image, source=found
    )


async def prepare_questions(
    role: str = "a curious attendee from another subfield",
) -> str:
    """Prepare questions about the research paper the user loaded, so that you can play a listener
    while they practice presenting it. Use it when the user wants to practice their talk, their
    poster pitch or their defense, or asks you to question them about their paper.

    Args:
        role: Who you will play, in English, for example 'a curious attendee from another
            subfield', 'a demanding reviewer' or 'a journalist'.
    """
    state = current_session.get()
    if not state.paper:
        raise RuntimeError(
            "No paper is loaded. The user can load one with the paper button or an arXiv link"
        )
    return await genmedia.paper_questions(role, state.paper)


async def find_paper(query: str) -> str:
    """Find a research paper with Google Search and load it, so that you can discuss it. Use it
    when the user names a paper by its title, its authors or its topic and wants to talk about
    it. You are told when it is loaded.

    Args:
        query: The paper's title, or what the user said about it, in English.
    """
    # the tool runner loads the paper itself, because it also updates the browser
    raise RuntimeError("find_paper is handled by the tool runner")


TOOLS: list[Callable] = [
    generate_image,
    generate_video,
    edit_image,
    edit_video,
    generate_interactive_scene,
    generate_illustrated_scene,
    edit_interactive_scene,
    annotate_current_view,
    ask_paper,
    show_paper_part,
    prepare_questions,
    find_paper,
]


def split_docstring(doc: str | None) -> tuple[str, dict[str, str]]:
    """Summary text and one description per parameter, from a docstring with an Args section."""
    summary: list[str] = []
    params: dict[str, str] = {}
    name = None
    in_args = False
    for line in inspect.cleandoc(doc or "").splitlines():
        stripped = line.strip()
        if stripped == "Args:":
            in_args = True
            continue
        if not in_args:
            summary.append(stripped)
        elif ":" in stripped and not line.startswith("        "):
            name, text = stripped.split(":", 1)
            params[name.strip()] = text.strip()
        elif name:
            params[name] = f"{params[name]} {stripped}".strip()
    return " ".join(part for part in summary if part), params


def function_declarations(tools: list[Callable]) -> list[dict]:
    """Live API function declarations built from the tool functions' signatures and docstrings."""
    declarations = []
    for tool in tools:
        # the GEMINI_API option skips the response schema, which the return type cannot express; parameters are the same
        declaration = types.FunctionDeclaration.from_callable_with_api_option(
            callable=tool, api_option="GEMINI_API"
        )
        data = declaration.model_dump(exclude_none=True)
        summary, params = split_docstring(tool.__doc__)
        data["description"] = summary
        for param_name, schema in (
            data.get("parameters", {}).get("properties", {}).items()
        ):
            schema.pop("default", None)
            if param_name in params:
                schema["description"] = params[param_name]
        declarations.append(data)
    return declarations
