# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from dataclasses import field
import os

from dataclasses_json import dataclass_json
import mesop as me
from shared.nav_menu import nav_menu
import vertexai
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
    Part,
)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")  # Your Google Cloud Project ID
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION")  # Your Google Cloud Project Region
vertexai.init(project=PROJECT_ID, location=LOCATION)


@dataclass_json
@me.stateclass
class State:
    model: str = "gemini-1.5-flash-002"
    current_page: str = "/"

    # Story
    input: str = ""
    story_character_name: str
    story_character_type: str = "Cat"
    story_character_personality: str = "Mitten is a very friendly cat."
    story_character_location: str = "Andromeda Galaxy"
    story_selected_premises: list[str] = field(default_factory=lambda: ["adventure"])
    story_temp_value: str = "low"
    story_length_value: str = "short"
    story_progress: bool = False
    story_output: str = ""

    # Marketing
    marketing_product: str = "ZomZoo"
    marketing_product_categories: list[str] = field(
        default_factory=lambda: [
            "clothing",
            "electronics",
            "food",
            "health & beauty",
            "home & garden",
        ]
    )
    marketing_product_category: str = "clothing"
    marketing_target_audiences: list[str] = field(
        default_factory=lambda: ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"]
    )
    marketing_target_audience: str = "18-24"
    marketing_target_locations: list[str] = field(
        default_factory=lambda: ["urban", "suburban", "rural"]
    )
    marketing_target_location: str = "urban"
    marketing_campaign_goals: list[str] = field(
        default_factory=lambda: [
            "increase brand awareness",
            "generate leads",
            "drive sales",
            "improve brand sentiment",
        ]
    )
    marketing_campaign_goal: str = "increase brand awareness"
    marketing_campaign_selected_goals: list[str] = field(
        default_factory=lambda: ["increase brand awareness", "generate leads"]
    )
    marketing_brand_voices: list[str] = field(
        default_factory=lambda: ["formal", "informal", "serious", "humorous", "casual"]
    )
    marketing_brand_voice: str = "formal"
    marketing_budgets: list[str] = field(
        default_factory=lambda: [
            "1,000 - 5,000",
            "5,000 - 10,000",
            "10,000 - 20,000",
            "20,000+",
        ]
    )
    marketing_budget: str = "1,000 - 5,000"
    marketing_campaign_progress: bool = False
    marketing_campaign_output: str = ""

    # Image playground
    image_tab: str = "furniture"

    furniture_recommendation_output: str = ""
    oven_instructions_output: str = ""
    er_doc_output: str = ""
    image_glasses_shape_radio_value: str = "oval"
    image_glasses_output_radio_value: str = "text"
    glasses_rec_output: str = ""
    math_answers_output: str = ""

    image_progress_spinner: bool = False

    # Video playground
    video_tab: str = "desc"

    video_spinner_progress: bool = False
    video_description_content: str = ""
    video_tags_content: str = ""
    video_highlights_content: str = ""
    video_geolocation_content: str = ""


# Helpers
def gcs_to_http(gcs_uri: str) -> str:
    """given a GCS URI, return the HTTPS URL

    Args:
        gcs_uri (str): Google Cloud Storage URI

    Returns:
        string: the HTTPS URL equivalent
    """
    return "https://storage.googleapis.com/" + gcs_uri.split("gs://")[1]


# Events


def on_input(e: me.InputEvent) -> None:
    print(f"{e}")
    state = me.state(State)
    setattr(state, e.key, e.value)


# Story events
def on_selection_change(e: me.SelectSelectionChangeEvent) -> None:
    s = me.state(State)
    s.story_selected_premises = e.values
    print(f"selected: {s.story_selected_premises}")


def on_click_clear_story(e: me.ClickEvent) -> None:
    """Click event for clearing story text."""
    state = me.state(State)
    state.story_output = 0


def on_radio_change(event: me.RadioChangeEvent) -> None:
    s = me.state(State)
    s.radio_value = event.value


def on_length_radio_change(event: me.RadioChangeEvent) -> None:
    s = me.state(State)
    s.story_length_value = event.value


def generate_story(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.story_output = ""  # clear any existing story
    s.story_progress = True
    yield

    if s.story_temp_value == "low":
        temp = 0.5
    elif s.story_temp_value == "high":
        temp = 1.5
    else:
        temp = 1
    prompt = f"""Write a {s.story_length_value} story based on the following premise: \n
    character_name: {s.story_character_name} \n
    character_type: {s.story_character_type} \n
    character_persona: {s.story_character_personality} \n
    character_location: {s.story_character_location} \n
    story_premise: {",".join(s.story_selected_premises)} \n
    If the story is "short", then make sure to have 5 chapters or else if it is "long" then 10 chapters.
    Important point is that each chapters should be generated based on the premise given above.
    First start by giving the book introduction, chapter introductions and then each chapter. It should also have a proper ending.
    The book should have prologue and epilogue.
    """
    print(f"prompt: {prompt}")

    model = GenerativeModel(s.model)
    config = GenerationConfig(temperature=temp, max_output_tokens=2048)
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    response = model.generate_content(
        prompt,
        generation_config=config,
        safety_settings=safety_settings,
    )
    print(response)
    s.story_output = response.text
    s.story_progress = False
    yield


# Marketing events
def on_change_marketing_category(e: me.RadioChangeEvent) -> None:
    state = me.state(State)
    state.marketing_product_category = e.value


def on_change_marketing_target(e: me.RadioChangeEvent) -> None:
    state = me.state(State)
    state.marketing_target_audience = e.value


def on_change_marketing_location(e: me.RadioChangeEvent) -> None:
    state = me.state(State)
    state.marketing_target_location = e.value


def on_selection_change_marketing_goals(e: me.SelectSelectionChangeEvent) -> None:
    s = me.state(State)
    s.marketing_campaign_selected_goals = e.values
    print(f"selected: {s.marketing_campaign_selected_goals}")


def on_change_marketing_brand_voice(e: me.RadioChangeEvent) -> None:
    state = me.state(State)
    state.marketing_brand_voice = e.value


def on_change_marketing_budget(e: me.RadioChangeEvent) -> None:
    state = me.state(State)
    state.marketing_budget = e.value


def generate_marketing_campaign(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.marketing_campaign_progress = True
    prompt = f"""Generate a marketing campaign for {s.marketing_product}, a {s.marketing_product_category} designed for the age group: {s.marketing_target_audience}.
    The target location is this: {s.marketing_target_location}.
    Aim to primarily achieve {s.marketing_campaign_selected_goals}.
    Emphasize the product's unique selling proposition while using a {s.marketing_brand_voice} tone of voice.
    Allocate the total budget of {s.marketing_budget}.
    With these inputs, make sure to follow following guidelines and generate the marketing campaign with proper headlines: \n
    - Briefly describe company, its values, mission, and target audience.
    - Highlight any relevant brand guidelines or messaging frameworks.
    - Provide a concise overview of the campaign's objectives and goals.
    - Briefly explain the product or service being promoted.
    - Define your ideal customer with clear demographics, psychographics, and behavioral insights.
    - Understand their needs, wants, motivations, and pain points.
    - Clearly articulate the desired outcomes for the campaign.
    - Use SMART goals (Specific, Measurable, Achievable, Relevant, and Time-bound) for clarity.
    - Define key performance indicators (KPIs) to track progress and success.
    - Specify the primary and secondary goals of the campaign.
    - Examples include brand awareness, lead generation, sales growth, or website traffic.
    - Clearly define what differentiates your product or service from competitors.
    - Emphasize the value proposition and unique benefits offered to the target audience.
    - Define the desired tone and personality of the campaign messaging.
    - Identify the specific channels you will use to reach your target audience.
    - Clearly state the desired action you want the audience to take.
    - Make it specific, compelling, and easy to understand.
    - Identify and analyze your key competitors in the market.
    - Understand their strengths and weaknesses, target audience, and marketing strategies.
    - Develop a differentiation strategy to stand out from the competition.
    - Define how you will track the success of the campaign.
   -  Utilize relevant KPIs to measure performance and return on investment (ROI).
   Give proper bullet points and headlines for the marketing campaign. Do not produce any empty lines.
   Be very succinct and to the point.
    """
    print(f"prompt: {prompt}")

    config = GenerationConfig(temperature=0.8, max_output_tokens=2048)

    model = GenerativeModel(s.model)

    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }
    response = model.generate_content(
        prompt,
        generation_config=config,
        safety_settings=safety_settings,
    )
    print(response)
    s.marketing_campaign_output = response.text
    s.marketing_campaign_progress = False


def on_click_clear_marketing_campaign(e: me.ClickEvent) -> None:
    """Click event for clearing marketing text."""
    state = me.state(State)
    state.marketing_campaign_output = 0


# Image Events

ROOM_IMAGE_URI = (
    "gs://github-repo/img/gemini/retail-recommendations/rooms/living_room.jpeg"
)
CHAIR_1_IMAGE_URI = (
    "gs://github-repo/img/gemini/retail-recommendations/furnitures/chair1.jpeg"
)
CHAIR_2_IMAGE_URI = (
    "gs://github-repo/img/gemini/retail-recommendations/furnitures/chair2.jpeg"
)
CHAIR_3_IMAGE_URI = (
    "gs://github-repo/img/gemini/retail-recommendations/furnitures/chair3.jpeg"
)
CHAIR_4_IMAGE_URI = (
    "gs://github-repo/img/gemini/retail-recommendations/furnitures/chair4.jpeg"
)
IMAGE_OVEN = "gs://github-repo/img/gemini/multimodality_usecases_overview/stove.jpg"
IMAGE_ER_DIAGRAM = "gs://github-repo/img/gemini/multimodality_usecases_overview/er.png"
IMAGE_GLASSES_1 = (
    "gs://github-repo/img/gemini/multimodality_usecases_overview/glasses1.jpg"
)
IMAGE_GLASSES_2 = (
    "gs://github-repo/img/gemini/multimodality_usecases_overview/glasses2.jpg"
)
IMAGE_MATH = (
    "gs://github-repo/img/gemini/multimodality_usecases_overview/math_beauty.jpg"
)


def generate_furniture_recommendation(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.image_progress_spinner = True

    room_image_part = Part.from_uri(ROOM_IMAGE_URI, mime_type="image/jpeg")
    chair_1_image_part = Part.from_uri(CHAIR_1_IMAGE_URI, mime_type="image/jpeg")
    chair_2_image_part = Part.from_uri(CHAIR_2_IMAGE_URI, mime_type="image/jpeg")
    chair_3_image_part = Part.from_uri(CHAIR_3_IMAGE_URI, mime_type="image/jpeg")
    chair_4_image_part = Part.from_uri(CHAIR_4_IMAGE_URI, mime_type="image/jpeg")

    content = [
        "Consider the following chairs:",
        "chair 1:",
        chair_1_image_part,
        "chair 2:",
        chair_2_image_part,
        "chair 3:",
        chair_3_image_part,
        "and",
        "chair 4:",
        chair_4_image_part,
        "\n"
        "For each chair, explain why it would be suitable or not suitable for the following room:",
        room_image_part,
        "Only recommend for the room provided and not other rooms. Provide your recommendation in a table format with chair name and reason as columns.",
    ]

    model_name = s.model

    print(f"using model: {model_name}")

    config = GenerationConfig(temperature=0.3, max_output_tokens=2048)

    model = GenerativeModel(
        model_name=model_name,
        generation_config=config,
        # safety_settings=safety_settings,
    )

    response = model.generate_content(content)
    print(response)
    s.furniture_recommendation_output = response.text
    s.image_progress_spinner = False


def on_click_clear_furniture_recommendation(e: me.ClickEvent) -> None:
    """Click event for clearing furniture recommendation text."""
    state = me.state(State)
    state.furniture_recommendation_output = 0


def generate_oven_instructions(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.image_progress_spinner = True

    oven_image = Part.from_uri(IMAGE_OVEN, mime_type="image/jpeg")

    content = [
        oven_image,
        """How can I reset the clock on this appliance? Provide the instructions in English.
If instructions include buttons, also explain where those buttons are physically located.""",
    ]

    model_name = s.model

    print(f"using model: {model_name}")

    config = GenerationConfig(temperature=0.3, max_output_tokens=2048)

    model = GenerativeModel(
        model_name=model_name,
        generation_config=config,
        # safety_settings=safety_settings,
    )

    response = model.generate_content(content)
    s.oven_instructions_output = response.text
    s.image_progress_spinner = False


def on_click_clear_oven_instructions(e: me.ClickEvent) -> None:
    """Click event for clearing oven instructions text."""
    state = me.state(State)
    state.oven_instructions_output = 0


def generate_er_doc(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.image_progress_spinner = True

    er_image = Part.from_uri(IMAGE_ER_DIAGRAM, mime_type="image/jpeg")

    content = [
        er_image,
        """Document the entities and relationships in this ER diagram.""",
    ]

    model_name = s.model

    print(f"using model: {model_name}")

    config = GenerationConfig(temperature=0.3, max_output_tokens=2048)

    model = GenerativeModel(
        model_name=model_name,
        generation_config=config,
        # safety_settings=safety_settings,
    )

    response = model.generate_content(content)
    s.er_doc_output = response.text
    s.image_progress_spinner = False


def on_click_clear_er_doc(e: me.ClickEvent) -> None:
    """Click event for clearing er documentation text."""
    state = me.state(State)
    state.er_doc_output = 0


def generate_glasses_rec(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.image_progress_spinner = True

    glasses_1 = Part.from_uri(IMAGE_GLASSES_1, mime_type="image/jpeg")
    glasses_2 = Part.from_uri(IMAGE_GLASSES_2, mime_type="image/jpeg")

    content = [
        f"Which of these glasses you recommend for me based on the shape of my face: {s.image_glasses_shape_radio_value} I have a {s.image_glasses_shape_radio_value} shaped face.\n",
        "Glasses 1: ",
        glasses_1,
        "Glasses 2: ",
        glasses_2,
        f"""
Explain how you reach out to this decision.
Provide your recommendation based on my face shape, and reasoning for each in {s.image_glasses_output_radio_value} format.
""",
    ]

    model_name = s.model

    print(f"using model: {model_name}")

    config = GenerationConfig(temperature=0.3, max_output_tokens=2048)
    model = GenerativeModel(
        model_name=model_name,
        generation_config=config,
        # safety_settings=safety_settings,
    )

    response = model.generate_content(content)
    s.glasses_rec_output = response.text
    s.image_progress_spinner = False


def on_change_image_glasses(e: me.RadioChangeEvent) -> None:
    s = me.state(State)

    value_name = f"image_{e.key}_radio_value"
    print(f"{e.value} {e.key} {value_name}")
    # value_object = getattr(s, value_name)
    setattr(s, value_name, e.value)


def on_click_clear_glasses_rec(e: me.ClickEvent) -> None:
    """Click event for clearing glasses documentation text."""
    state = me.state(State)
    state.glasses_rec_output = 0


def generate_math_answers(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.image_progress_spinner = True

    math_image = Part.from_uri(IMAGE_MATH, mime_type="image/jpeg")

    content = [
        math_image,
        """
Follow the instructions.
Surround math expressions with $.
Use a table with a row for each instruction and its result.

INSTRUCTIONS:
- Extract the formula.
- What is the symbol right before Pi? What does it mean?
- Is this a famous formula? Does it have a name?
""",
    ]

    model_name = s.model

    print(f"using model: {model_name}")

    config = GenerationConfig(temperature=0.3, max_output_tokens=2048)
    model = GenerativeModel(
        model_name=model_name,
        generation_config=config,
        # safety_settings=safety_settings,
    )

    response = model.generate_content(content)
    s.math_answers_output = response.text
    s.image_progress_spinner = False


def on_click_clear_math(e: me.ClickEvent) -> None:
    """Click event for clearing math documentation text."""
    state = me.state(State)
    state.math_answers_output = 0


# Video Events

VIDEO_DESCRIPTION = (
    "gs://github-repo/img/gemini/multimodality_usecases_overview/mediterraneansea.mp4"
)
VIDEO_TAGS = (
    "gs://github-repo/img/gemini/multimodality_usecases_overview/photography.mp4"
)
VIDEO_HIGHLIGHTS = (
    "gs://github-repo/img/gemini/multimodality_usecases_overview/pixel8.mp4"
)
VIDEO_GEOLOCATION = (
    "gs://github-repo/img/gemini/multimodality_usecases_overview/bus.mp4"
)


def generate_video_description(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.video_spinner_progress = True

    video_part = Part.from_uri(VIDEO_DESCRIPTION, mime_type="video/mp4")

    prompt = """Describe what is happening in the video and answer the following questions: \n
    - What am I looking at? \n
    - Where should I go to see it? \n
    - What are other top 5 places in the world that look like this?
    """

    model_name = s.model

    print(f"using model: {model_name}")
    print(f"video url: {VIDEO_DESCRIPTION}")
    print(f"prompt: {prompt}")

    config = GenerationConfig(temperature=0.3, max_output_tokens=2048)
    model = GenerativeModel(
        model_name=model_name,
        generation_config=config,
        # safety_settings=safety_settings,
    )
    contents = [video_part, prompt]
    response = model.generate_content(contents)
    print(response)
    s.video_description_content = response.text
    s.video_spinner_progress = False


def on_click_clear_video_description(e: me.ClickEvent) -> None:
    """Click event for clearing video description text."""
    state = me.state(State)
    state.video_description_content = 0


def generate_video_tags(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.video_spinner_progress = True

    video_part = Part.from_uri(VIDEO_TAGS, mime_type="video/mp4")

    prompt = """Answer the following questions using the video only:
    1. What is in the video?
    2. What objects are in the video?
    3. What is the action in the video?
    4. Provide 5 best tags for this video?

    Give the answer in the table format with question and answer as columns.
    """

    model_name = s.model

    print(f"using model: {model_name}")
    print(f"video url: {VIDEO_TAGS}")
    print(f"prompt: {prompt}")

    config = GenerationConfig(temperature=0.3, max_output_tokens=2048)
    model = GenerativeModel(
        model_name=model_name,
        generation_config=config,
        # safety_settings=safety_settings,
    )
    contents = [video_part, prompt]
    response = model.generate_content(contents)
    print(response)
    s.video_tags_content = response.text
    s.video_spinner_progress = False


def on_click_clear_video_tags(e: me.ClickEvent) -> None:
    """Click event for clearing video tags text."""
    state = me.state(State)
    state.video_tags_content = 0


def generate_video_highlights(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.video_spinner_progress = True

    video_part = Part.from_uri(VIDEO_HIGHLIGHTS, mime_type="video/mp4")

    prompt = """Answer the following questions using the video only: What is the profession of the girl in this video? Which all features of the phone are highlighted here? Summarize the video in one paragraph. Provide the answer in table format.
    """

    model_name = s.model

    print(f"using model: {model_name}")
    print(f"video url: {VIDEO_TAGS}")
    print(f"prompt: {prompt}")

    config = GenerationConfig(temperature=0.3, max_output_tokens=2048)
    model = GenerativeModel(
        model_name=model_name,
        generation_config=config,
        # safety_settings=safety_settings,
    )
    contents = [video_part, prompt]
    response = model.generate_content(contents)
    print(response)
    s.video_highlights_content = response.text
    s.video_spinner_progress = False


def on_click_clear_video_highlights(e: me.ClickEvent) -> None:
    """Click event for clearing video highlights text."""
    state = me.state(State)
    state.video_highlights_content = 0


def generate_video_geolocation(e: me.ClickEvent | me.EnterEvent) -> None:
    s = me.state(State)
    s.video_spinner_progress = True

    video_part = Part.from_uri(VIDEO_GEOLOCATION, mime_type="video/mp4")

    prompt = """Answer the following questions using the video only:

    What is this video about?
    How do you know which city it is?
    What street is this?
    What is the nearest intersection?

    Answer the questions in a table format with question and answer as columns.
    """

    model_name = s.model

    print(f"using model: {model_name}")
    print(f"video url: {VIDEO_TAGS}")
    print(f"prompt: {prompt}")

    config = GenerationConfig(temperature=0.3, max_output_tokens=2048)
    model = GenerativeModel(
        model_name=model_name,
        generation_config=config,
        # safety_settings=safety_settings,
    )
    contents = [video_part, prompt]
    response = model.generate_content(contents)
    print(response)
    s.video_geolocation_content = response.text
    s.video_spinner_progress = False


def on_click_clear_video_geolocation(e: me.ClickEvent) -> None:
    """Click event for clearing video geolocation text."""
    state = me.state(State)
    state.video_geolocation_content = 0


# Pages


def on_load(e: me.LoadEvent) -> None:
    s = me.state(State)
    s.current_page = "/"


@me.component
def vertex_gemini_header() -> None:
    with me.box(style=_STYLE_MAIN_HEADER):
        with me.box(style=_STYLE_TITLE_BOX):
            with me.box(
                style=me.Style(
                    display="flex", flex_direction="row", gap=5, align_content="center"
                ),
            ):
                me.text(
                    "Vertex AI Gemini ", type="headline-5", style=FANCY_TEXT_GRADIENT
                )
                me.text("with Mesop", type="headline-5")


# Generate a story page / main
@me.page(
    path="/",
    title="Vertex AI Gemini with Mesop",
    security_policy=me.SecurityPolicy(
        allowed_iframe_parents=["https://google.github.io"]
    ),
    on_load=on_load,
)
def app() -> None:
    state = me.state(State)
    # Main header
    vertex_gemini_header()

    # Nav header
    nav_menu(state)

    # Main content
    with me.box(style=_STYLE_MAIN_COLUMN):
        me.text(text="Generate a story", type="headline-6")

        with me.box(style=me.Style(display="flex", flex_direction="row", gap=15)):
            with me.box(style=me.Style(display="flex", flex_direction="column", gap=2)):
                me.input(
                    key="story_character_name",
                    label="Character name",
                    value="Mittens",
                    on_input=on_input,
                    style=_STORY_INPUT_STYLE,
                )
                me.input(
                    key="story_character_type",
                    label="Type of character",
                    value="Cat",
                    on_input=on_input,
                    style=_STORY_INPUT_STYLE,
                )
                me.input(
                    key="story_character_personality",
                    label="Personality of character",
                    value="Mitten is a very friendly cat.",
                    on_input=on_input,
                    style=_STORY_INPUT_STYLE,
                )
                me.input(
                    key="story_character_location",
                    label="Where does the character live?",
                    value="Andromeda Galaxy",
                    on_input=on_input,
                    style=_STORY_INPUT_STYLE,
                )
                me.select(
                    key="story_selected_premises",
                    label="Story's premise",
                    options=[
                        me.SelectOption(label="Love", value="love"),
                        me.SelectOption(label="Adventure", value="adventure"),
                        me.SelectOption(label="Mystery", value="mystery"),
                        me.SelectOption(label="Horror", value="horror"),
                        me.SelectOption(label="Comedy", value="comedy"),
                        me.SelectOption(label="Sci-Fi", value="sci-fi"),
                        me.SelectOption(label="Fantasy", value="fantasy"),
                        me.SelectOption(label="Thriller", value="thriller"),
                    ],
                    multiple=True,
                    on_selection_change=on_selection_change,
                    value=state.story_selected_premises,
                )
                me.text("Story creativity")
                me.radio(
                    on_change=on_radio_change,
                    options=[
                        me.RadioOption(label="Low", value="low"),
                        me.RadioOption(label="High", value="high"),
                    ],
                    value=state.story_temp_value,
                )
                me.text("Length of story")
                me.radio(
                    on_change=on_length_radio_change,
                    options=[
                        me.RadioOption(label="Short", value="short"),
                        me.RadioOption(label="Long", value="long"),
                    ],
                    value=state.story_length_value,
                )
                with me.box(
                    style=me.Style(
                        display="flex", gap=10, padding=me.Padding(bottom=20)
                    )
                ):
                    me.button(
                        "Clear",
                        color="primary",
                        type="stroked",
                        on_click=on_click_clear_story,
                    )
                    me.button(
                        "Generate my story",
                        color="primary",
                        type="flat",
                        on_click=generate_story,
                    )

            with me.box(style=_BOX_STYLE):
                me.text("Output", style=me.Style(font_weight=500))
                if state.story_progress:
                    with me.box(style=_SPINNER_STYLE):
                        me.progress_spinner()
                        me.text("Generating story with Gemini 1.5 ...")
                if state.story_output:
                    with me.box(
                        style=me.Style(
                            display="grid",
                            justify_content="center",
                            justify_items="center",
                        )
                    ):
                        me.markdown(
                            key="story_output",
                            text=state.story_output,
                            style=me.Style(width="100%", margin=me.Margin(top=10)),
                        )


# Marketing page
@me.page(
    path="/marketing",
    title="Vertex AI Gemini with Mesop",
    security_policy=me.SecurityPolicy(
        allowed_iframe_parents=["https://google.github.io"]
    ),
)
def marketing_page() -> None:
    state = me.state(State)
    # Main header
    vertex_gemini_header()

    # Nav header
    nav_menu(state.current_page)
    # Main content
    with me.box(style=_STYLE_MAIN_COLUMN):
        me.text(text="Generate your marketing campaign", type="headline-6")

        with me.box(style=me.Style(display="flex", flex_direction="row", gap=15)):
            with me.box(style=me.Style(display="flex", flex_direction="column", gap=2)):
                # product name
                me.input(
                    key="marketing_product",
                    label="Name of your product",
                    value="ZomZoo",
                    on_input=on_input,
                    style=_STORY_INPUT_STYLE,
                )
                # category
                me.text("Select your product category")
                marketing_product_category_options = []
                for c in state.marketing_product_categories:
                    marketing_product_category_options.append(
                        me.RadioOption(label=c.title(), value=c)
                    )
                me.radio(
                    on_change=on_change_marketing_category,
                    options=marketing_product_category_options,
                    value=state.marketing_product_category,
                )
                # audience
                me.text("Select your target audience")
                me.text("Target age", type="caption")
                marketing_target_age_options = []
                for c in state.marketing_target_audiences:
                    marketing_target_age_options.append(
                        me.RadioOption(label=c.title(), value=c)
                    )

                me.radio(
                    on_change=on_change_marketing_target,
                    options=marketing_target_age_options,
                    value=state.marketing_target_audience,
                )
                me.text("Target location", type="caption")
                marketing_target_location_options = []
                for c in state.marketing_target_locations:
                    marketing_target_location_options.append(
                        me.RadioOption(label=c.title(), value=c)
                    )
                me.radio(
                    on_change=on_change_marketing_location,
                    options=marketing_target_location_options,
                    value=state.marketing_target_location,
                )
                # campaign goal
                me.text("Select your marketing campaign goal")
                me.text("Campaign goal", type="caption")
                marketing_campaign_goal_options = []
                for c in state.marketing_campaign_goals:
                    marketing_campaign_goal_options.append(
                        me.SelectOption(label=c.title(), value=c)
                    )
                me.select(
                    style=me.Style(width="50vh"),
                    key="marketing_campaign_goal",
                    label="Campaign goal",
                    options=marketing_campaign_goal_options,
                    multiple=True,
                    value=state.marketing_campaign_selected_goals,
                    on_selection_change=on_selection_change_marketing_goals,
                )
                me.text("Brand voice", type="caption")
                marketing_brand_voice_options = []
                for c in state.marketing_brand_voices:
                    marketing_brand_voice_options.append(
                        me.RadioOption(label=c.title(), value=c)
                    )
                me.radio(
                    on_change=on_change_marketing_brand_voice,
                    options=marketing_brand_voice_options,
                    value=state.marketing_brand_voice,
                )
                me.text("Estimated budget ($)", type="caption")
                marketing_budget_options = []
                for c in state.marketing_budgets:
                    marketing_budget_options.append(
                        me.RadioOption(label=c.title(), value=c)
                    )
                me.radio(
                    on_change=on_change_marketing_budget,
                    options=marketing_budget_options,
                    value=state.marketing_budget,
                )
                with me.box(
                    style=me.Style(
                        display="flex", gap=10, padding=me.Padding(bottom=20)
                    )
                ):
                    me.button(
                        "Clear",
                        color="primary",
                        type="stroked",
                        on_click=on_click_clear_marketing_campaign,
                    )
                    me.button(
                        "Generate my campaign",
                        color="primary",
                        type="flat",
                        on_click=generate_marketing_campaign,
                    )

            with me.box(style=_BOX_STYLE):
                me.text("Output", style=me.Style(font_weight=500))
                if state.marketing_campaign_output:
                    with me.box(
                        style=me.Style(
                            display="grid",
                            justify_content="center",
                            justify_items="center",
                        )
                    ):
                        me.markdown(
                            key="marketing_campaign_output",
                            text=state.marketing_campaign_output,
                            style=me.Style(width="100%", margin=me.Margin(top=10)),
                        )


# Image playground page
@me.page(
    path="/images",
    title="Vertex AI Gemini with Mesop",
    security_policy=me.SecurityPolicy(
        allowed_iframe_parents=["https://google.github.io"]
    ),
)
def image_playground_page() -> None:
    state = me.state(State)
    # Main header
    vertex_gemini_header()

    # Nav header
    nav_menu(state.current_page)

    # Main content
    with me.box(style=_STYLE_MAIN_COLUMN):
        me.text(text="Image playground", type="headline-6")

        image_playground_page_tabber()


image_tabs_json = [
    {"display": "Furniture Recommendation", "name": "furniture"},
    {"display": "Oven Instructions", "name": "oven"},
    {"display": "ER Diagrams", "name": "er"},
    {"display": "Glasses Recommendation", "name": "glasses"},
    {"display": "Math Reasoning", "name": "math"},
]


def image_switch_tab(e: me.ClickEvent) -> None:
    s = me.state(State)
    s.image_tab = e.key


def image_playground_page_tabber() -> None:
    state = me.state(State)

    with me.box(
        style=me.Style(
            padding=me.Padding(top=0, right=0, left=0, bottom=2),
            border=me.Border(
                bottom=me.BorderSide(color="#e5e5e5", width=1, style="solid"),
                top=None,
                right=None,
                left=None,
            ),
        ),
    ):
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=5)):
            for tab in image_tabs_json:
                disabled = False
                if state.image_tab == tab.get("name"):
                    disabled = True
                me.button(
                    tab.get("display"),
                    key=f"{tab.get('name')}",
                    on_click=image_switch_tab,
                    disabled=disabled,
                    style=_STYLE_CURRENT_TAB if disabled else _STYLE_OTHER_TAB,
                    # type="flat" if disabled else "stroked"
                )

    match state.image_tab:
        case "furniture":
            image_furniture_tab()
        case "oven":
            image_oven_tab()
        case "er":
            image_er_diagrams_tab()
        case "glasses":
            image_glasses_recommendations_tab()
        case "math":
            image_math_reasoning_tab()
        case _:
            image_furniture_tab()


def image_math_reasoning_tab() -> None:
    state = me.state(State)
    me.box(style=me.Style(height=12))
    me.text("Math Reasoning", style=me.Style(font_weight="bold"))
    me.box(style=me.Style(height=12))

    me.text(
        "Gemini 1.5 Pro can also recognize math formulas and equations and extract specific information from them. This capability is particularly useful for generating explanations for math problems, as shown below."
    )
    me.box(style=me.Style(height=12))

    with me.box(
        style=me.Style(display="grid", gap=0, grid_template_columns="repeat(4, 1fr)")
    ):

        with me.box(
            style=me.Style(
                display="grid",
                flex_direction="column",
                gap=2,
            )
        ):
            me.image(
                src=gcs_to_http(IMAGE_MATH),
                alt="math equation ",
                style=me.Style(width="350px"),
            )
            with me.box(
                style=me.Style(align_content="center", flex_grow=1, display="flex")
            ):
                me.text(
                    "image of a math equation",
                    style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
                )
    me.box(style=me.Style(height=12))

    me.text("Our expectation: Ask questions about the math equation as follows:")
    me.markdown(
        text="* Extract the formula.\n* What is the symbol right before Pi? What does it mean?\n* Is this a famous formula? Does it have a name?"
    )

    with me.box(style=me.Style(display="flex", gap=10, padding=me.Padding(bottom=20))):
        me.button(
            "Clear", color="primary", type="stroked", on_click=on_click_clear_math
        )
        me.button(
            "Generate answers",
            color="primary",
            type="flat",
            on_click=generate_math_answers,
        )

    with me.box(style=_BOX_STYLE):
        me.text("Recommendation", style=me.Style(font_weight=500))
        if state.math_answers_output:
            with me.box(
                style=me.Style(
                    display="grid",
                    justify_content="center",
                    justify_items="center",
                )
            ):
                me.markdown(
                    key="math_answers_output",
                    text=state.math_answers_output,
                    style=me.Style(width="100%", margin=me.Margin(top=10)),
                )


def image_glasses_recommendations_tab() -> None:
    state = me.state(State)
    me.box(style=me.Style(height=12))
    me.text("Glasses Recommendation", style=me.Style(font_weight="bold"))
    me.box(style=me.Style(height=12))

    me.text(
        "Gemini 1.5 is capable of image comparison and providing recommendations. This may be useful in industries like e-commerce and retail. Below is an example of choosing which pair of glasses would be better suited to various face types:"
    )
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(margin=me.Margin.all(15))):
        me.text("What is your face shape?")
        me.radio(
            on_change=on_change_image_glasses,
            key="glasses_shape",
            options=[
                me.RadioOption(label="Oval", value="oval"),
                me.RadioOption(label="Round", value="round"),
                me.RadioOption(label="Square", value="square"),
                me.RadioOption(label="Heart", value="heart"),
                me.RadioOption(label="Diamond", value="diamond"),
            ],
            value=state.image_glasses_shape_radio_value,
        )
        me.text("Select the output type")
        me.radio(
            on_change=on_change_image_glasses,
            key="glasses_output",
            options=[
                me.RadioOption(label="text", value="text"),
                me.RadioOption(label="table", value="table"),
                me.RadioOption(label="json", value="json"),
            ],
            value=state.image_glasses_output_radio_value,
        )

    with me.box(
        style=me.Style(display="grid", gap=0, grid_template_columns="repeat(4, 1fr)")
    ):

        with me.box(
            style=me.Style(
                display="grid",
                flex_direction="column",
                gap=2,
            )
        ):
            me.image(
                src=gcs_to_http(IMAGE_GLASSES_1),
                alt="glasses 1",
                style=me.Style(width="350px"),
            )
            with me.box(
                style=me.Style(align_content="center", flex_grow=1, display="flex")
            ):
                me.text(
                    "Glasses type 1",
                    style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
                )
        with me.box(style=me.Style(display="grid", flex_direction="column", gap=2)):
            me.image(
                src=gcs_to_http(IMAGE_GLASSES_2),
                alt="glasses 2",
                style=me.Style(width="350px"),
            )
            with me.box(
                style=me.Style(align_content="center", flex_grow=1, display="flex")
            ):
                me.text(
                    "Glasses type 2",
                    style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
                )

    me.box(style=me.Style(height=12))

    me.text(
        f"Our expectation: Suggest which glasses type is better for the {state.image_glasses_shape_radio_value} face shape"
    )
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="flex", gap=10, padding=me.Padding(bottom=20))):
        me.button(
            "Clear",
            color="primary",
            type="stroked",
            on_click=on_click_clear_glasses_rec,
        )
        me.button(
            "Generate recommendation",
            color="primary",
            type="flat",
            on_click=generate_glasses_rec,
        )

    with me.box(style=_BOX_STYLE):
        me.text("Recommendation", style=me.Style(font_weight=500))
        if state.glasses_rec_output:
            with me.box(
                style=me.Style(
                    display="grid",
                    justify_content="center",
                    justify_items="center",
                )
            ):
                me.markdown(
                    key="glasses_rec_output",
                    text=state.glasses_rec_output,
                    style=me.Style(width="100%", margin=me.Margin(top=10)),
                )


def image_er_diagrams_tab() -> None:
    state = me.state(State)
    me.box(style=me.Style(height=12))
    me.text("ER Diagrams", style=me.Style(font_weight="bold"))
    me.box(style=me.Style(height=12))

    me.text(
        "Gemini 1.5 multimodal capabilities empower it to comprehend diagrams and take actionable steps, such as optimization or code generation. The following example demonstrates how Gemini 1.0 can decipher an Entity Relationship (ER) diagram."
    )
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="grid", flex_direction="column", gap=2)):
        me.image(
            src=gcs_to_http(IMAGE_ER_DIAGRAM),
            alt="image of an entity relationship diagram",
            style=me.Style(width="350px"),
        )
        with me.box(
            style=me.Style(align_content="center", flex_grow=1, display="flex")
        ):
            me.text(
                "Image of an ER diagram",
                style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
            )
    me.box(style=me.Style(height=12))

    me.text(
        "Our expectation: Document the entities and relationships in this ER diagram."
    )
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="flex", gap=10, padding=me.Padding(bottom=20))):
        me.button(
            "Clear", color="primary", type="stroked", on_click=on_click_clear_er_doc
        )
        me.button(
            "Generate documentation",
            color="primary",
            type="flat",
            on_click=generate_er_doc,
        )

    with me.box(style=_BOX_STYLE):
        me.text("Documentation", style=me.Style(font_weight=500))
        if state.er_doc_output:
            with me.box(
                style=me.Style(
                    display="grid",
                    justify_content="center",
                    justify_items="center",
                )
            ):
                me.markdown(
                    key="er_doc_output",
                    text=state.er_doc_output,
                    style=me.Style(width="100%", margin=me.Margin(top=10)),
                )


def image_oven_tab() -> None:
    state = me.state(State)
    me.box(style=me.Style(height=12))
    me.text("Oven Instructions", style=me.Style(font_weight="bold"))
    me.box(style=me.Style(height=12))

    me.text(
        "Equipped with the ability to extract information from visual elements on screens, Gemini 1.5 Pro can analyze screenshots, icons, and layouts to provide a holistic understanding of the depicted scene."
    )
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="grid", flex_direction="column", gap=2)):
        me.image(
            src="https://storage.googleapis.com/github-repo/img/gemini/multimodality_usecases_overview/stove.jpg",
            alt="image of an oven",
            style=me.Style(width="350px"),
        )
        with me.box(
            style=me.Style(align_content="center", flex_grow=1, display="flex")
        ):
            me.text(
                "Image of an oven",
                style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
            )
    me.box(style=me.Style(height=12))

    me.text(
        "Our expectation: Provide instructions for resetting the clock on this appliance in English"
    )
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="flex", gap=10, padding=me.Padding(bottom=20))):
        me.button(
            "Clear",
            color="primary",
            type="stroked",
            on_click=on_click_clear_oven_instructions,
        )
        me.button(
            "Generate instructions",
            color="primary",
            type="flat",
            on_click=generate_oven_instructions,
        )

    with me.box(style=_BOX_STYLE):
        me.text("Instructions", style=me.Style(font_weight=500))
        if state.oven_instructions_output:
            with me.box(
                style=me.Style(
                    display="grid",
                    justify_content="center",
                    justify_items="center",
                )
            ):
                me.markdown(
                    key="oven_instrictions_output",
                    text=state.oven_instructions_output,
                    style=me.Style(width="100%", margin=me.Margin(top=10)),
                )


def image_furniture_tab() -> None:
    state = me.state(State)
    me.box(style=me.Style(height=12))
    me.text("Furniture Recommendation", style=me.Style(font_weight="bold"))
    me.box(style=me.Style(height=12))

    me.text(
        "In this example, you'll be presented with a scene (e.g. a living room) and will use the Gemini model to perform visual understanding. You will see how Gemini can be used to recommend an item (e.g., a chair) from a list of furniture options as input. You can use Gemini to recommend a chair that would complement the given scene and will be provided with its rationale for such selections from the provided list."
    )
    me.box(style=me.Style(height=12))

    room_image_urls = gcs_to_http(ROOM_IMAGE_URI)
    chair_1_image_urls = gcs_to_http(CHAIR_1_IMAGE_URI)
    chair_2_image_urls = gcs_to_http(CHAIR_2_IMAGE_URI)
    chair_3_image_urls = gcs_to_http(CHAIR_3_IMAGE_URI)
    chair_4_image_urls = gcs_to_http(CHAIR_4_IMAGE_URI)

    with me.box(style=me.Style(display="flex", flex_direction="column", gap=2)):
        me.image(
            src=room_image_urls,
            alt="living room",
            style=me.Style(width="350px"),
        )
        with me.box(
            style=me.Style(align_content="center", flex_grow=1, display="flex")
        ):
            me.text(
                "Image of a living room",
                style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
            )

    me.box(style=me.Style(height=12))

    with me.box(
        style=me.Style(display="grid", gap=0, grid_template_columns="repeat(4, 1fr)")
    ):

        with me.box(
            style=me.Style(
                display="grid",
                flex_direction="column",
                gap=2,
            )
        ):
            me.image(
                src=chair_1_image_urls,
                alt="chair1",
                style=me.Style(width="200px"),
            )
            with me.box(
                style=me.Style(align_content="center", flex_grow=1, display="flex")
            ):
                me.text(
                    "Chair 1",
                    style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
                )
        with me.box(style=me.Style(display="grid", flex_direction="column", gap=2)):
            me.image(
                src=chair_2_image_urls,
                alt="chair2",
                style=me.Style(width="200px"),
            )
            with me.box(
                style=me.Style(align_content="center", flex_grow=1, display="flex")
            ):
                me.text(
                    "Chair 2",
                    style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
                )
        with me.box(style=me.Style(display="grid", flex_direction="column", gap=2)):
            me.image(
                src=chair_3_image_urls,
                alt="chair3",
                style=me.Style(width="200px"),
            )
            with me.box(
                style=me.Style(align_content="center", flex_grow=1, display="flex")
            ):
                me.text(
                    "Chair 3",
                    style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
                )
        with me.box(style=me.Style(display="grid", flex_direction="column", gap=2)):
            me.image(
                src=chair_4_image_urls,
                alt="chair4",
                style=me.Style(width="200px"),
            )
            with me.box(
                style=me.Style(align_content="center", flex_grow=1, display="flex")
            ):
                me.text(
                    "Chair 4",
                    style=me.Style(color="rgba(49, 51, 63, 0.6)", font_size="14px"),
                )

    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="flex", gap=10, padding=me.Padding(bottom=20))):
        me.button(
            "Clear",
            color="primary",
            type="stroked",
            on_click=on_click_clear_furniture_recommendation,
        )
        me.button(
            "Generate a recommendation",
            color="primary",
            type="flat",
            on_click=generate_furniture_recommendation,
        )

    with me.box(style=_BOX_STYLE):
        me.text("Recommendation", style=me.Style(font_weight=500))
        if state.furniture_recommendation_output:
            with me.box(
                style=me.Style(
                    display="grid",
                    justify_content="center",
                    justify_items="center",
                )
            ):
                me.markdown(
                    key="furniture_recommendation_output",
                    text=state.furniture_recommendation_output,
                    style=me.Style(width="100%", margin=me.Margin(top=10)),
                )


# Video playground page
@me.page(
    path="/videos",
    title="Vertex AI Gemini with Mesop",
    security_policy=me.SecurityPolicy(
        allowed_iframe_parents=["https://google.github.io"]
    ),
)
def video_playground_page() -> None:
    state = me.state(State)
    # Main header
    vertex_gemini_header()

    # Nav header
    nav_menu(state.current_page)

    # Main content
    with me.box(style=_STYLE_MAIN_COLUMN):
        me.text(text="Video playground", type="headline-6")

        video_playground_page_tabber()


video_tabs_json = [
    {"display": "Video Description", "name": "desc"},
    {"display": "Video Tags", "name": "tags"},
    {"display": "Video Highlights", "name": "highlights"},
    {"display": "Video Geolocation", "name": "geo"},
]


def video_switch_tab(e: me.ClickEvent) -> None:
    s = me.state(State)
    s.video_tab = e.key


def video_playground_page_tabber() -> None:
    state = me.state(State)

    with me.box(
        style=me.Style(
            padding=me.Padding(top=0, right=0, left=0, bottom=2),
            border=me.Border(
                bottom=me.BorderSide(color="#e5e5e5", width=1, style="solid"),
                top=None,
                right=None,
                left=None,
            ),
        ),
    ):
        with me.box(style=me.Style(display="flex", flex_direction="row", gap=5)):
            for tab in video_tabs_json:
                disabled = False
                if state.image_tab == tab.get("name"):
                    disabled = True
                me.button(
                    tab.get("display"),
                    key=f"{tab.get('name')}",
                    on_click=image_switch_tab,
                    disabled=disabled,
                    style=_STYLE_CURRENT_TAB if disabled else _STYLE_OTHER_TAB,
                    # type="flat" if disabled else "stroked"
                )

    match state.image_tab:
        case "desc":
            video_description_tab()
        case "tags":
            video_tags_tab()
        case "highlights":
            video_highlights_tab()
        case "geo":
            video_geolocation_tab()
        case _:
            video_description_tab()


def video_description_tab() -> None:
    state = me.state(State)
    me.box(style=me.Style(height=24))
    me.text("Gemini can provide a description of what's happening in a video:")
    me.box(style=me.Style(height=12))

    video_desc_url = "gs://github-repo/img/gemini/multimodality_usecases_overview/mediterraneansea.mp4"
    state.video_url = video_desc_url
    video_desc_url = gcs_to_http(video_desc_url)

    me.video(
        src=video_desc_url,
        style=me.Style(width=704),
    )
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="flex", gap=10, padding=me.Padding(bottom=20))):
        me.button(
            "Clear",
            color="primary",
            type="stroked",
            on_click=on_click_clear_video_description,
        )
        me.button(
            "Generate a description",
            color="primary",
            type="flat",
            on_click=generate_video_description,
        )

    with me.box(style=_BOX_STYLE):
        me.text("Description", style=me.Style(font_weight=500))
        if state.video_description_content:
            with me.box(
                style=me.Style(
                    display="grid",
                    justify_content="center",
                    justify_items="center",
                )
            ):
                me.markdown(
                    key="video_description_content",
                    text=state.video_description_content,
                    style=me.Style(width="100%", margin=me.Margin(top=10)),
                )


def video_tags_tab() -> None:
    state = me.state(State)
    me.box(style=me.Style(height=24))

    me.text("Gemini 1.5 can also extract tags throughout a video, as shown below:")
    me.box(style=me.Style(height=12))

    me.video(
        key="tags",
        src=gcs_to_http(VIDEO_TAGS),
        style=me.Style(width=704),
    )
    me.box(style=me.Style(height=12))

    me.text("Our expectation: Generate the tags for the video.")
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="flex", gap=10, padding=me.Padding(bottom=20))):
        me.button(
            "Clear",
            color="primary",
            type="stroked",
            on_click=on_click_clear_video_tags,
        )
        me.button(
            "Generate video tags",
            color="primary",
            type="flat",
            on_click=generate_video_tags,
        )

    with me.box(style=_BOX_STYLE):
        me.text("Tags", style=me.Style(font_weight=500))
        if state.video_tags_content:
            with me.box(
                style=me.Style(
                    display="grid",
                    justify_content="center",
                    justify_items="center",
                )
            ):
                me.markdown(
                    key="video_tags_content",
                    text=state.video_tags_content,
                    style=me.Style(width="100%", margin=me.Margin(top=10)),
                )


def video_highlights_tab() -> None:
    state = me.state(State)
    me.box(style=me.Style(height=24))

    me.text(
        "Another example of using Gemini 1.5 is to ask questions about objects, people or the context, as shown in the video about Pixel 8 below:"
    )
    me.box(style=me.Style(height=12))

    me.video(
        key="highlights",
        src=gcs_to_http(VIDEO_HIGHLIGHTS),
        style=me.Style(width=704),
    )
    me.box(style=me.Style(height=12))

    me.text("Our expectation: Generate the highlights for the video.")
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="flex", gap=10, padding=me.Padding(bottom=20))):
        me.button(
            "Clear",
            color="primary",
            type="stroked",
            on_click=on_click_clear_video_tags,
        )
        me.button(
            "Generate highlights",
            color="primary",
            type="flat",
            on_click=generate_video_highlights,
        )

    with me.box(style=_BOX_STYLE):
        me.text("Highlights", style=me.Style(font_weight=500))
        if state.video_highlights_content:
            with me.box(
                style=me.Style(
                    display="grid",
                    justify_content="center",
                    justify_items="center",
                )
            ):
                me.markdown(
                    key="video_highlights_content",
                    text=state.video_highlights_content,
                    style=me.Style(width="100%", margin=me.Margin(top=10)),
                )


def video_geolocation_tab() -> None:
    state = me.state(State)
    me.box(style=me.Style(height=24))

    me.text(
        "Even in short, detail-packed videos, Gemini 1.5 can identify the locations."
    )
    me.box(style=me.Style(height=12))

    me.video(
        key="geo",
        src=gcs_to_http(VIDEO_GEOLOCATION),
        style=me.Style(width=704),
    )
    me.box(style=me.Style(height=12))

    me.text("Our expectation: answers about the location of the video")
    me.box(style=me.Style(height=12))

    with me.box(style=me.Style(display="flex", gap=10, padding=me.Padding(bottom=20))):
        me.button(
            "Clear",
            color="primary",
            type="stroked",
            on_click=on_click_clear_video_tags,
        )
        me.button(
            "Generate ",
            color="primary",
            type="flat",
            on_click=generate_video_geolocation,
        )

    with me.box(style=_BOX_STYLE):
        me.text("Geolocation info", style=me.Style(font_weight=500))
        if state.video_geolocation_content:
            with me.box(
                style=me.Style(
                    display="grid",
                    justify_content="center",
                    justify_items="center",
                )
            ):
                me.markdown(
                    key="video_geolocation_content",
                    text=state.video_geolocation_content,
                    style=me.Style(width="100%", margin=me.Margin(top=10)),
                )


# Styles

_DEFAULT_BORDER = me.Border.all(me.BorderSide(color="#e0e0e0", width=1, style="solid"))

_STYLE_CONTAINER = me.Style(
    display="grid",
    grid_template_columns="5fr 2fr",
    grid_template_rows="auto 5fr",
    height="100vh",
)

_STYLE_MAIN_HEADER = me.Style(
    border=_DEFAULT_BORDER, padding=me.Padding(top=15, left=15, right=15, bottom=5)
)

_STYLE_MAIN_COLUMN = me.Style(
    border=_DEFAULT_BORDER,
    padding=me.Padding.all(15),
    overflow_y="scroll",
)

_STYLE_TITLE_BOX = me.Style(display="inline-block")

_STORY_INPUT_STYLE = me.Style(
    width="500px"
    # display="flex",
    # flex_basis="max(100vh, calc(50% - 48px))",
)

_BOX_STYLE = me.Style(
    flex_basis="max(100vh, calc(50% - 48px))",
    background="#fff",
    border_radius=12,
    box_shadow=("0 3px 1px -2px #0003, 0 2px 2px #00000024, 0 1px 5px #0000001f"),
    padding=me.Padding(top=16, left=16, right=16, bottom=16),
    display="flex",
    flex_direction="column",
)

_SPINNER_STYLE = me.Style(
    display="flex",
    flex_direction="row",
    padding=me.Padding.all(16),
    align_items="center",
    gap=10,
)

FANCY_TEXT_GRADIENT = me.Style(
    color="transparent",
    background=(
        "linear-gradient(72.83deg,#4285f4 11.63%,#9b72cb 40.43%,#d96570 68.07%)" " text"
    ),
)

_STYLE_CURRENT_TAB = me.Style(
    color="#99000",
    border_radius=0,
    font_weight="bold",
    border=me.Border(
        bottom=me.BorderSide(color="#000", width=2, style="solid"),
        top=None,
        right=None,
        left=None,
    ),
)

_STYLE_OTHER_TAB = me.Style(
    color="#8d8e9d",
    border_radius=0,
    # font_weight="bold",
)
