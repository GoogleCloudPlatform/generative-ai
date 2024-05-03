import base64
import io
import json
import time

from config import config
from gcs import read_file_from_gcs_link
from google.api_core.exceptions import InvalidArgument
import streamlit as st
from utilities import add_logo
from utils_standalone_image_gen import image_generation, render_image_edit_prompt
import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel
import vertexai.preview.generative_models as generative_models

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
    generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
    generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
}


st.image(image=config["Images"]["chat"], width=200)

if "JSONdata" not in st.session_state:
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    st.session_state["JSONdata"] = read_file_from_gcs_link(DATA_PATH)


def img_gen_prompt(text: str) -> str:
    """Generates a prompt for image generation based on the given text.

    Args:
        text (str): The text to generate the prompt from.

    Returns:
        str: The generated prompt.

    """
    query = """
                "{}", what does the user want to generate image of based on current chat history? Strictly give the name of the outfit only.
            """.format(
        text
    )
    print(query)
    res = bot.send_message(
        query, generation_config=generation_config, safety_settings=safety_settings
    )
    prompt = "Outfit - " + res.text
    return prompt


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

if cat_key in st.session_state:
    context = st.session_state[cat_key]
else:
    context = f"""You are a fashion expert in {category}. Answer fashion related queries solely based on the data provided.

    Important points -
    - The data provided represents what popular influencers are wearing nowadays
    - If user asks about something that is not present in the data, answer that it is not trending in fashion
    - Popularity of an item is proportional to its counts in the data
    - If item is not in data provided, it is not fashionable.

    {category.capitalize()} data - """

    words = 0
    if category in st.session_state["JSONdata"]["finaldata"][country]:
        for outfit in st.session_state["JSONdata"]["finaldata"][country][category]:
            if isinstance(outfit, str):
                context += outfit + ", "
                words += 1
            if words > 3000:
                break

    st.session_state[cat_key] = context

bot_key = "bot" + country + category


if bot_key in st.session_state:
    bot = st.session_state[bot_key]
else:
    model = GenerativeModel("gemini-1.0-pro-002")
    bot = model.start_chat()

    st.session_state[bot_key] = bot


hist_key = "chatHistory" + country + category
img_gen_one_shot = ""


if hist_key not in st.session_state:
    with st.spinner("Loading Chatbot..."):
        bot.send_message(st.session_state[cat_key])
        bot.send_message(
            "answer based on data you have about " + category + "",
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        bot.send_message(
            "based on frequency of semantically similar items, what are top 5 frequent items?",
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        time.sleep(10)
        bot.send_message(
            "don't mention counts with answer ",
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        bot.send_message(
            "assume popularity depends on frequency in given data",
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
        bot.send_message(
            "if item is not present in given data, assume its not trending",
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
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
                    "select_button",
                    "selected_image_key",
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
                gen_prompt = img_gen_prompt(st.session_state["prompt"]) + " " + category
                print(gen_prompt)
                try:
                    _imgs = image_generation(
                        prompt=gen_prompt + " " + category,
                        sample_count=1,
                        state_key="imagen_image",
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
