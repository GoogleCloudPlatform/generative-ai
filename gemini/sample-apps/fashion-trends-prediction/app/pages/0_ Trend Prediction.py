import base64
import io
import json
from io import StringIO

import streamlit as st
import streamlit.components.v1 as components
import vertexai
import vertexai.preview.generative_models as generative_models
from articles import Articles
from config import config
from genAIprompts import image_prompt, trends_prompt
from prediction import Prediction
from utilities import add_logo, stImg
from utils_standalone_image_gen import predict_image
from vertexai.preview.generative_models import GenerativeModel

PROJECT_ID = config["PROJECT_ID"]  # @param {type:"string"}
LOCATION = config["LOCATION"]  # @param {type:"string"}
DATA_PATH = config["Data"]["current_data"]

print("DATA_PATH: ", DATA_PATH)

if "gemini_modal" not in st.session_state:
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    st.session_state["gemini_modal"] = GenerativeModel("gemini-1.0-pro-vision-001")

if "source" not in st.session_state:
    st.session_state["source"] = "Insta"

if "JSONdata" not in st.session_state:
    with open(DATA_PATH, "r") as f:
        st.session_state["JSONdata"] = json.load(f)

    with open(DATA_PATH, "r") as f:
        st.session_state["JSONdata2"] = json.load(f)


def generate(image_gen_instruction):
    """Generates text using the Gemini model.

    Args:
        image_gen_instruction (str): The text prompt to generate images from.

    Returns:
        str: The generated text.
    """
    response = st.session_state["gemini_modal"].generate_content(
        image_gen_instruction,
        generation_config={
            "max_output_tokens": 2048,
            "temperature": 0.2,
            "top_p": 1,
            "top_k": 32,
        },
        safety_settings={
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        },
        stream=False,
    )

    return response.text


def get_generic_trends(prompt):
    """Generates generic trends using the Gemini model.

    Args:
        prompt (str): The text prompt to generate generic trends from.

    Returns:
        str: The generated text.
    """
    response = st.session_state["gemini_modal"].generate_content(
        prompt,
        generation_config={
            "max_output_tokens": 2048,
            "temperature": 0.4,
            "top_p": 0.4,
            "top_k": 32,
        },
    )
    return response.text


add_logo(config["Images"]["logo"])
st.image(image=stImg(config["Images"]["trend"]))
st.title("Fashion Trend Prediction")

uploaded_file = st.file_uploader("Choose a file (optional)")

if uploaded_file is not None and st.session_state["source"] != uploaded_file.name:
    print("!!!inside uploaded_file if block!!!")
    stringio = StringIO(uploaded_file.getvalue().decode("utf-8"))
    string_data = stringio.read()
    st.session_state["source"] = uploaded_file.name
    st.session_state["JSONdata"] = json.loads(string_data)

    st.session_state["predictionModel"] = Prediction(st.session_state["JSONdata"])

    st.session_state["articleModel"] = Articles(
        st.session_state["JSONdata2"]["articles"]
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
        st.session_state["JSONdata2"]["articles"]
    )
articles = st.session_state["articleModel"]


submit = st.button("Get trend predictions", type="primary")


def change_button_colour(widget_label, prsd_status):
    """Changes the color of a button based on its pressed status.

    Args:
        widget_label (str): The label of the button.
        prsd_status (bool): True if the button is pressed, False otherwise.
    """
    btn_bg_colour = pressed_colour if prsd_status == True else unpressed_colour
    htmlstr = f"""
        <script>
            var elements = window.parent.document.querySelectorAll('button');
            for (var i = 0; i < elements.length; ++i) {{
                if (elements[i].innerText == '{widget_label}') {{
                    elements[i].style.color = '{btn_bg_colour[0]}';  // Set text color
                    elements[i].style.borderColor = '{btn_bg_colour[1]}';  // Change border color
                    elements[i].style.display = 'inline-block'; // Or 'block' if that's your original layout
                }}
            }}
        </script>
        """
    components.html(f"{htmlstr}", height=0, width=0)


def chk_btn_status_and_assign_colour(buttons):
    """Checks the pressed status of a list of buttons and assigns colors accordingly.

    Args:
        buttons (list): A list of button labels.
    """
    for i in range(len(buttons)):
        change_button_colour(buttons[i], state["btn_prsd_status"][i])


def btn_pressed_callback(i):
    """Callback function for when a button is pressed.

    Args:
        i (int): The index of the button that was pressed.
    """
    # toggle
    if state["btn_prsd_status"][i]:  # button was pressed
        state["btn_prsd_status"][i] = False

    else:  # button was not pressed
        state["btn_prsd_status"] = [False] * len(
            state["btn_prsd_status"]
        )  # unpress other buttons
        state["btn_prsd_status"][i] = True


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
            resp = get_generic_trends(
                trends_prompt.format(
                    data=st.session_state["JSONdata"]["finaldata"][country][category],
                    category=category,
                )
            )

            try:
                start_index = resp.find("{")
                end_index = resp.rfind("}")

                resp = resp[start_index : end_index + 1]

                response = json.loads(resp)
                state["summary"] = response

            except Exception as error:
                print("An error occurred:", error)
                state["summary"] = ""

        state["items"] = [i.capitalize() for i in state["items"]]
        state["additional_outfits"] = [
            [i.capitalize() for i in l] for l in state["additional_outfits"]
        ]

        print(state["items"])
        print(state["additional_outfits"])

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
                index = state["btn_prsd_status"].index(True)
            except ValueError:
                index = -1

            if index != -1:
                selected_button = index

                outfit = str(state["items"][selected_button])

                if outfit not in state:
                    state[outfit] = {}

                with st.spinner("Loading..."):
                    try:
                        print(state.keys())
                        if state[outfit] == {}:
                            _imgs = predict_image(
                                instance_dict={
                                    "prompt": generate(
                                        image_prompt.format(outfit=outfit)
                                    )
                                },
                                parameters={
                                    "sampleCount": 1,
                                    "sampleImageSize": 512,
                                    "aspectRatio": "1:1",
                                },
                            )

                            state[outfit]["imgs"] = [
                                io.BytesIO(base64.b64decode(_img["bytesBase64Encoded"]))
                                for _img in _imgs
                            ]

                        if len(state[outfit]["imgs"]) > 0:
                            st.image(state[outfit]["imgs"][0], use_column_width=True)

                            st.download_button(
                                label="Download",
                                key=f"_btn_download_{str(0) + ' ' + outfit}",
                                data=state[outfit]["imgs"][0],
                                file_name="image.png",
                            )

                        else:
                            st.markdown(
                                """
                                    <style>
                                    .box-container {
                                        border: 1px solid gray;
                                        padding: 120px;
                                        border-radius: 5px;
                                        background-color: #f5f5f5;
                                    }
                                    </style>
                                    <div class="box-container">
                                        Image generation failed due to responsible AI restrictions.
                                    </div>
                                    """,
                                unsafe_allow_html=True,
                            )

                    except Exception as error:
                        st.markdown(
                            """
                                    <style>
                                    .box-container {
                                        border: 1px solid gray;
                                        padding: 120px;
                                        border-radius: 5px;
                                        background-color: #f5f5f5;
                                    }
                                    </style>
                                    <div class="box-container">
                                        Image generation failed due to responsible AI restrictions.
                                    </div>
                                    """,
                            unsafe_allow_html=True,
                        )
                        print("error in generating imgs: ", error)

                st.write("")
                if len(state["additional_outfits"][selected_button]) > 0:
                    st.write("##### Similar: ")

                for item in state["additional_outfits"][selected_button]:
                    st.markdown(f" - {item}")

                if country == "India":
                    st.write("#### Relevant Articles")
                    none_found = True

                    if "relevant_articles" not in state[outfit]:
                        with st.spinner("Fetching relevant articles..."):
                            print(state["items"][selected_button])
                            state[outfit]["relevant_articles"] = articles.getArticles(
                                state["items"][selected_button][0].lower()
                            )

                    for article in state[outfit]["relevant_articles"]:
                        st.write(article[0])
                        st.link_button("Vogue Link", article[1])
                        none_found = False

                    if none_found:
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
        details_content = ""
        for index, (key, values) in enumerate(response.items()):
            values = [value for idx, value in enumerate(values, start=1)]
            print("values: ", values)
            values = [v.capitalize() for v in values]
            print("values: ", values)
            values_str = ",&nbsp;&nbsp;&nbsp;".join(
                [f"{idx}. {value}" for idx, value in enumerate(values, start=1)]
            )
            print("values_str: ", values_str)
            if index != len(response) - 1:
                details_content += f"""
                                    <style>
                                    .box-container {{
                                        border: 1px solid gray;
                                        padding: 10px;
                                        border-radius: 5px;
                                        background-color: #f5f5f5;
                                        margin: 15px;
                                    }}
                                    </style>
                                    <div class="box-container">
                                        <summary style='list-style: none;'><span style='color: #ff4c4b; font-size: 17px;'>{key}:<br> </span></summary><div><span style='font-size: 16px;'>{values_str}<br></span></div>
                                    </div>
                                    """

        st.markdown(details_content, unsafe_allow_html=True)
