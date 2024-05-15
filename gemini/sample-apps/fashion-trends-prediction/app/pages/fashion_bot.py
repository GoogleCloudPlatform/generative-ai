# pylint: disable=E0401

import base64
import io
import json
import time

from config import config
from gcs import read_file_from_gcs_link
from genai_prompts import FASHION_BOT_IMG_GEN_INTENT, fashion_bot_context
from google.api_core.exceptions import InvalidArgument
import streamlit as st
from utilities import add_logo
from utils_standalone_image_gen import image_generation, render_image_edit_prompt
import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel
from vertexai.preview.generative_models import HarmBlockThreshold, HarmCategory

add_logo(config["Images"]["logo"])


PROJECT_ID = config["PROJECT_ID"]  # @param {type:"string"}
LOCATION = config["LOCATION"]  # @param {type:"string"}
DATA_PATH = config["Data"]["current_data"]

params = config["parameters"]["fashion_bot"]
generation_config = GenerationConfig(
    max_output_tokens=params["max_output_tokens"],
    temperature=params["temperature"],
    top_p=params["top_p"],
    top_k=params["top_k"],
)
safety_settings = {
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
}


st.image(image=config["Images"]["chat"], width=200)

if "JSONdata" not in st.session_state:
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    st.session_state["JSONdata"] = read_file_from_gcs_link(DATA_PATH)


country = st.selectbox(
    "Select Country", st.session_state["JSONdata"]["finaldata"].keys()
)

category = st.selectbox(
    "Select category of outfit?",
    list(
        map(
            lambda x: x.capitalize(),
            st.session_state["JSONdata"]["top_categories"][country],
        )
    ),
)


prompt = st.chat_input("Ask Something")

if prompt:
    st.session_state["prompt"] = prompt
    st.rerun()


category = category.lower()

cat_key = "chat-context" + country + category

if cat_key not in st.session_state:
    st.session_state[cat_key] = fashion_bot_context(
        country, category, st.session_state["JSONdata"]["finaldata"]
    )

bot_key = "bot" + country + category


if bot_key in st.session_state:
    bot = st.session_state[bot_key]
else:
    model = GenerativeModel(
        model_name="gemini-1.0-pro-002", system_instruction=[st.session_state[cat_key]]
    )
    bot = model.start_chat()

    st.session_state[bot_key] = bot


hist_key = "chatHistory" + country + category


if hist_key not in st.session_state:
    with st.spinner("Loading Chatbot..."):
        st.session_state[hist_key] = [
            ["assistant", "Ask me anything about " + category + " outfits"]
        ]


with st.container(border=True):
    # chat history
    for i in range(len(st.session_state[hist_key])):
        chat = st.session_state[hist_key][i]
        if chat[0] == "image":
            st.image(chat[1], width=200)

            col1, col2 = st.columns(2, gap="small")
            stamp = chat[3]
            edit_img_key = "img " + str(stamp)
            with col1:
                st.download_button(
                    label=":arrow_down:",
                    key=f"_btn_download_{stamp}",
                    data=chat[1],
                    file_name="image.png",
                )
            with col2:
                if st.button(label=":pencil2:", key=f"image: {stamp}"):
                    st.session_state[edit_img_key] = chat[1]
                    st.session_state[hist_key][i][2] = True

            if st.session_state[hist_key][i][2]:
                render_image_edit_prompt(
                    "edit_image_prompt_key" + str(stamp),
                    "edited_images_key" + str(stamp),
                    False,
                    edit_img_key,
                    "edit_with_mask" + str(stamp),
                    "mask_image_key" + str(stamp),
                    True,
                )

            continue

        st.chat_message(chat[0]).write(chat[1])

    if "prompt" in st.session_state and st.session_state["prompt"] != "":
        st.chat_message("user").write(st.session_state["prompt"])
        st.session_state[hist_key].append(["user", st.session_state["prompt"]])

        words_list = ["generate", "create", "produce", "show", "image"]

        with st.spinner("Generating response..."):
            if any(word in st.session_state["prompt"].lower() for word in words_list):
                intented_outfit = bot.send_message(
                    FASHION_BOT_IMG_GEN_INTENT.format(st.session_state["prompt"]),
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                ).text
                gen_prompt = "Outfit - " + intented_outfit + " " + category

                try:
                    _imgs = image_generation(
                        prompt=gen_prompt, sample_count=1, state_key="imagen_image"
                    )

                    imgs = [_img._image_bytes for _img in _imgs]
                    st.session_state[hist_key].append(
                        ["image", imgs[0], False, time.time()]
                    )
                    st.image(imgs[0], width=200)

                except InvalidArgument as e:
                    res_text = "Invalid prompt. Try again."
                    st.chat_message("assistant").write(res_text)
                    st.session_state[hist_key].append(["assistant", res_text])

            else:
                res = bot.send_message(
                    st.session_state["prompt"],
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                )
                res_text = res.text

                st.chat_message("assistant").write(res.text)
                st.session_state[hist_key].append(["assistant", res_text])

        st.session_state["prompt"] = ""
        st.rerun()
