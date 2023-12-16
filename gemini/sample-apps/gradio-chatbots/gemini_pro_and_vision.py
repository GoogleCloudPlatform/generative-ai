"""gemini-pro-and-vision.ipynb
Colab notebook is located at
    https://colab.research.google.com/drive/1Ma5G_yCCs1MU3TPgdIm2SdwpketkVhhK
"""

import os

# import required packages
import google.generativeai as genai
import gradio as gr
import PIL.Image
from gradio.data_classes import FileData
from gradio_multimodalchatbot import MultimodalChatbot

# For better security practices, retrieve sensitive information
# like API keys from environment variables.
# Set an environment variable
os.environ["GOOGLE_API_KEY"] = "enter-your-google-gemini-API-key-here"

# Fetch an environment variable.
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize genai models
model = genai.GenerativeModel("gemini-pro")
modelvis = genai.GenerativeModel("gemini-pro-vision")


def gemini(input, file, chatbot=[]):
    """
    Function to handle gemini model and gemini vision model interactions.

    Parameters:
    input (str): The input text.
    file (File): An optional file object for image processing.
    chatbot (list): A list to keep track of chatbot interactions.

    Returns:
    tuple: Updated chatbot interaction list, an empty string, and None.
    """

    messages = []
    print(chatbot)

    # Process previous chatbot messages if present
    if len(chatbot) != 0:
        for user, bot in chatbot:
            user, bot = user.text, bot.text
            messages.extend(
                [{"role": "user",
                  "parts": [user]}, {"role": "model", "parts": [bot]}]
            )
        messages.append({"role": "user", "parts": [input]})
    else:
        messages.append({"role": "user", "parts": [input]})

    try:
        # Process image if file is provided
        if file is not None:
            with PIL.Image.open(file.name) as img:
                message = [{"role": "user", "parts": [input, img]}]
                response = modelvis.generate_content(message)
                gemini_video_resp = response.text
                messages.append({"role": "model",
                                 "parts": [gemini_video_resp]})

                # Construct list of messages in the required format
                user_msg = {
                    "text": input,
                    "files": [{"file": FileData(path=file.name)}],
                }
                bot_msg = {"text": gemini_video_resp, "files": []}
                chatbot.append([user_msg, bot_msg])
        else:
            response = model.generate_content(messages)
            gemini_resp = response.text

            # Construct list of messages in the required format
            user_msg = {"text": input, "files": []}
            bot_msg = {"text": gemini_resp, "files": []}
            chatbot.append([user_msg, bot_msg])
    except Exception as e:
        # Handling exceptions and raising error to the modal
        print(f"An error occurred: {e}")
        raise gr.Error(e)

    return chatbot, "", None


# Define the Gradio Blocks interface
with gr.Blocks() as demo:
    # Add a centered header using HTML
    gr.HTML("<center><h1>Gemini-PRO & Gemini-PRO-Vision API</h1></center>")

    # Initialize the MultimodalChatbot component
    multi = MultimodalChatbot(value=[], height=800)

    with gr.Row():
        # Textbox for user input with increased scale for better visibility
        tb = gr.Textbox(scale=4)

        # Upload button for image files
        up = gr.UploadButton("Upload Image", file_types=["image"], scale=1)

    # Define the behavior on text submission
    tb.submit(gemini, [tb, up, multi], [multi, tb, up])

    # Define the behavior on image upload
    # Using chained then() calls to update the upload button's state
    up.upload(lambda: gr.UploadButton("Uploading Image..."), [], up).then(
        lambda: gr.UploadButton("Image Uploaded"), [], up
    ).then(lambda: gr.UploadButton("Upload Image"), [], up)

# Launch the demo with a queue to handle multiple users
demo.queue().launch(debug=True, share=True)
