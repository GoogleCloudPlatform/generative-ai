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
import base64
import io
import json
import logging
import os
import re
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote, urlsplit

from google import genai
from google.genai import types

from .auth import get_credentials

logger = logging.getLogger("voxplore.genmedia")

IMAGE_ASPECT_RATIOS = {"1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9"}
VIDEO_ASPECT_RATIOS = {"16:9", "9:16"}

_clients: dict[str, genai.Client] = {}


@dataclass
class PaperPage:
    label: str
    page: int
    image: bytes  # JPEG


@dataclass
class GeneratedMedia:
    kind: str
    mime_type: str
    data: bytes
    interaction_id: str | None = (
        None  # Omni interaction, lets a later edit build on this video
    )
    note: str | None = None  # something for the avatar to say about this result
    source: Optional["PaperPage"] = None  # the page of the paper a scene was built from

    @property
    def base64(self) -> str:
        return base64.b64encode(self.data).decode("ascii")


def use_gemini_api() -> bool:
    return os.environ.get("GENMEDIA_BACKEND", "vertex").lower() == "gemini"


def image_model() -> str:
    return os.environ.get("IMAGE_MODEL", "gemini-nano-banana-2.1")


def video_model() -> str:
    return os.environ.get("VIDEO_MODEL", "gemini-omni-1.2-flash")


def get_client(location: str) -> genai.Client:
    key = "gemini" if use_gemini_api() else location
    if key not in _clients:
        if use_gemini_api():
            _clients[key] = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        else:
            _clients[key] = genai.Client(
                vertexai=True,
                project=os.environ.get("GCP_PROJECT_ID"),
                location=location,
                credentials=get_credentials(),
            )
    return _clients[key]


def _field(obj: Any, name: str):
    if isinstance(obj, dict):
        return obj.get(name)
    return getattr(obj, name, None)


Reference = Optional[
    tuple[str, bytes]
]  # (mime type, bytes) of a frame the user is showing


def as_list(reference: Any) -> list:
    """One reference picture or several, as a list."""
    if not reference:
        return []
    return list(reference) if isinstance(reference, list) else [reference]


def _generate_image_sync(
    prompt: str, aspect_ratio: str | None, reference: Reference = None
) -> GeneratedMedia:
    client = get_client(os.environ.get("IMAGE_MODEL_LOCATION", "global"))
    contents: Any = prompt
    if reference:
        contents = [
            types.Part.from_bytes(data=data, mime_type=mime)
            for mime, data in as_list(reference)
        ] + [prompt]
    response = client.models.generate_content(
        model=image_model(),
        contents=contents,
        config=types.GenerateContentConfig(
            response_modalities=["TEXT", "IMAGE"],
            image_config=types.ImageConfig(aspect_ratio=aspect_ratio)
            if aspect_ratio
            else None,
        ),
    )
    for candidate in response.candidates or []:
        content = candidate.content
        for part in content.parts if content and content.parts else []:
            if part.inline_data and part.inline_data.data:
                return GeneratedMedia(
                    kind="image",
                    mime_type=part.inline_data.mime_type or "image/png",
                    data=part.inline_data.data,
                )
    raise RuntimeError(f"{image_model()} returned no image for this prompt")


def _generate_video_sync(
    prompt: str,
    aspect_ratio: str,
    reference: Reference = None,
    previous_interaction_id: str | None = None,
) -> GeneratedMedia:
    client = get_client(os.environ.get("VIDEO_MODEL_LOCATION", "global"))
    video_input: Any = prompt
    if reference:
        video_input = [
            {
                "type": "image",
                "data": base64.b64encode(data).decode("ascii"),
                "mime_type": mime,
            }
            for mime, data in as_list(reference)
        ]
        video_input.append({"type": "text", "text": prompt})
    request: dict[str, Any] = {
        "model": video_model(),
        "input": video_input,
        "response_format": {
            "type": "video",
            "resolution": os.environ.get("VIDEO_RESOLUTION", "720p"),
        },
        "timeout": float(os.environ.get("VIDEO_TIMEOUT_SECONDS", "600")),
    }
    if previous_interaction_id:
        request["previous_interaction_id"] = previous_interaction_id
    else:
        request["response_format"]["aspect_ratio"] = aspect_ratio
    interaction = client.interactions.create(**request)
    interaction_id = _field(interaction, "id")
    video = _field(interaction, "output_video")
    if video is None:
        status = _field(interaction, "status")
        raise RuntimeError(f"{video_model()} returned no video (status: {status})")

    data = _field(video, "data")
    if data:
        raw = base64.b64decode(data) if isinstance(data, str) else bytes(data)
        return GeneratedMedia(
            kind="video",
            mime_type=_field(video, "mime_type") or "video/mp4",
            data=raw,
            interaction_id=interaction_id,
        )

    uri = _field(video, "uri")
    raise RuntimeError(
        f"{video_model()} returned the video as a URI instead of inline data: {uri}"
    )


async def generate_image(
    prompt: str, aspect_ratio: str | None = None, reference: Reference = None
) -> GeneratedMedia:
    ratio = aspect_ratio if aspect_ratio in IMAGE_ASPECT_RATIOS else "16:9"
    return await asyncio.to_thread(_generate_image_sync, prompt, ratio, reference)


async def generate_video(
    prompt: str, aspect_ratio: str | None = None, reference: Reference = None
) -> GeneratedMedia:
    ratio = aspect_ratio if aspect_ratio in VIDEO_ASPECT_RATIOS else "16:9"
    return await asyncio.to_thread(_generate_video_sync, prompt, ratio, reference)


async def edit_image(instruction: str, source: Reference) -> GeneratedMedia:
    """Edits a previously generated image; the model receives the image and the instruction."""
    return await asyncio.to_thread(_generate_image_sync, instruction, None, source)


async def edit_video(instruction: str, previous_interaction_id: str) -> GeneratedMedia:
    """Edits or extends a previously generated video through the stateful Omni interaction."""
    return await asyncio.to_thread(
        _generate_video_sync, instruction, "16:9", None, previous_interaction_id
    )


FREE_SCENE_INSTRUCTIONS = """You write one self-contained HTML document that shows an interactive 3D scene
or simulation for a learner. A voice tutor is talking with the learner while they use it.

Rules:
- Output only the HTML document. No markdown fences, no commentary.
- For a 3D subject use three.js as ES modules in a single <script type="module">:
  import * as THREE from 'three';
  import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
  The import map is already provided. Do not add one. Use soft lighting and OrbitControls
  with damping. The only other addon available is three/addons/renderers/CSS2DRenderer.js.
- For a flat subject (a curve, a plot, a pendulum, a loss function of one variable) use a plain
  2D canvas with no library, with labeled axes where there are axes.
- Do not load anything from the network.
- The page fills its window: html and body with no margin and 100% height, a full-window
  canvas that follows window resize, dark neutral background.
- Build everything procedurally. No external textures, fonts, models, images or libraries.
  For labels use HTML elements positioned over the canvas.
- Give every meaningful part a short human-readable name (mesh.userData.name in 3D). On a click
  that is not a drag, find the part under the pointer, highlight it, show its name, and call
  window.tutor.event('select', {part: name}).
- If the scene has parameters, add at most three labeled range sliders in a small overlay
  panel. Update the scene on 'input', and on 'change' call
  window.tutor.event('set', {name: parameterName, value: value}).
- When something notable happens in a simulation (it diverges, converges, reaches a limit),
  call window.tutor.event('outcome', {what: shortDescription}) once per occurrence.
- Do not call window.tutor.event for rotation, zoom or any continuous motion.
- Be scientifically accurate in structure, proportions and behavior. Say in a small caption
  when something is not to scale.
- Keep the document under 300 lines.
"""

SCENE_BRIDGE = """<script type="importmap">{"imports":{"three":"/vendor/three.module.js","three/addons/":"/vendor/addons/"}}</script>
<script>
window.tutor = {
  event: function (name, detail) {
    parent.postMessage({ scene: true, type: "event", name: String(name), detail: detail }, "*");
  }
};
window.addEventListener("error", function (e) {
  parent.postMessage({ scene: true, type: "error", message: String(e.message || "a script failed to load") }, "*");
}, true);
window.addEventListener("unhandledrejection", function (e) {
  parent.postMessage({ scene: true, type: "error", message: String(e.reason) }, "*");
});
</script>
"""


EXAMPLE_3D = """const world = stage.three({ camera: [0, 1.2, 5] });
const angle = (104.5 * Math.PI) / 180;
const reach = 1.2;
const oxygen = world.sphere(0.55, 0xe53935, [0, 0.3, 0]);
const left = world.sphere(0.35, 0xf5f5f5, [-reach * Math.sin(angle / 2), 0.3 - reach * Math.cos(angle / 2), 0]);
const right = world.sphere(0.35, 0xf5f5f5, [reach * Math.sin(angle / 2), 0.3 - reach * Math.cos(angle / 2), 0]);
world.bond(oxygen, left);
world.bond(oxygen, right);
world.part(oxygen, 'oxygen atom', 'Oxygen pulls the shared electrons towards itself, so this end is slightly negative.');
world.part(left, 'hydrogen atom', 'Each hydrogen shares one pair of electrons with the oxygen.');
world.part(right, 'hydrogen atom', 'Each hydrogen shares one pair of electrons with the oxygen.');
world.label(oxygen, 'O');
world.label(left, 'H');
world.label(right, 'H');
stage.caption('Water, H2O. The H-O-H angle is 104.5 degrees. Atom sizes are not to scale.');
"""

EXAMPLE_2D = """const loss = (w) => w * w;
const gradient = (w) => 2 * w;
const plot = stage.plot({ x: [-3, 3], y: [-1, 9], xLabel: 'w', yLabel: 'loss' });
const rate = stage.slider('learning rate', 0.01, 1.2, 0.1, 0.01);
const showSteps = stage.readout('steps');
let w = 2.5;
let path = [[w, loss(w)]];
stage.button('Step', () => {
    w = w - rate() * gradient(w);
    path.push([w, loss(w)]);
    if (Math.abs(w) > 3) stage.outcome('the steps overshoot and diverge because the learning rate is too high');
    else if (Math.abs(w) < 0.01) stage.outcome('the steps reached the minimum');
});
stage.button('Reset', () => {
    w = 2.5;
    path = [[w, loss(w)]];
});
plot.draw((g) => {
    g.curve(loss, { color: '#60a5fa' });
    g.path(path, { color: '#fbbf24' });
    g.point(0, 0, { color: '#34d399', name: 'minimum', description: 'The lowest loss, at w = 0.' });
    g.point(w, loss(w), { color: '#f87171', radius: 7, name: 'current weight',
        description: 'Each step moves it by the learning rate times the gradient, downhill.' });
    showSteps(path.length - 1);
});
stage.caption('Update rule: w = w - learning rate x gradient');
"""

STAGE_INSTRUCTIONS = (
    """You write the JavaScript for one interactive scene or simulation for a learner. A voice tutor
is talking with the learner while they use it.

Your code runs as an ES module inside a page that already provides the canvas, camera, lights,
rotate and zoom controls, click selection, the slider panel and the link to the tutor. Two names
are in scope: `stage` (the runtime described below) and `THREE` (three.js). Write only what is
specific to this scene. Output only JavaScript: no HTML, no markdown fences, no commentary, no
imports.

Choose one mode.

3D, for objects in space:
  const world = stage.three({ camera: [x, y, z], target: [0, 0, 0] });
  world.scene, world.camera, world.controls      three.js objects, for anything not covered below
  world.sphere(radius, color, [x, y, z])         adds and returns a mesh
  world.bond(a, b, radius, color)                cylinder between two positions or meshes;
                                                 bond.setEnds(a, b) moves it
  world.line([[x, y, z], ...], color)            polyline
  world.label(meshOrPosition, 'text')            text that follows the object
  world.part(object, 'name', 'one sentence')     makes the object clickable: it is highlighted, its
                                                 name and sentence are shown, and the tutor is told
  Build other shapes with THREE and add them to world.scene.

2D, for curves, plots and flat mechanisms:
  const plot = stage.plot({ x: [min, max], y: [min, max], xLabel, yLabel, axes: true, equal: false });
  Use equal: true when circles must look round. Use axes: false for mechanisms such as a pendulum.
  plot.draw((g) => { ... })                      called every frame after the axes; draw with:
    g.curve((x) => y, { color, width })          a function over the visible x range
    g.path([[x, y], ...], { color, width })
    g.segment(x1, y1, x2, y2, { color, width, dash })
    g.arrow(x1, y1, x2, y2, { color, width })
    g.circle(x, y, radius, { color, fill })      radius in plot units
    g.rect(x, y, width, height, { color, name, description })    x, y is the lower left corner
    g.point(x, y, { color, radius, label, name, description })   radius in pixels
    g.text(x, y, 'text', { color, size, align })
    g.ctx, g.px(x), g.py(y)                      the 2D context and plot-to-pixel conversion
    A point or rect with a name is clickable, like a 3D part.
  plot.onDrag((x, y) => { ... })                 the learner drags on the plot, in plot units
  plot.setRange([min, max], [min, max])

Both modes:
  const value = stage.slider('name', min, max, initial, step, (v) => { ... })
                                                 value() gives the current value
  stage.button('label', () => { ... })
  const show = stage.readout('name'); show(numberOrText)     a live value in the panel
  stage.caption('one line: a formula, or a note that sizes are not to scale')
  stage.onFrame((t, dt) => { ... })              every frame, in seconds
  stage.outcome('short description')             tells the tutor that something notable happened
                                                 (it diverged, converged, reached a limit)
  stage.panel                                    the panel element, for a custom control if needed

Rules:
- Be scientifically accurate in structure, counts, proportions, formulas and behavior.
- Give every meaningful part a short name and one explanatory sentence, so the learner can click it.
- Add at most three sliders, and only for parameters that teach something.
- Clicks, sliders and buttons are reported to the tutor for you. Do not call window.tutor.
- Do not create a renderer, a camera, lights, an animation loop or resize handling. Do not load
  anything from the network.
- Keep it short: most scenes need 30 to 90 lines.

Example, 3D:
"""
    + EXAMPLE_3D
    + """
Example, 2D:
"""
    + EXAMPLE_2D
)

SCENE_SHELL = """<!DOCTYPE html>
<html><head><meta charset="UTF-8">
__BRIDGE__</head><body>
<script type="module">
import * as THREE from 'three';
import '/scene/stage.js';
const stage = window.__stage;
__CODE__
</script>
</body></html>
"""

ILLUSTRATED_PAGE = (
    Path(__file__).resolve().parent / "illustrated_scene.html"
).read_text(encoding="utf-8")

ILLUSTRATION_PROMPT = """__SUBJECT__
A clear, detailed illustration for a learner, with the whole subject in view and its main parts
large, distinct and well separated, on a plain background. No text, no labels, no numbers, no
arrows and no captions anywhere in the picture."""

ILLUSTRATION_PARTS_PROMPT = """This picture was drawn for a learner who asked for: "__SUBJECT__"
List the six to ten most important distinct parts that are clearly visible in it. Return JSON:
{"title": a title of at most five words,
 "parts": [{"name": the name of the part,
            "box_2d": [ymin, xmin, ymax, xmax] on a scale of 0 to 1000 from the top left corner, tight around it,
            "info": one or two sentences a tutor would say about it, at most thirty words}]}
List only what is really drawn, each part once, with boxes that overlap as little as possible.
Write the title, the names and the info in __LANGUAGE__.
"""

LIBRARY_DIR = Path(__file__).resolve().parent.parent / "scene_library"
TOPIC_STOPWORDS = {
    "a",
    "an",
    "the",
    "of",
    "in",
    "3d",
    "2d",
    "interactive",
    "model",
    "simulation",
    "scene",
}


def scene_model() -> str:
    return os.environ.get("SCENE_MODEL", "gemini-4-argon")


def reader_model() -> str:
    return os.environ.get("READER_MODEL", "gemini-3.8-flash")


def free_mode() -> bool:
    """SCENE_MODE=free makes the model write the whole page instead of code for the shared runtime."""
    return os.environ.get("SCENE_MODE", "template").lower() == "free"


def is_page(source: str) -> bool:
    head = source.lstrip()[:2000].lower()
    return head.startswith("<!doctype") or "<html" in head


def _generate_scene_sync(request: str, free: bool, image: Reference = None) -> str:
    client = get_client(os.environ.get("SCENE_MODEL_LOCATION", "global"))
    contents: Any = request
    if image:
        contents = [document_part(image), request]
    # SCENE_THINKING_LEVEL (low or high) trades scene quality for speed on models that reason before answering
    level = os.environ.get("SCENE_THINKING_LEVEL", "").strip()
    response = client.models.generate_content(
        model=scene_model(),
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=FREE_SCENE_INSTRUCTIONS if free else STAGE_INSTRUCTIONS,
            temperature=0.4,
            thinking_config=types.ThinkingConfig(thinking_level=level)
            if level
            else None,
        ),
    )
    text = (response.text or "").strip()
    fenced = re.match(r"^```[a-zA-Z]*\n(.*?)\n?```$", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    if ("<script" if free else "stage.") not in text:
        raise RuntimeError(f"{scene_model()} returned no scene for this request")
    return text


def scene_media(source: str) -> GeneratedMedia:
    """The page the browser runs: the scene's code in the shared shell, or a whole page with the bridge added."""
    if is_page(source):
        head = re.search(r"<head[^>]*>", source, re.IGNORECASE)
        if head:
            end = head.end()
            html = source[:end] + "\n" + SCENE_BRIDGE + source[end:]
        else:
            html = SCENE_BRIDGE + source
    else:
        # the shell already imports these
        code = re.sub(
            r"^\s*import\s+\*\s+as\s+THREE\s+from\s+['\"]three['\"];?\s*$",
            "",
            source,
            flags=re.MULTILINE,
        )
        code = re.sub(
            r"^\s*const\s+stage\s*=\s*window\.__stage;?\s*$",
            "",
            code,
            flags=re.MULTILINE,
        )
        code = code.replace("</script", "<\\/script")
        html = SCENE_SHELL.replace("__BRIDGE__", SCENE_BRIDGE).replace("__CODE__", code)
    return GeneratedMedia(
        kind="scene", mime_type="text/html", data=html.encode("utf-8")
    )


async def generate_scene(
    description: str, image: Reference = None, paper: Reference = None
) -> str:
    """Source of a new interactive scene, optionally based on what the learner is showing or on a loaded paper."""
    request = f"Scene to build:\n{description}"
    if paper:
        request += (
            "\n\nThe attached research paper is the source. Build only the part of it that the request "
            "names, from what the paper describes, with its notation and parameter names. Say in the "
            "caption which figure, equation or section it illustrates, and that it is a simplified "
            "illustration."
        )
    elif image:
        request += "\n\nThe attached picture is what the learner is showing. Base the scene on it."
    return await asyncio.to_thread(
        _generate_scene_sync, request, free_mode(), paper or image
    )


async def edit_scene(instruction: str, source: str) -> str:
    request = (
        f"Current code:\n{source}\n\nChange requested:\n{instruction}\n\n"
        "Return the full updated code."
    )
    return await asyncio.to_thread(_generate_scene_sync, request, is_page(source))


async def fix_scene(source: str, error: str) -> str:
    request = (
        f"Current code:\n{source}\n\nIt failed in the browser with this error:\n{error}\n\n"
        "Fix it and return the full corrected code."
    )
    return await asyncio.to_thread(_generate_scene_sync, request, is_page(source))


def topic_slug(topic: str) -> str:
    words = [
        word
        for word in re.findall(r"[a-z0-9]+", (topic or "").lower())
        if word not in TOPIC_STOPWORDS
    ]
    return "-".join(
        word[:-1] if len(word) > 3 and word.endswith("s") else word for word in words
    )


def library_scene(topic: str) -> str | None:
    """A scene prepared in advance for this topic (see prewarm_scenes.py), if there is one."""
    slug = topic_slug(topic)
    if not slug or os.environ.get("SCENE_LIBRARY", "off").lower() != "on":
        return None
    path = LIBRARY_DIR / f"{slug}.js"
    return path.read_text(encoding="utf-8") if path.is_file() else None


def save_library_scene(topic: str, source: str) -> Path:
    LIBRARY_DIR.mkdir(exist_ok=True)
    path = LIBRARY_DIR / f"{topic_slug(topic)}.js"
    path.write_text(source, encoding="utf-8")
    return path


READER_PROMPT = """A learner is showing this picture to a tutor and says: "__REQUEST__"
Look at the picture carefully and check the work it shows.
Return JSON with two fields:
- "finding": one or two sentences the tutor can say: what is wrong and what the correct version is,
  or that the work is correct.
- "markup": instructions for an illustrator who will draw on this picture with a red pen: exactly
  what to circle, underline or point at, identified by its content and position, and the exact
  short text to write next to it. If the work is correct, ask for a green check mark next to it.
"""


def _illustration_parts_sync(
    subject: str, picture: tuple[str, bytes], language: str
) -> dict[str, Any]:
    client = get_client(os.environ.get("READER_MODEL_LOCATION", "global"))
    prompt = ILLUSTRATION_PARTS_PROMPT.replace("__SUBJECT__", subject).replace(
        "__LANGUAGE__", language or "English"
    )
    response = client.models.generate_content(
        model=reader_model(),
        contents=[types.Part.from_bytes(data=picture[1], mime_type=picture[0]), prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json", temperature=0
        ),
    )
    found = json.loads(response.text or "{}")
    parts = []
    for part in found.get("parts") or []:
        box = part.get("box_2d") if isinstance(part, dict) else None
        if not (
            part.get("name")
            and isinstance(box, list)
            and len(box) == 4
            and all(isinstance(value, (int, float)) for value in box)
        ):
            continue
        top, left, bottom, right = (min(max(float(value), 0), 1000) for value in box)
        if bottom - top < 15 or right - left < 15:
            continue
        parts.append(
            {
                "name": str(part["name"]),
                "info": str(part.get("info") or ""),
                "box": [top, left, bottom, right],
            }
        )
    if len(parts) < 2:
        raise RuntimeError(
            f"{reader_model()} found no parts to click in the illustration"
        )
    # small parts last, so that they stay clickable on top of the large ones that contain them
    parts.sort(
        key=lambda part: (
            -(part["box"][2] - part["box"][0]) * (part["box"][3] - part["box"][1])
        )
    )
    return {"title": str(found.get("title") or subject)[:60], "parts": parts[:10]}


async def generate_illustrated_scene(
    subject: str, language: str = "English"
) -> tuple[str, GeneratedMedia]:
    """An illustration from the image model with its parts made clickable. Returns the page and the picture."""
    from PIL import Image

    picture = await generate_image(
        ILLUSTRATION_PROMPT.replace("__SUBJECT__", subject), "16:9"
    )
    found = await asyncio.to_thread(
        _illustration_parts_sync, subject, (picture.mime_type, picture.data), language
    )
    width, height = Image.open(io.BytesIO(picture.data)).size
    found["ratio"] = round(width / height, 4)
    found["image"] = f"data:{picture.mime_type};base64,{picture.base64}"
    page = ILLUSTRATED_PAGE.replace("__DATA__", json.dumps(found).replace("</", "<\\/"))
    return page, picture


def _read_frame_sync(request: str, frame: tuple[str, bytes]) -> dict[str, str]:
    client = get_client(os.environ.get("READER_MODEL_LOCATION", "global"))
    response = client.models.generate_content(
        model=reader_model(),
        contents=[
            types.Part.from_bytes(data=frame[1], mime_type=frame[0]),
            READER_PROMPT.replace("__REQUEST__", request),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json", temperature=0
        ),
    )
    reading = json.loads(response.text or "{}")
    if not reading.get("markup"):
        raise RuntimeError(f"{reader_model()} could not read the picture")
    return {
        "finding": str(reading.get("finding") or ""),
        "markup": str(reading["markup"]),
    }


async def read_frame(request: str, frame: tuple[str, bytes]) -> dict[str, str]:
    """What is wrong in the work the learner is showing, and how to mark it."""
    return await asyncio.to_thread(_read_frame_sync, request, frame)


PAPER_HOSTS = {
    "arxiv.org",
    "www.arxiv.org",
    "export.arxiv.org",
    "openreview.net",
    "proceedings.neurips.cc",
    "papers.nips.cc",
    "proceedings.mlr.press",
    "aclanthology.org",
}
PAPER_MAX_BYTES = 30 * 1024 * 1024

PAPER_DIGEST_PROMPT = """Read the attached research paper for a tutor who will discuss it with a visitor.
Return JSON with:
- "title": the paper's title.
- "summary": the main idea and the main result, in three sentences that a graduate student from
  another subfield can follow.
- "key_points": three to five short strings: the problem, the method, the main result, and one
  limitation the authors state.
- "parts": four to eight parts of the paper that a visitor could ask to see or try: its figures,
  its main equations, the components of its method and its experiments. Each is an object with
  "label", the name the paper uses, such as "Figure 3", "Equation 5" or "Section 4.2", "shows",
  at most twelve words on what it shows, and "page", the number of the PDF page it is on, counting
  the first page of the file as 1. Take them from across the paper, in its order.
- "figure_count": how many numbered figures the paper has, as a number.
Stay with what the paper says. Do not add claims it does not make.
"""

PAPER_ANSWER_PROMPT = """Answer the visitor's question about the attached research paper, for a tutor to say aloud.
Use only what the paper says, in at most four short sentences, and name the section, figure or
equation you rely on. If the paper does not answer the question, say so.

Question: """


PAPER_SEARCH_PROMPT = """Find the research paper a visitor means by: "__QUERY__"
Search for it, then reply with two lines only. First line: its exact title. Second line: its arXiv
identifier (for example 1706.03762) if it is on arXiv, otherwise the address of its PDF on
OpenReview, the NeurIPS proceedings, PMLR or the ACL Anthology. If you cannot find it, reply NONE.
"""


PAPER_LOCATE_PROMPT = """A tutor is about to show a visitor this part of the attached research paper:
"__PART__"
Return JSON with "label", the name the paper gives the figure, table, equation or section that
this refers to, such as "Figure 3", and "page", the number of the PDF page it is on, counting the
first page of the file as 1. If the request names no single place, use the place that shows it best.
"""

PAPER_BOX_PROMPT = """This is one page of a research paper. Find "__LABEL__" on it.
Return JSON with "box_2d": [ymin, xmin, ymax, xmax], on a scale of 0 to 1000 from the top left
corner, around the whole figure, table, algorithm or equation with its caption. Return
{"box_2d": null} if it is not on this page, or if it is a section of running text.
"""

PAPER_QUESTIONS_PROMPT = """A researcher wants to practice presenting the attached paper. A tutor will play this
listener: __ROLE__.
Write five questions that such a listener would ask, from the easiest to the hardest, each about
something specific in this paper: a choice in the method, a result, a baseline, a limitation, what
comes next. After each question add, in brackets, what the paper itself says about it in one
sentence, or that the paper does not address it. Plain text, one question per line.
"""


def document_part(reference: tuple[str, Any]) -> types.Part:
    """A picture or a PDF for the model: its bytes, or its public address when only that is known."""
    if isinstance(reference[1], str):
        return types.Part.from_uri(file_uri=reference[1], mime_type=reference[0])
    return types.Part.from_bytes(data=reference[1], mime_type=reference[0])


def paper_model() -> str:
    return os.environ.get("PAPER_MODEL", "gemini-3.8-flash")


def paper_url(reference: str) -> str:
    """Address of the PDF for an arXiv identifier, or for a link to a paper on a known site."""
    reference = reference.strip()
    arxiv = re.search(
        r"(?:arxiv\.org/(?:abs|pdf)/|arxiv:\s*|^)(\d{4}\.\d{4,5}(?:v\d+)?)",
        reference,
        re.IGNORECASE,
    )
    if arxiv:
        return f"https://arxiv.org/pdf/{arxiv.group(1)}"
    parsed = urlsplit(reference)
    if parsed.scheme != "https" or parsed.hostname not in PAPER_HOSTS:
        raise ValueError(
            "Only arXiv identifiers and links to arXiv, OpenReview, NeurIPS, PMLR or ACL Anthology "
            "can be loaded. Upload the PDF instead."
        )
    if parsed.hostname == "openreview.net" and parsed.path == "/forum":
        return reference.replace("/forum?", "/pdf?")
    return reference


def checked_pdf(data: bytes) -> bytes:
    if len(data) > PAPER_MAX_BYTES:
        raise ValueError("The paper is larger than 30 MB")
    if not data.lstrip().startswith(b"%PDF-"):
        raise ValueError("This is not a PDF")
    return data


def _fetch_paper_sync(reference: str) -> bytes:
    request = urllib.request.Request(
        paper_url(reference), headers={"User-Agent": "voxplore/1.0"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return checked_pdf(response.read(PAPER_MAX_BYTES + 1))


async def fetch_paper(reference: str) -> tuple[str, bytes]:
    return ("application/pdf", await asyncio.to_thread(_fetch_paper_sync, reference))


def _paper_sync(paper: tuple[str, bytes], prompt: str, as_json: bool) -> str:
    client = get_client(os.environ.get("PAPER_MODEL_LOCATION", "global"))
    response = client.models.generate_content(
        model=paper_model(),
        contents=[document_part(paper), prompt],
        config=types.GenerateContentConfig(
            response_mime_type="application/json" if as_json else None, temperature=0.2
        ),
    )
    return (response.text or "").strip()


async def digest_paper(paper: tuple[str, bytes]) -> dict[str, Any]:
    """Title, summary, key points and a part worth making interactive, for the avatar and the chat."""
    digest = json.loads(
        await asyncio.to_thread(_paper_sync, paper, PAPER_DIGEST_PROMPT, True) or "{}"
    )
    if not digest.get("title"):
        raise RuntimeError(f"{paper_model()} could not read the paper")
    return {
        "title": str(digest["title"]),
        "summary": str(digest.get("summary") or ""),
        "key_points": [str(point) for point in digest.get("key_points") or []],
        "parts": [
            {
                "label": str(part.get("label") or ""),
                "shows": str(part.get("shows") or ""),
                "page": part.get("page") if isinstance(part.get("page"), int) else None,
            }
            for part in digest.get("parts") or []
            if isinstance(part, dict) and part.get("label")
        ][:8],
        "figure_count": int(digest["figure_count"])
        if str(digest.get("figure_count") or "").isdigit()
        else 0,
    }


async def ask_paper(question: str, paper: tuple[str, bytes]) -> str:
    answer = await asyncio.to_thread(
        _paper_sync, paper, PAPER_ANSWER_PROMPT + question, False
    )
    if not answer:
        raise RuntimeError(f"{paper_model()} returned no answer")
    return answer


def search_model() -> str:
    return os.environ.get("SEARCH_MODEL") or paper_model()


def _resolved(address: str) -> str:
    """Where a link from a search result leads. Grounded results come as redirects."""
    request = urllib.request.Request(
        address, method="HEAD", headers={"User-Agent": "voxplore/1.0"}
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.geturl()


def _accepted(candidates: list) -> str | None:
    for candidate in candidates:
        try:
            return paper_url(candidate)
        except ValueError:
            continue
    return None


def _google_search_sync(query: str) -> str | None:
    client = get_client(
        os.environ.get("SEARCH_MODEL_LOCATION")
        or os.environ.get("PAPER_MODEL_LOCATION", "global")
    )
    response = client.models.generate_content(
        model=search_model(),
        contents=PAPER_SEARCH_PROMPT.replace("__QUERY__", query),
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())], temperature=0
        ),
    )
    candidate = (response.candidates or [None])[0]
    parts = (candidate.content.parts if candidate and candidate.content else None) or []
    text = " ".join(part.text for part in parts if part.text)
    logger.info(f'Google Search answer for "{query}": {text!r}')
    named = [
        f"arxiv:{found}" for found in re.findall(r"\b(\d{4}\.\d{4,5}(?:v\d+)?)\b", text)
    ]
    named += [
        link.rstrip(".,;") for link in re.findall(r"https://[^\s\"'<>)\]]+", text)
    ]
    address = _accepted(named)
    if address:
        return address
    # the answer named no usable address: look at the pages the search itself returned
    grounding = candidate.grounding_metadata if candidate else None
    chunks = (grounding.grounding_chunks if grounding else None) or []
    redirects = [
        chunk.web.uri for chunk in chunks if chunk.web and chunk.web.uri
    ] + named
    for link in redirects:
        if urlsplit(link).hostname != "vertexaisearch.cloud.google.com":
            continue
        try:
            address = _accepted([_resolved(link)])
        except Exception:
            continue
        if address:
            return address
    return None


def _arxiv_search_sync(query: str) -> str | None:
    words = quote(" ".join(re.findall(r"\w+", query)))
    request = urllib.request.Request(
        f"https://export.arxiv.org/api/query?search_query=all:{words}&max_results=1&sortBy=relevance",
        headers={"User-Agent": "voxplore/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        feed = response.read(1_000_000).decode("utf-8", "replace")
    found = re.search(
        r"<id>https?://arxiv\.org/abs/(\d{4}\.\d{4,5}(?:v\d+)?)</id>", feed
    )
    return paper_url(found.group(1)) if found else None


def _render_page_sync(pdf: bytes, page: int) -> bytes:
    import pypdfium2

    document = pypdfium2.PdfDocument(pdf)
    try:
        if not 1 <= page <= len(document):
            raise ValueError(f"The paper has no page {page}")
        picture = document[page - 1].render(scale=2).to_pil().convert("RGB")
    finally:
        document.close()
    out = io.BytesIO()
    picture.save(out, "JPEG", quality=85)
    return out.getvalue()


def _crop_part_sync(page_image: bytes, label: str) -> bytes | None:
    """The figure, table or equation cut out of the picture of its page. None when it cannot be found."""
    client = get_client(os.environ.get("READER_MODEL_LOCATION", "global"))
    response = client.models.generate_content(
        model=reader_model(),
        contents=[
            types.Part.from_bytes(data=page_image, mime_type="image/jpeg"),
            PAPER_BOX_PROMPT.replace("__LABEL__", label),
        ],
        config=types.GenerateContentConfig(
            response_mime_type="application/json", temperature=0
        ),
    )
    box = json.loads(response.text or "{}").get("box_2d")
    if not (
        isinstance(box, list)
        and len(box) == 4
        and all(isinstance(value, (int, float)) for value in box)
    ):
        return None
    from PIL import Image

    picture = Image.open(io.BytesIO(page_image))
    top, left, bottom, right = (min(max(value, 0), 1000) / 1000 for value in box)
    margin = 0.015
    area = (
        int(max(left - margin, 0) * picture.width),
        int(max(top - margin, 0) * picture.height),
        int(min(right + margin, 1) * picture.width),
        int(min(bottom + margin, 1) * picture.height),
    )
    if (
        area[2] - area[0] < 0.15 * picture.width
        or area[3] - area[1] < 0.05 * picture.height
    ):
        return None
    out = io.BytesIO()
    picture.crop(area).save(out, "JPEG", quality=88)
    return out.getvalue()


async def paper_page(
    part: str,
    paper: tuple[str, Any],
    page: int | None = None,
    label: str = "",
    crop: bool = False,
) -> PaperPage | None:
    """The page of the paper that shows a part of it, as a picture, or only that part when crop is
    set and it can be found. None when it cannot be made.
    """
    if not isinstance(paper[1], bytes):
        return None
    given = bool(page)
    try:
        if not page:
            prompt = PAPER_LOCATE_PROMPT.replace("__PART__", part)
            found = json.loads(
                await asyncio.to_thread(_paper_sync, paper, prompt, True) or "{}"
            )
            page, label = int(found["page"]), str(found.get("label") or label)
        image = await asyncio.to_thread(_render_page_sync, paper[1], page)
    except Exception as e:
        logger.warning(f'Could not show the page of the paper for "{part}": {e}')
        return None
    label = label or f"Page {page}"
    if crop:
        try:
            cut = await asyncio.to_thread(_crop_part_sync, image, label)
            if cut is None and given:
                # the page noted when the paper was read may be off: look the part up again
                return await paper_page(part, paper, None, label, crop)
            image = cut or image
        except Exception as e:
            logger.warning(
                f"Could not cut {label} out of page {page}, showing the whole page: {e}"
            )
    return PaperPage(label=label, page=page, image=image)


async def paper_questions(role: str, paper: tuple[str, bytes]) -> str:
    questions = await asyncio.to_thread(
        _paper_sync, paper, PAPER_QUESTIONS_PROMPT.replace("__ROLE__", role), False
    )
    if not questions:
        raise RuntimeError(f"{paper_model()} returned no questions")
    return questions


def _find_paper_sync(query: str) -> tuple[str, str]:
    reasons = []
    for source, search in (
        ("Google Search", _google_search_sync),
        ("arXiv search", _arxiv_search_sync),
    ):
        try:
            address = search(query)
        except Exception as e:
            logger.warning(f'{source} failed for "{query}": {e}')
            reasons.append(f"{source}: {e}")
            continue
        if address:
            return address, source
        reasons.append(f"{source}: nothing found")
    raise RuntimeError(f'No paper was found for "{query}" ({"; ".join(reasons)})')


async def find_paper(query: str) -> tuple[str, str]:
    """Address of the paper a title or description refers to, and the search that found it."""
    return await asyncio.to_thread(_find_paper_sync, query)
