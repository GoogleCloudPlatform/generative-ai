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

import os

from google.adk.agents import LlmAgent

from .tools import TOOLS, function_declarations

AVATARS = {
    "Professional": ["Kira", "Ingrid", "Vera", "Sam", "Jay", "Paul"],
    "Stylized": ["Ben", "Kai", "Leo", "Carmen", "Piper"],
}
AVATAR_NAMES = [name for names in AVATARS.values() for name in names]

VOICES = {
    "Aoede": "Breezy",
    "Puck": "Upbeat",
    "Kore": "Firm",
    "Zephyr": "Bright",
    "Charon": "Informative",
    "Leda": "Youthful",
    "Sulafat": "Warm",
    "Achird": "Friendly",
    "Sadaltager": "Knowledgeable",
    "Vindemiatrix": "Gentle",
    "Fenrir": "Excitable",
    "Orus": "Firm",
    "Autonoe": "Bright",
    "Umbriel": "Easy-going",
    "Erinome": "Clear",
    "Laomedeia": "Upbeat",
    "Schedar": "Even",
    "Sadachbia": "Lively",
    "Enceladus": "Breathy",
    "Algieba": "Smooth",
    "Algenib": "Gravelly",
    "Achernar": "Soft",
    "Gacrux": "Mature",
    "Zubenelgenubi": "Casual",
    "Callirrhoe": "Easy-going",
    "Iapetus": "Clear",
    "Despina": "Smooth",
    "Rasalgethi": "Informative",
    "Alnilam": "Firm",
    "Pulcherrima": "Forward",
}

root_agent = LlmAgent(
    name="voxplore_assistant",
    model="gemini-3.8-live",  # or "gemini-3.1-flash-live-preview-04-2026"
    instruction="""You are a professional AI assistant with a live avatar.
Your goal is to answer simple questions based on your knowledge in a polite, direct, and concise manner.
Keep your answers brief as they will be spoken by your avatar.
Always speak clearly and be helpful.

When the user shares their camera or screen you can see it. Answer questions about what is shown
and refer to it naturally.

You can also create media for the user:
- Call generate_image when they ask for any visual: a picture, an image, an illustration, a diagram,
  a chart, an infographic, a mockup, a poster, a logo.
- Call generate_video when they ask for a video, a clip or an animation.
- Call edit_image or edit_video when they want to change or extend the image or video that was just made.
- Call generate_video with use_last_image when they want to animate the image that was just made.
- Call generate_interactive_scene when they ask for something in 3D, a model they can rotate or
  explore, or a simulation they can try themselves. Call edit_interactive_scene to change it.
  Scenes are made of simple shapes: use them for structure and behavior, such as molecules,
  orbits, networks, graphs and mechanisms.
- Call generate_illustrated_scene when they want to explore or interact with something that has
  to be drawn to look right: the human body, an organ, a cell, an animal, a plant, a machine, a
  place or a city with its landmarks. It draws the subject and makes its parts clickable. Never
  refuse an interactive request for such a subject: use this tool. When they only want to see
  the subject, use an image or a video. Say that it is a generated illustration, so a drawing of
  a real place is not an accurate map.
- Call annotate_current_view when they show their work or their screen and want you to check it,
  correct it or point at something in it. Pass on what they asked; you are told what was found.
- When they show a paper, a poster or a figure and ask about it, explain the key idea in two or
  three short sentences, then offer to build an interactive scene of it. If they accept, call
  generate_interactive_scene with use_current_view set to true.
- When the user asks for a simulation, a scene, an image or a video from a paper, a poster or a
  document and has not said which part of it, do not choose for them. First ask one short,
  open question about what they want to explore. Describe the directions by what they are about,
  in plain words and across the whole work: for example how the method works, what an experiment
  found, or a trade-off they could play with. Add that they can also name any figure, table or
  equation. Do not reduce the question to a choice between two figure numbers. If their answer
  is still broad, ask one more question, such as what they would like to be able to change.
  Call the tool only once you know what to build. When they have named the part, or tell you to
  choose, go ahead without asking.
- When the user uploads or links a paper, you are told its title and content once it has been
  read. Never ask them for the title or the topic of a paper they loaded.
- When the user names a research paper they want to discuss, call find_paper to load it. When you
  are told that a paper is loaded, you have its summary. For any detailed
  question about it, call ask_paper and wait for the answer instead of guessing. To turn the part
  they chose into something they can try, call generate_interactive_scene with use_paper set to
  true and name that part in the description. For a visual abstract, call generate_image and say that it is an
  illustration, not a figure from the paper.
- When the user asks to see or look at a figure, a table, an equation or a section of the loaded
  paper, call show_paper_part. When you are told that it is displayed, say what it shows and ask
  what they would like to do with it.
- When the user wants to practice presenting their paper, their poster pitch or their defense, or
  asks you to question them, call prepare_questions with the listener you will play. If no paper
  is loaded, ask them to load it, or to summarize their work in a minute, and ask your questions
  from what they say.
Create media when the user asks for it. When you are told that proactive mode is on, you may
also create it without being asked, as that message describes.
You can always create these. Never say that you cannot generate images, diagrams or videos; call the tool.
Turn what the user asked for into a rich, detailed prompt. If they want what they are showing on
camera or screen in the result, set use_current_view to true. When you call one of these tools,
say in one short sentence that you are generating it and keep helping the user.
The result appears in the conversation automatically. When you are told that a generation
is ready, tell the user in one short sentence. Create as many images and videos as the user asks for.
- When the user uploads pictures, they are numbered in upload order. To make something from them,
  call generate_image or generate_video with use_uploads set to true and refer to them in the
  prompt as image 1, image 2.
A generation takes from a few seconds to a minute. After you call a tool, never say that the result
is ready, shown or done until you are told that it is displayed. While you wait, keep explaining
the topic in a few short sentences.
When you are told what the user did in an interactive scene, react to it as a tutor in one or two
short sentences: explain the part they selected or the effect of the value they set.
""",
    description="Voice tutor on the Gemini Live API that generates images, videos and interactive scenes.",
    tools=TOOLS,
)


PRESETS = {
    "learning": "",
    "research": """
You are at a research conference and the people you talk to are researchers. Speak to them as a
peer, at graduate level, with the precise terms of their field. When the conversation starts, or
when they ask what you can do, invite them to load a paper: theirs or one they want to understand.
""",
}


MODE_NOTES = {
    "learning": "The session is now in learning mode: speak to a general learner, in plain words.",
    "research": "The session is now in research mode."
    + PRESETS["research"].replace("\n", " "),
}

PROACTIVE_NOTES = {
    True: (
        "Proactive mode is on. While you explain something, when an image, an interactive scene or an "
        "illustrated scene would clearly help the user understand, create it without being asked, and say in "
        "a few words that you are doing so. Create one thing at a time: never start one while another is "
        "still being made, and at most one for a topic unless the user asks for more. Do not create videos "
        "unless the user asks."
    ),
    False: "Proactive mode is off. Create media only when the user asks for it.",
}


def proactive_default() -> bool:
    return os.environ.get("PROACTIVE_MODE", "off").lower() == "on"


def preset() -> str:
    return pick(os.environ.get("DEMO_PRESET"), PRESETS, "learning")


# The project's name, shown in the app and in the evaluation report. APP_NAME in .env overrides it.
DEFAULT_APP_NAME = "VoxPlore"


def app_name() -> str:
    return os.environ.get("APP_NAME", "").strip() or DEFAULT_APP_NAME


def pick(name: str | None, options, default: str) -> str:
    """Case-insensitive match against the allowed names, falling back to the default."""
    if name:
        for option in options:
            if option.lower() == name.strip().lower():
                return option
    return default


def default_avatar() -> str:
    return pick(os.environ.get("AVATAR_NAME"), AVATAR_NAMES, "Kira")


def default_voice() -> str:
    return pick(os.environ.get("VOICE_NAME"), VOICES, "Aoede")


def get_agent_setup_config(
    agent: LlmAgent, avatar_name: str | None = None, voice_name: str | None = None
) -> dict:
    """Live API setup message for the agent: model, instruction, tools, avatar and voice."""
    instruction_text = agent.instruction
    if callable(instruction_text):
        instruction_text = instruction_text(None)
    instruction_text += PRESETS[preset()]
    if proactive_default():
        instruction_text += "\n" + PROACTIVE_NOTES[True] + "\n"
    use_avatar = os.environ.get("ENABLE_AVATAR", "true").lower() == "true"
    project_id = os.environ.get("GCP_PROJECT_ID", "")
    region = os.environ.get("GCP_REGION", "us-central1")

    model_name = agent.model
    if "projects/" not in model_name and "publishers/" not in model_name:
        model_name = f"projects/{project_id}/locations/{region}/publishers/google/models/{model_name}"
    elif "publishers/" in model_name and "projects/" not in model_name:
        model_name = f"projects/{project_id}/locations/{region}/{model_name}"

    print(f"Model name: {model_name}")

    setup = {
        "system_instruction": {"parts": [{"text": instruction_text}]},
        "model": model_name,
        "generation_config": {
            "response_modalities": ["VIDEO"] if use_avatar else ["AUDIO"],
            "speech_config": {
                "voice_config": {
                    "prebuilt_voice_config": {
                        "voice_name": pick(voice_name, VOICES, default_voice())
                    }
                }
            },
        },
        "realtime_input_config": {
            "automatic_activity_detection": {
                "disabled": False,
                "start_of_speech_sensitivity": "START_SENSITIVITY_HIGH",
                "end_of_speech_sensitivity": "END_SENSITIVITY_HIGH",
                "prefix_padding_ms": 20,
                "silence_duration_ms": 100,
            }
        },
        "tools": [{"function_declarations": function_declarations(agent.tools)}],
        "input_audio_transcription": {},
        "output_audio_transcription": {},
    }
    if use_avatar:
        setup["avatar_config"] = {
            "avatar_name": pick(avatar_name, AVATAR_NAMES, default_avatar())
        }
    else:
        # Proactive audio routes to an audio-only model variant (e.g. *_proactive)
        # that rejects response_modalities=["VIDEO"]. Only enable it in audio-only mode.
        setup["proactivity"] = {"proactive_audio": True}
    return {"setup": setup}
