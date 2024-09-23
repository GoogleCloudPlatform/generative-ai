import os

import requests
import streamlit as st

backend_url = os.environ.get("BACKEND_URL", "http://localhost:8080")


# helper function - send prompt to backend --> model
def get_chat_response(user_prompt: str, messages: []) -> str:
    # call Java backend
    request = {"prompt": user_prompt}
    response = requests.post(backend_url + "/chat", json=request)
    if response.status_code != 200:
        raise Exception(f"Bad response from backend: {response.text}")
    return response.json()["response"]


# --------- STREAMLIT APP ---------------------------------------
st.title("🚗 Fix my car! ")
st.text("Questions about your vehicle? Ask me! Include the make, model, and year.")

if "messages" not in st.session_state:
    st.session_state.messages = []

# show chat history in UI
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input(
    "Tell me the make + model of your car, then ask a question."
):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        # include previous messages as context
        for response in get_chat_response(prompt, st.session_state.messages[:-1]):
            full_response += response
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    st.session_state.messages.append({"role": "assistant", "content": full_response})
