import streamlit as st
from PIL import Image
from src.utils import *
from src.vertex import *

st.set_page_config(
    page_title="Vertex PaLM Text Generation API",
    page_icon=":robot:",
    layout="centered",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://www.extremelycoolapp.com/help',
        'Report a bug': "https://www.extremelycoolapp.com/bug",
        'About': "# This app shows you how to use Vertex PaLM Text Generator API"
    }
)

#creating session states
create_session_state()



image = Image.open('./image/palm.jpg')
st.image(image)
st.title(":red[PaLM 2] :blue[Vertex AI] Text Generation")

with st.sidebar:
    image = Image.open('./image/sidebar_image.jpg')
    st.image(image)
    st.markdown("<h2 style='text-align: center; color: red;'>Setting Tab</h2>", unsafe_allow_html=True)


    st.write("Model Settings:")

    #define the temeperature for the model
    temperature_value = st.slider('Temperature :', 0.0, 1.0, 0.2)
    st.session_state['temperature'] = temperature_value

    #define the temeperature for the model
    token_limit_value = st.slider('Token limit :', 1, 1024, 256)
    st.session_state['token_limit'] = token_limit_value

    #define the temeperature for the model
    top_k_value = st.slider('Top-K  :', 1,40,40)
    st.session_state['top_k'] = top_k_value

    #define the temeperature for the model
    top_p_value = st.slider('Top-P :', 0.0, 1.0, 0.8)
    st.session_state['top_p'] = top_p_value

    if st.button("Reset Session"):
        reset_session()



with st.container():
    st.write("Current Generator Settings: ")
    # if st.session_state['temperature'] or st.session_state['debug_mode'] or :
    st.write ("Temperature: ",st.session_state['temperature']," \t \t Token limit: ",st.session_state['token_limit']
                ," \t \t Top-K: ",st.session_state['top_k']
                ," \t \t Top-P: ",st.session_state['top_p']
                ," \t \t Debug Model: ",st.session_state['debug_mode'])


    prompt = st.text_area("Add your prompt: ",height = 100)
    if prompt:
        st.session_state['prompt'].append(prompt)
        st.markdown("<h3 style='text-align: center; color: blue;'>Generator Model Response</h3>", unsafe_allow_html=True)
        with st.spinner('PaLM is working to generate, wait.....'):
            response = get_text_generation(prompt=prompt, temperature = st.session_state['temperature'],
                                max_output_tokens = st.session_state['token_limit'],
                                top_p = st.session_state['top_p'],
                                top_k = st.session_state['top_k'])
            st.session_state['response'].append(response)
            st.markdown(response)
