"""The page that computes and displays the predicted fashion trends"""

# pylint: disable=E0401

from io import StringIO
import json
import logging

from articles import Articles
from config import config
from gcs import read_file_from_gcs_link
from genai_prompts import IMAGE_PROMPT, TRENDS_PROMPT
from prediction import Prediction
import streamlit as st
import streamlit.components.v1 as components
from utilities import EXCEPTION_HTML, add_logo, button_html_script, details_html
from utils_standalone_image_gen import image_generation
import vertexai
from vertexai.preview.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
)

logging.basicConfig(level=logging.INFO)

PROJECT_ID = config["PROJECT_ID"]  # @param {type:"string"}
LOCATION = config["LOCATION"]  # @param {type:"string"}
DATA_PATH = config["Data"]["current_data"]


def change_button_colour(widget_label: str, prsd_status: bool) -> None:
    """Changes the color of a button based on its pressed status.

    Args:
        widget_label (str): The label of the button.
        prsd_status (bool): True if the button is pressed, False otherwise.
    """
    btn_bg_colour = pressed_colour if prsd_status is True else unpressed_colour
    htmlstr = button_html_script(
        widget_label=widget_label,
        btn_bg_color1=btn_bg_colour[0],
        btn_bg_color2=btn_bg_colour[1],
    )

    components.html(f"{htmlstr}", height=0, width=0)


def chk_btn_status_and_assign_colour(buttons_list: list) -> None:
    """Checks the pressed status of a list of buttons and assigns colors accordingly.

    Args:
        buttons_list (list): A list of button labels.
    """
    for i_index, button in enumerate(buttons_list):
        change_button_colour(button, state["btn_prsd_status"][i_index])


def btn_pressed_callback(i_index: int) -> None:
    """Callback function for when a button is pressed.

    Args:
        i_index (int): The index of the button that was pressed.
    """
    # toggle
    if state["btn_prsd_status"][i_index]:  # button was pressed
        state["btn_prsd_status"][i_index] = False

    else:  # button was not pressed
        state["btn_prsd_status"] = [False] * len(
            state["btn_prsd_status"]
        )  # unpress other buttons
        state["btn_prsd_status"][i_index] = True


if "gemini_model" not in st.session_state:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    st.session_state["gemini_model"] = GenerativeModel("gemini-1.0-pro-vision-001")

if "source" not in st.session_state:
    st.session_state["source"] = "Insta"

if "JSONdata" not in st.session_state:
    st.session_state["JSONdata"] = read_file_from_gcs_link(DATA_PATH)

add_logo(config["Images"]["logo"])
st.image(image=config["Images"]["trend"])
st.title("Fashion Trend Prediction")

uploaded_file = st.file_uploader("Choose a file (optional)")

if uploaded_file is not None and st.session_state["source"] != uploaded_file.name:
    string_data = StringIO(uploaded_file.getvalue().decode("utf-8")).read()
    st.session_state["source"] = uploaded_file.name
    st.session_state["JSONdata"] = json.loads(string_data)

    st.session_state["predictionModel"] = Prediction(st.session_state["JSONdata"])

    st.session_state["articleModel"] = Articles(
        st.session_state["JSONdata"]["articles"]
    )


if "JSONdata" in st.session_state:
    country = st.selectbox(
        "Select Country", st.session_state["JSONdata"]["finaldata"].keys()
    )

    category = st.selectbox(
        "Select category of outfit",
        list(
            map(
                lambda x: x.capitalize(),
                st.session_state["JSONdata"]["top_categories"][country],
            )
        ),
    )

    category = category.lower()
    key = st.session_state["source"] + country + "" + category


if "predictionModel" not in st.session_state:
    st.session_state["predictionModel"] = Prediction(st.session_state["JSONdata"])
prediction_model = st.session_state["predictionModel"]

if "articleModel" not in st.session_state:
    st.session_state["articleModel"] = Articles(
        st.session_state["JSONdata"]["articles"]
    )
articles = st.session_state["articleModel"]


submit = st.button("Get trend predictions", type="primary")


if submit or key in st.session_state:
    if key not in st.session_state:
        st.session_state[key] = {}

    state = st.session_state[key]

    if submit:
        with st.spinner("Getting trending outfits..."):
            state["items"], state["additional_outfits"] = prediction_model.query(
                category, country
            )

        state["btn_prsd_status"] = [False] * len(state["items"])

        # generic trends
        with st.spinner("Computing overall trends across attributes..."):
            prompt_for_generic_trends = TRENDS_PROMPT.format(
                data=st.session_state["JSONdata"]["finaldata"][country][category],
                category=category,
            )
            resp = (
                st.session_state["gemini_model"]
                .generate_content(
                    prompt_for_generic_trends,
                    generation_config=GenerationConfig(
                        max_output_tokens=2048,
                        temperature=0.4,
                        top_p=0.4,
                        top_k=32,
                    ),
                )
                .text
            )

            try:
                start_index = resp.find("{")
                end_index = resp.rfind("}")

                resp = resp[slice(start_index, end_index + 1)]

                response = json.loads(resp)
                state["summary"] = response

            except (IndexError, json.decoder.JSONDecodeError) as error:
                state["summary"] = ""
                print(error)

        state["items"] = [i.capitalize() for i in state["items"]]
        state["additional_outfits"] = [
            [i.capitalize() for i in list_var]
            for list_var in state["additional_outfits"]
        ]

        logging.info(state["items"])
        logging.info(state["additional_outfits"])

    outer_tabs = st.tabs(
        ["### Trending outfits", "### Overall trends across attributes"]
    )
    with outer_tabs[0]:
        col1, col2 = st.columns([1, 1.5])
        buttons = state["items"]

        unpressed_colour = ["#31333f", "#d6d6d8"]  # black, grey
        pressed_colour = ["#ff4c4b", "#ff4c4b"]  # red, red

        with col1:
            for i, button_label in enumerate(buttons):
                st.button(
                    button_label,
                    key=f"btn_{i}",
                    on_click=btn_pressed_callback,
                    args=(i,),
                )
            chk_btn_status_and_assign_colour(buttons)
        with col2:
            try:
                INDEX_VAL = state["btn_prsd_status"].index(True)
            except ValueError:
                INDEX_VAL = -1

            if INDEX_VAL != -1:
                selected_button = INDEX_VAL

                OUTFIT = str(state["items"][selected_button])

                if OUTFIT not in state:
                    state[OUTFIT] = {}

                with st.spinner("Loading..."):
                    print(state.keys())
                    if state[OUTFIT] == {}:
                        THRESHOLD = HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE
                        prompt = (
                            st.session_state["gemini_model"]
                            .generate_content(
                                IMAGE_PROMPT.format(outfit=OUTFIT),
                                generation_config=GenerationConfig(
                                    max_output_tokens=2048,
                                    temperature=0.2,
                                    top_p=1,
                                    top_k=32,
                                ),
                                safety_settings={
                                    HarmCategory.HARM_CATEGORY_HATE_SPEECH: THRESHOLD,
                                    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: THRESHOLD,
                                    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: THRESHOLD,
                                    HarmCategory.HARM_CATEGORY_HARASSMENT: THRESHOLD,
                                },
                                stream=False,
                            )
                            .text
                        )

                        state[OUTFIT]["imgs"] = [
                            _img._image_bytes
                            for _img in image_generation(
                                prompt=prompt,
                                sample_count=1,
                                state_key="imagen_image",
                            )
                        ]

                    if len(state[OUTFIT]["imgs"]) > 0:
                        st.image(state[OUTFIT]["imgs"][0], use_column_width=True)

                        st.download_button(
                            label="Download",
                            key=f"_btn_download_{str(0) + ' ' + OUTFIT}",
                            data=state[OUTFIT]["imgs"][0],
                            file_name="image.png",
                        )

                    else:
                        st.markdown(
                            EXCEPTION_HTML,
                            unsafe_allow_html=True,
                        )

                st.write("")
                if len(state["additional_outfits"][selected_button]) > 0:
                    st.write("##### Similar: ")

                for item in state["additional_outfits"][selected_button]:
                    st.markdown(f" - {item}")

                if country == "India":
                    st.write("#### Relevant Articles")
                    NONE_FOUND = True

                    if "relevant_articles" not in state[OUTFIT]:
                        with st.spinner("Fetching relevant articles..."):
                            print(state["items"][selected_button])
                            state[OUTFIT]["relevant_articles"] = articles.get_articles(
                                state["items"][selected_button][0].lower()
                            )

                    for article in state[OUTFIT]["relevant_articles"]:
                        st.write(article[0])
                        st.link_button("Vogue Link", article[1])
                        NONE_FOUND = False

                    if NONE_FOUND:
                        st.write("No relevant articles found")

            else:
                st.markdown(
                    """
                            <style>
                            div.stMarkdown div.css-17eq0hr {
                                text-align: center;
                            }
                            </style>
                            """,
                    unsafe_allow_html=True,
                )
                st.write("###### Select an item to view details")

    with outer_tabs[1]:
        response = state["summary"]
        DETAILS_CONTENT = ""
        for index, (key, values) in enumerate(response.items()):
            values = [value for idx, value in enumerate(values, start=1)]
            print("values: ", values)
            values = [v.capitalize() for v in values]
            print("values: ", values)
            VALUES_STR = ",&nbsp;&nbsp;&nbsp;".join(
                [f"{idx}. {value}" for idx, value in enumerate(values, start=1)]
            )
            if index != len(response) - 1:
                DETAILS_CONTENT += details_html(key=key, values_str=VALUES_STR)

        st.markdown(DETAILS_CONTENT, unsafe_allow_html=True)
