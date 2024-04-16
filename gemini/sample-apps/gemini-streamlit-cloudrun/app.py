import os

import streamlit as st
import vertexai
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
    Part,
)

PROJECT_ID = os.environ.get("GCP_PROJECT")  # Your Google Cloud Project ID
LOCATION = os.environ.get("GCP_REGION")  # Your Google Cloud Project Region
vertexai.init(project=PROJECT_ID, location=LOCATION)


@st.cache_resource
def load_models():
    """
    Load the generative models for text and multimodal generation.

    Returns:
        Tuple: A tuple containing the text model and multimodal model.
    """
    text_model_pro = GenerativeModel("gemini-1.0-pro")
    multimodal_model_pro = GenerativeModel("gemini-1.0-pro-vision")
    return text_model_pro, multimodal_model_pro


def get_gemini_pro_text_response(
    model: GenerativeModel,
    contents: str,
    generation_config: GenerationConfig,
    stream: bool = True,
):
    safety_settings = {
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    responses = model.generate_content(
        prompt,
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=stream,
    )

    final_response = []
    for response in responses:
        try:
            # st.write(response.text)
            final_response.append(response.text)
        except IndexError:
            # st.write(response)
            final_response.append("")
            continue
    return " ".join(final_response)


def get_gemini_pro_vision_response(
    model, prompt_list, generation_config={}, stream: bool = True
):
    generation_config = {"temperature": 0.1, "max_output_tokens": 2048}
    responses = model.generate_content(
        prompt_list, generation_config=generation_config, stream=stream
    )
    final_response = []
    for response in responses:
        try:
            final_response.append(response.text)
        except IndexError:
            pass
    return "".join(final_response)


st.header("Vertex AI Gemini 1.0 API", divider="rainbow")
text_model_pro, multimodal_model_pro = load_models()

tab1, tab2, tab3, tab4 = st.tabs(
    ["Generate story", "Marketing campaign", "Image Playground", "Video Playground"]
)

with tab1:
    st.write("Using Gemini 1.0 Pro - Text only model")
    st.subheader("Generate a story")

    # Story premise
    character_name = st.text_input(
        "Enter character name: \n\n", key="character_name", value="Mittens"
    )
    character_type = st.text_input(
        "What type of character is it? \n\n", key="character_type", value="Cat"
    )
    character_persona = st.text_input(
        "What personality does the character have? \n\n",
        key="character_persona",
        value="Mitten is a very friendly cat.",
    )
    character_location = st.text_input(
        "Where does the character live? \n\n",
        key="character_location",
        value="Andromeda Galaxy",
    )
    story_premise = st.multiselect(
        "What is the story premise? (can select multiple) \n\n",
        [
            "Love",
            "Adventure",
            "Mystery",
            "Horror",
            "Comedy",
            "Sci-Fi",
            "Fantasy",
            "Thriller",
        ],
        key="story_premise",
        default=["Love", "Adventure"],
    )
    creative_control = st.radio(
        "Select the creativity level: \n\n",
        ["Low", "High"],
        key="creative_control",
        horizontal=True,
    )
    length_of_story = st.radio(
        "Select the length of the story: \n\n",
        ["Short", "Long"],
        key="length_of_story",
        horizontal=True,
    )

    if creative_control == "Low":
        temperature = 0.30
    else:
        temperature = 0.95

    max_output_tokens = 2048

    prompt = f"""Write a {length_of_story} story based on the following premise: \n
    character_name: {character_name} \n
    character_type: {character_type} \n
    character_persona: {character_persona} \n
    character_location: {character_location} \n
    story_premise: {",".join(story_premise)} \n
    If the story is "short", then make sure to have 5 chapters or else if it is "long" then 10 chapters.
    Important point is that each chapters should be generated based on the premise given above.
    First start by giving the book introduction, chapter introductions and then each chapter. It should also have a proper ending.
    The book should have prologue and epilogue.
    """
    config = {
        "temperature": 0.8,
        "max_output_tokens": 2048,
    }

    generate_t2t = st.button("Generate my story", key="generate_t2t")
    if generate_t2t and prompt:
        # st.write(prompt)
        with st.spinner("Generating your story using Gemini 1.0 Pro ..."):
            first_tab1, first_tab2 = st.tabs(["Story", "Prompt"])
            with first_tab1:
                response = get_gemini_pro_text_response(
                    text_model_pro,
                    prompt,
                    generation_config=config,
                )
                if response:
                    st.write("Your story:")
                    st.write(response)
            with first_tab2:
                st.text(prompt)

with tab2:
    st.write("Using Gemini 1.0 Pro - Text only model")
    st.subheader("Generate your marketing campaign")

    product_name = st.text_input(
        "What is the name of the product? \n\n", key="product_name", value="ZomZoo"
    )
    product_category = st.radio(
        "Select your product category: \n\n",
        ["Clothing", "Electronics", "Food", "Health & Beauty", "Home & Garden"],
        key="product_category",
        horizontal=True,
    )
    st.write("Select your target audience: ")
    target_audience_age = st.radio(
        "Target age: \n\n",
        ["18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
        key="target_audience_age",
        horizontal=True,
    )
    # target_audience_gender = st.radio("Target gender: \n\n",["male","female","trans","non-binary","others"],key="target_audience_gender",horizontal=True)
    target_audience_location = st.radio(
        "Target location: \n\n",
        ["Urban", "Suburban", "Rural"],
        key="target_audience_location",
        horizontal=True,
    )
    st.write("Select your marketing campaign goal: ")
    campaign_goal = st.multiselect(
        "Select your marketing campaign goal: \n\n",
        [
            "Increase brand awareness",
            "Generate leads",
            "Drive sales",
            "Improve brand sentiment",
        ],
        key="campaign_goal",
        default=["Increase brand awareness", "Generate leads"],
    )
    if campaign_goal is None:
        campaign_goal = ["Increase brand awareness", "Generate leads"]
    brand_voice = st.radio(
        "Select your brand voice: \n\n",
        ["Formal", "Informal", "Serious", "Humorous"],
        key="brand_voice",
        horizontal=True,
    )
    estimated_budget = st.radio(
        "Select your estimated budget ($): \n\n",
        ["1,000-5,000", "5,000-10,000", "10,000-20,000", "20,000+"],
        key="estimated_budget",
        horizontal=True,
    )

    prompt = f"""Generate a marketing campaign for {product_name}, a {product_category} designed for the age group: {target_audience_age}.
    The target location is this: {target_audience_location}.
    Aim to primarily achieve {campaign_goal}.
    Emphasize the product's unique selling proposition while using a {brand_voice} tone of voice.
    Allocate the total budget of {estimated_budget}.
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
    config = {
        "temperature": 0.8,
        "max_output_tokens": 2048,
    }
    generate_t2t = st.button("Generate my campaign", key="generate_campaign")
    if generate_t2t and prompt:
        second_tab1, second_tab2 = st.tabs(["Campaign", "Prompt"])
        with st.spinner("Generating your marketing campaign using Gemini 1.0 Pro ..."):
            with second_tab1:
                response = get_gemini_pro_text_response(
                    text_model_pro,
                    prompt,
                    generation_config=config,
                )
                if response:
                    st.write("Your marketing campaign:")
                    st.write(response)
            with second_tab2:
                st.text(prompt)

with tab3:
    st.write("Using Gemini 1.0 Pro Vision - Multimodal model")
    image_undst, screens_undst, diagrams_undst, recommendations, sim_diff = st.tabs(
        [
            "Furniture recommendation",
            "Oven instructions",
            "ER diagrams",
            "Glasses recommendation",
            "Math reasoning",
        ]
    )

    with image_undst:
        st.markdown(
            """In this demo, you will be presented with a scene (e.g., a living room) and will use the Gemini 1.0 Pro Vision model to perform visual understanding. You will see how Gemini 1.0 can be used to recommend an item (e.g., a chair) from a list of furniture options as input. You can use Gemini 1.0 Pro Vision to recommend a chair that would complement the given scene and will be provided with its rationale for such selections from the provided list.
                    """
        )

        room_image_uri = (
            "gs://github-repo/img/gemini/retail-recommendations/rooms/living_room.jpeg"
        )
        chair_1_image_uri = (
            "gs://github-repo/img/gemini/retail-recommendations/furnitures/chair1.jpeg"
        )
        chair_2_image_uri = (
            "gs://github-repo/img/gemini/retail-recommendations/furnitures/chair2.jpeg"
        )
        chair_3_image_uri = (
            "gs://github-repo/img/gemini/retail-recommendations/furnitures/chair3.jpeg"
        )
        chair_4_image_uri = (
            "gs://github-repo/img/gemini/retail-recommendations/furnitures/chair4.jpeg"
        )

        room_image_urls = (
            "https://storage.googleapis.com/" + room_image_uri.split("gs://")[1]
        )
        chair_1_image_urls = (
            "https://storage.googleapis.com/" + chair_1_image_uri.split("gs://")[1]
        )
        chair_2_image_urls = (
            "https://storage.googleapis.com/" + chair_2_image_uri.split("gs://")[1]
        )
        chair_3_image_urls = (
            "https://storage.googleapis.com/" + chair_3_image_uri.split("gs://")[1]
        )
        chair_4_image_urls = (
            "https://storage.googleapis.com/" + chair_4_image_uri.split("gs://")[1]
        )

        room_image = Part.from_uri(room_image_uri, mime_type="image/jpeg")
        chair_1_image = Part.from_uri(chair_1_image_uri, mime_type="image/jpeg")
        chair_2_image = Part.from_uri(chair_2_image_uri, mime_type="image/jpeg")
        chair_3_image = Part.from_uri(chair_3_image_uri, mime_type="image/jpeg")
        chair_4_image = Part.from_uri(chair_4_image_uri, mime_type="image/jpeg")

        st.image(room_image_urls, width=350, caption="Image of a living room")
        st.image(
            [
                chair_1_image_urls,
                chair_2_image_urls,
                chair_3_image_urls,
                chair_4_image_urls,
            ],
            width=200,
            caption=["Chair 1", "Chair 2", "Chair 3", "Chair 4"],
        )

        st.write(
            "Our expectation: Recommend a chair that would complement the given image of a living room."
        )
        content = [
            "Consider the following chairs:",
            "chair 1:",
            chair_1_image,
            "chair 2:",
            chair_2_image,
            "chair 3:",
            chair_3_image,
            "and",
            "chair 4:",
            chair_4_image,
            "\n"
            "For each chair, explain why it would be suitable or not suitable for the following room:",
            room_image,
            "Only recommend for the room provided and not other rooms. Provide your recommendation in a table format with chair name and reason as columns.",
        ]

        tab1, tab2 = st.tabs(["Response", "Prompt"])
        generate_image_description = st.button(
            "Generate recommendation....", key="generate_image_description"
        )
        with tab1:
            if generate_image_description and content:
                with st.spinner(
                    "Generating recommendation using Gemini 1.0 Pro Vision ..."
                ):
                    response = get_gemini_pro_vision_response(
                        multimodal_model_pro, content
                    )
                    st.markdown(response)
        with tab2:
            st.write("Prompt used:")
            st.text(content)

    with screens_undst:
        stove_screen_uri = (
            "gs://github-repo/img/gemini/multimodality_usecases_overview/stove.jpg"
        )
        stove_screen_url = (
            "https://storage.googleapis.com/" + stove_screen_uri.split("gs://")[1]
        )

        st.write(
            "Equipped with the ability to extract information from visual elements on screens, Gemini 1.0 Pro Vision can analyze screenshots, icons, and layouts to provide a holistic understanding of the depicted scene."
        )
        # cooking_what = st.radio("What are you cooking?",["Turkey","Pizza","Cake","Bread"],key="cooking_what",horizontal=True)
        stove_screen_img = Part.from_uri(stove_screen_uri, mime_type="image/jpeg")
        st.image(stove_screen_url, width=350, caption="Image of a oven")
        st.write(
            "Our expectation: Provide instructions for resetting the clock on this appliance in English"
        )
        prompt = """How can I reset the clock on this appliance? Provide the instructions in English.
If instructions include buttons, also explain where those buttons are physically located.
"""
        tab1, tab2 = st.tabs(["Response", "Prompt"])
        generate_instructions_description = st.button(
            "Generate instructions", key="generate_instructions_description"
        )
        with tab1:
            if generate_instructions_description and prompt:
                with st.spinner(
                    "Generating instructions using Gemini 1.0 Pro Vision..."
                ):
                    response = get_gemini_pro_vision_response(
                        multimodal_model_pro, [stove_screen_img, prompt]
                    )
                    st.markdown(response)
        with tab2:
            st.write("Prompt used:")
            st.text(prompt + "\n" + "input_image")

    with diagrams_undst:
        er_diag_uri = (
            "gs://github-repo/img/gemini/multimodality_usecases_overview/er.png"
        )
        er_diag_url = "https://storage.googleapis.com/" + er_diag_uri.split("gs://")[1]

        st.write(
            "Gemini 1.0 Pro Vision multimodal capabilities empower it to comprehend diagrams and take actionable steps, such as optimization or code generation. The following example demonstrates how Gemini 1.0 can decipher an Entity Relationship (ER) diagram."
        )
        er_diag_img = Part.from_uri(er_diag_uri, mime_type="image/jpeg")
        st.image(er_diag_url, width=350, caption="Image of a ER diagram")
        st.write(
            "Our expectation: Document the entities and relationships in this ER diagram."
        )
        prompt = """Document the entities and relationships in this ER diagram.
                """
        tab1, tab2 = st.tabs(["Response", "Prompt"])
        er_diag_img_description = st.button("Generate!", key="er_diag_img_description")
        with tab1:
            if er_diag_img_description and prompt:
                with st.spinner("Generating..."):
                    response = get_gemini_pro_vision_response(
                        multimodal_model_pro, [er_diag_img, prompt]
                    )
                    st.markdown(response)
        with tab2:
            st.write("Prompt used:")
            st.text(prompt + "\n" + "input_image")

    with recommendations:
        compare_img_1_uri = (
            "gs://github-repo/img/gemini/multimodality_usecases_overview/glasses1.jpg"
        )
        compare_img_2_uri = (
            "gs://github-repo/img/gemini/multimodality_usecases_overview/glasses2.jpg"
        )

        compare_img_1_url = (
            "https://storage.googleapis.com/" + compare_img_1_uri.split("gs://")[1]
        )
        compare_img_2_url = (
            "https://storage.googleapis.com/" + compare_img_2_uri.split("gs://")[1]
        )

        st.write(
            """Gemini 1.0 Pro Vision is capable of image comparison and providing recommendations. This may be useful in industries like e-commerce and retail.
                    Below is an example of choosing which pair of glasses would be better suited to various face types:"""
        )
        compare_img_1_img = Part.from_uri(compare_img_1_uri, mime_type="image/jpeg")
        compare_img_2_img = Part.from_uri(compare_img_2_uri, mime_type="image/jpeg")
        face_type = st.radio(
            "What is your face shape?",
            ["Oval", "Round", "Square", "Heart", "Diamond"],
            key="face_type",
            horizontal=True,
        )
        output_type = st.radio(
            "Select the output type",
            ["text", "table", "json"],
            key="output_type",
            horizontal=True,
        )
        st.image(
            [compare_img_1_url, compare_img_2_url],
            width=350,
            caption=["Glasses type 1", "Glasses type 2"],
        )
        st.write(
            f"Our expectation: Suggest which glasses type is better for the {face_type} face shape"
        )
        content = [
            f"""Which of these glasses you recommend for me based on the shape of my face:{face_type}?
           I have an {face_type} shape face.
           Glasses 1: """,
            compare_img_1_img,
            """
           Glasses 2: """,
            compare_img_2_img,
            f"""
           Explain how you reach out to this decision.
           Provide your recommendation based on my face shape, and reasoning for each in {output_type} format.
           """,
        ]
        tab1, tab2 = st.tabs(["Response", "Prompt"])
        compare_img_description = st.button(
            "Generate recommendation!", key="compare_img_description"
        )
        with tab1:
            if compare_img_description and content:
                with st.spinner(
                    "Generating recommendations using Gemini 1.0 Pro Vision..."
                ):
                    response = get_gemini_pro_vision_response(
                        multimodal_model_pro, content
                    )
                    st.markdown(response)
        with tab2:
            st.write("Prompt used:")
            st.text(content)

    with sim_diff:
        math_image_uri = "gs://github-repo/img/gemini/multimodality_usecases_overview/math_beauty.jpg"
        math_image_url = (
            "https://storage.googleapis.com/" + math_image_uri.split("gs://")[1]
        )
        st.write(
            "Gemini 1.0 Pro Vision can also recognize math formulas and equations and extract specific information from them. This capability is particularly useful for generating explanations for math problems, as shown below."
        )
        math_image_img = Part.from_uri(math_image_uri, mime_type="image/jpeg")
        st.image(math_image_url, width=350, caption="Image of a math equation")
        st.markdown(
            """
                Our expectation: Ask questions about the math equation as follows:
                - Extract the formula.
                - What is the symbol right before Pi? What does it mean?
                - Is this a famous formula? Does it have a name?
                    """
        )
        prompt = """
Follow the instructions.
Surround math expressions with $.
Use a table with a row for each instruction and its result.

INSTRUCTIONS:
- Extract the formula.
- What is the symbol right before Pi? What does it mean?
- Is this a famous formula? Does it have a name?
"""
        tab1, tab2 = st.tabs(["Response", "Prompt"])
        math_image_description = st.button(
            "Generate answers!", key="math_image_description"
        )
        with tab1:
            if math_image_description and prompt:
                with st.spinner(
                    "Generating answers for formula using Gemini 1.0 Pro Vision..."
                ):
                    response = get_gemini_pro_vision_response(
                        multimodal_model_pro, [math_image_img, prompt]
                    )
                    st.markdown(response)
                    st.markdown("\n\n\n")
        with tab2:
            st.write("Prompt used:")
            st.text(prompt)

with tab4:
    st.write("Using Gemini 1.0 Pro Vision - Multimodal model")

    vide_desc, video_tags, video_highlights, video_geolocation = st.tabs(
        ["Video description", "Video tags", "Video highlights", "Video geolocation"]
    )

    with vide_desc:
        st.markdown(
            """Gemini 1.0 Pro Vision can also provide the description of what is going on in the video:"""
        )
        vide_desc_uri = "gs://github-repo/img/gemini/multimodality_usecases_overview/mediterraneansea.mp4"
        video_desc_url = (
            "https://storage.googleapis.com/" + vide_desc_uri.split("gs://")[1]
        )
        if vide_desc_uri:
            vide_desc_img = Part.from_uri(vide_desc_uri, mime_type="video/mp4")
            st.video(video_desc_url)
            st.write("Our expectation: Generate the description of the video")
            prompt = """Describe what is happening in the video and answer the following questions: \n
            - What am I looking at? \n
            - Where should I go to see it? \n
            - What are other top 5 places in the world that look like this?
            """
            tab1, tab2 = st.tabs(["Response", "Prompt"])
            vide_desc_description = st.button(
                "Generate video description", key="vide_desc_description"
            )
            with tab1:
                if vide_desc_description and prompt:
                    with st.spinner(
                        "Generating video description using Gemini 1.0 Pro Vision ..."
                    ):
                        response = get_gemini_pro_vision_response(
                            multimodal_model_pro, [prompt, vide_desc_img]
                        )
                        st.markdown(response)
                        st.markdown("\n\n\n")
            with tab2:
                st.write("Prompt used:")
                st.write(prompt, "\n", "{video_data}")

    with video_tags:
        st.markdown(
            """Gemini 1.0 Pro Vision can also extract tags throughout a video, as shown below:."""
        )
        video_tags_uri = "gs://github-repo/img/gemini/multimodality_usecases_overview/photography.mp4"
        video_tags_url = (
            "https://storage.googleapis.com/" + video_tags_uri.split("gs://")[1]
        )
        if video_tags_url:
            video_tags_img = Part.from_uri(video_tags_uri, mime_type="video/mp4")
            st.video(video_tags_url)
            st.write("Our expectation: Generate the tags for the video")
            prompt = """Answer the following questions using the video only:
                        1. What is in the video?
                        2. What objects are in the video?
                        3. What is the action in the video?
                        4. Provide 5 best tags for this video?
                        Give the answer in the table format with question and answer as columns.
            """
            tab1, tab2 = st.tabs(["Response", "Prompt"])
            video_tags_description = st.button(
                "Generate video tags", key="video_tags_description"
            )
            with tab1:
                if video_tags_description and prompt:
                    with st.spinner(
                        "Generating video description using Gemini 1.0 Pro Vision ..."
                    ):
                        response = get_gemini_pro_vision_response(
                            multimodal_model_pro, [prompt, video_tags_img]
                        )
                        st.markdown(response)
                        st.markdown("\n\n\n")
            with tab2:
                st.write("Prompt used:")
                st.write(prompt, "\n", "{video_data}")
    with video_highlights:
        st.markdown(
            """Below is another example of using Gemini 1.0 Pro Vision to ask questions about objects, people or the context, as shown in the video about Pixel 8 below:"""
        )
        video_highlights_uri = (
            "gs://github-repo/img/gemini/multimodality_usecases_overview/pixel8.mp4"
        )
        video_highlights_url = (
            "https://storage.googleapis.com/" + video_highlights_uri.split("gs://")[1]
        )
        if video_highlights_url:
            video_highlights_img = Part.from_uri(
                video_highlights_uri, mime_type="video/mp4"
            )
            st.video(video_highlights_url)
            st.write("Our expectation: Generate the highlights for the video")
            prompt = """Answer the following questions using the video only:
What is the profession of the girl in this video?
Which all features of the phone are highlighted here?
Summarize the video in one paragraph.
Provide the answer in table format.
            """
            tab1, tab2 = st.tabs(["Response", "Prompt"])
            video_highlights_description = st.button(
                "Generate video highlights", key="video_highlights_description"
            )
            with tab1:
                if video_highlights_description and prompt:
                    with st.spinner(
                        "Generating video highlights using Gemini 1.0 Pro Vision ..."
                    ):
                        response = get_gemini_pro_vision_response(
                            multimodal_model_pro, [prompt, video_highlights_img]
                        )
                        st.markdown(response)
                        st.markdown("\n\n\n")
            with tab2:
                st.write("Prompt used:")
                st.write(prompt, "\n", "{video_data}")

    with video_geolocation:
        st.markdown(
            """Even in short, detail-packed videos, Gemini 1.0 Pro Vision can identify the locations."""
        )
        video_geolocation_uri = (
            "gs://github-repo/img/gemini/multimodality_usecases_overview/bus.mp4"
        )
        video_geolocation_url = (
            "https://storage.googleapis.com/" + video_geolocation_uri.split("gs://")[1]
        )
        if video_geolocation_url:
            video_geolocation_img = Part.from_uri(
                video_geolocation_uri, mime_type="video/mp4"
            )
            st.video(video_geolocation_url)
            st.markdown(
                """Our expectation: \n
            Answer the following questions from the video:
                - What is this video about?
                - How do you know which city it is?
                - What street is this?
                - What is the nearest intersection?
            """
            )
            prompt = """Answer the following questions using the video only:
            What is this video about?
            How do you know which city it is?
            What street is this?
            What is the nearest intersection?
            Answer the following questions in a table format with question and answer as columns.
            """
            tab1, tab2 = st.tabs(["Response", "Prompt"])
            video_geolocation_description = st.button(
                "Generate", key="video_geolocation_description"
            )
            with tab1:
                if video_geolocation_description and prompt:
                    with st.spinner(
                        "Generating location tags using Gemini 1.0 Pro Vision ..."
                    ):
                        response = get_gemini_pro_vision_response(
                            multimodal_model_pro, [prompt, video_geolocation_img]
                        )
                        st.markdown(response)
                        st.markdown("\n\n\n")
            with tab2:
                st.write("Prompt used:")
                st.write(prompt, "\n", "{video_data}")
