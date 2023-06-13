import gradio as gr
from vertexai.preview.language_models import ChatModel, InputOutputTextPair, ChatSession


def create_session():
    chat_model = ChatModel.from_pretrained("chat-bison@001")
    parameters = {
        "temperature": 0.2,
        "max_output_tokens": 256,
        "top_k": 40,
        "top_p": 0.80,
        "context": "You are an astronomer, knowledgeable about the solar system.",
        "examples": [
            InputOutputTextPair(
                input_text="How many moons does Mars have?",
                output_text="The planet Mars has two moons, Phobos and Deimos.",
            ),
        ],
    }
    chat = ChatSession(model=chat_model, **parameters)
    return chat


def response(chat, message):
    response = chat.send_message(
        message=message, max_output_tokens=256, temperature=0.2, top_k=40, top_p=0.8
    )
    return response.text


with gr.Blocks() as demo:
    chatbot = gr.Chatbot(
        [
            (
                "Hello! I'm an astronomer chatbot.\nAsk me anything about the solar system!",
                None,
            )
        ],
        label="PaLM-based Chatbot powered by Google Cloud",
    ).style(height=400)
    msg = gr.Textbox(placeholder="Type your response here", label="Response")
    clear = gr.Button("Clear")
    chat_model = create_session()

    def respond(message, chat_history):
        texts = [message]
        bot_message = response(chat_model, message)
        chat_history.append((message, bot_message))
        return "", chat_history

    msg.submit(respond, [msg, chatbot], [msg, chatbot])
    clear.click(lambda: None, None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=8080)
