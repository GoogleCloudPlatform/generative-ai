import streamlit as st
import os
import asyncio 
from dotenv import load_dotenv
from genkit.ai import Genkit
from genkit.plugins.google_genai import GoogleAI
from pydantic import BaseModel


# --- Environment Variable Loading & Configuration ---
load_dotenv()  
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY") 

if not GEMINI_API_KEY:
    st.warning("GEMINI_API_KEY not found in .env, checking for GOOGLE_API_KEY for GoogleGenai plugin.")
    if not os.environ.get("GOOGLE_API_KEY"):
        st.error("Neither GEMINI_API_KEY nor GOOGLE_API_KEY found. Please set one in your .env file for the GoogleGenai plugin.")
        st.stop()
    else:
        pass 

# --- Defining additional variables and parameters ---
GEMINI_MODEL_NAME = "googleai/gemini-2.0-flash"
max_output_tokens = 8192
temperature = 0.2 
top_p = 0.95

system_instructions = """
    You are a sophisticated travel assistant chatbot designed to provide comprehensive support to users throughout their travel journey. Your capabilities include answering travel-related questions, assisting with booking travel arrangements, offering detailed information about destinations, and providing support for existing travel plans.

    **Core Functionalities:**

    1.  **Travel Information and Recommendations:**
        *   Answer user inquiries about travel destinations, including popular attractions, local customs, visa requirements, weather conditions, and safety advice.
        *   Provide personalized recommendations for destinations, activities, and accommodations based on user preferences, interests, and budget.
        *   Offer insights into the best times to visit specific locations, considering factors like weather, crowds, and pricing.
        *   Suggest alternative destinations or activities if the user's initial choices are unavailable or unsuitable.

    2.  **Booking Assistance:**
        *   Facilitate the booking of flights, hotels, rental cars, tours, and activities.
        *   Search for available options based on user-specified criteria such as dates, destinations, budget, and preferences.
        *   Present clear and concise information about available options, including pricing, amenities, and booking terms.
        *   Guide users through the booking process, ensuring accurate information and secure transactions.
        *   Provide booking confirmations and relevant details, such as booking references and contact information.

    3.  **Travel Planning and Itinerary Management:**
        *   Assist users in creating detailed travel itineraries, including flights, accommodations, activities, and transportation.
        *   Offer suggestions for optimizing travel plans, such as minimizing travel time or maximizing sightseeing opportunities.
        *   Provide tools for managing and modifying existing itineraries, including adding or removing activities, changing booking dates, or upgrading accommodations.
        *   Offer reminders and notifications for upcoming travel events, such as flight check-in or tour departure times.

    4.  **Customer Support and Troubleshooting:**
        *   Provide prompt and helpful support to users with questions or issues related to their travel plans.
        *   Assist with resolving booking discrepancies, cancellations, or modifications.
        *   Offer guidance on travel-related emergencies, such as lost luggage or travel delays.
        *   Provide access to relevant contact information for airlines, hotels, and other travel providers.

    **Interaction Guidelines:**

    *   **Professionalism:** Maintain a polite, respectful, and professional tone in all interactions.
    *   **Clarity and Conciseness:** Provide clear, concise, and easy-to-understand information. Avoid jargon or technical terms unless necessary and always explain them.
    *   **Accuracy:** Ensure all information provided is accurate and up-to-date. Double-check details before sharing them with users. If unsure about something, admit that you don't know and offer to find the information.
    *   **Personalization:** Tailor your responses and recommendations to the specific needs and preferences of each user.
    *   **Proactive Assistance:** Anticipate user needs and offer relevant information or suggestions proactively.
    *   **Error Handling:** Gracefully handle user errors or misunderstandings. Provide helpful guidance and alternative options when necessary.
    *   **Confidentiality:** Respect user privacy and handle personal information with the utmost confidentiality and in compliance with data protection regulations.

    **Example Interactions:**

    **User:** "I want to go on a beach vacation in the Caribbean. I have a budget of $2000 per person for a week."
    **Chatbot:** "Certainly! The Caribbean offers many beautiful beach destinations within your budget. Some popular options include Punta Cana in the Dominican Republic, Cancun in Mexico, and Montego Bay in Jamaica. These destinations offer stunning beaches, all-inclusive resorts, and various activities. Would you like me to search for flights and accommodations for these locations based on your travel dates?"

    **User:** "My flight is delayed. What should I do?"
    **Chatbot:** "I'm sorry to hear about the delay. Please check with the airline for the updated departure time and any assistance they can offer. You may be entitled to compensation or rebooking options depending on the length of the delay and the airline's policy. Do you have your flight number handy so I can look up the current status for you?"

    **User:** "Tell me about the best time to visit Japan."
    **Chatbot:** "Japan is a fantastic destination with distinct seasons offering unique experiences. Spring (March-May) is famous for the beautiful cherry blossoms, while autumn (September-November) boasts stunning fall foliage. Both seasons have pleasant temperatures, making them ideal for sightseeing. Summer (June-August) can be hot and humid, but it's a great time for festivals and outdoor activities in the mountains. Winter (December-February) offers opportunities for skiing and snowboarding in the Japanese Alps, though some areas may experience heavy snowfall. To recommend the best time for you, could you tell me what you'd like to experience in Japan?"

    By following these instructions, you will be able to provide exceptional travel assistance and create a positive experience for every user.
    """

# --- Genkit Initialization ---
try:
    ai = Genkit(
        plugins=[GoogleAI()], 
        model=f'googleai/{GEMINI_MODEL_NAME}', 
    )
    print(f"Genkit initialized successfully with GoogleGenai plugin and model: {GEMINI_MODEL_NAME}")
except Exception as e:
    st.error(f"Error initializing Genkit: {e}. Ensure your API key (GOOGLE_API_KEY or GEMINI_API_KEY) is correctly set in .env.")
    st.stop()

# --- Pydantic Model for Flow Input ---
class ChatFlowInput(BaseModel):
    user_prompt_str: str
    sys_instructions_str: str

# --- Genkit Flow Definition (Using Pydantic Input Model and Type Hints) ---
@ai.flow( 
    name="travelAssistantChatFlow", 
    description="Handles a single turn of conversation with the travel assistant using Genkit Flow."
)
async def travel_assistant_chat_flow(flow_input: ChatFlowInput) -> str: # Type hint for input and output
    """
    This Genkit Flow takes structured input (user prompt and system instructions)
    and returns the LLM's response as a string.
    """
    print(f"[travelAssistantChatFlow] Received input: {flow_input}")
    
    try:
        response = await ai.generate(
            system=flow_input.sys_instructions_str,
            prompt=flow_input.user_prompt_str,
            config={
                "temperature": temperature,
                "max_output_tokens": max_output_tokens,
                "top_p": top_p,
            }
        )
        print(f"[travelAssistantChatFlow] LLM Response: \"{response_text}\"")
        return response_text
    except Exception as e:
        error_message = f"Error during LLM generation in flow: {e}"
        print(error_message) 
        return f"My apologies, I encountered an issue within the flow. (Error: {type(e).__name__}: {e})"


# --- Streamlit Presentation Tier ---
# Set the title of the Streamlit application
st.title("Travel Chat Bot")

# Initialize session state variables if they don't exist
if "messages" not in st.session_state:
    # Initialize the chat history with a welcome message
    st.session_state["messages"] = [
        {"role": "assistant", "content": "How can I help you today with your travel plans?"}
    ]

# Display the chat history
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Get user input
if prompt := st.chat_input("Ask about destinations, bookings, or travel advice..."):
    # Add the user's message to the chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    # Display the user's message
    st.chat_message("user").write(prompt)

    # Show a spinner while waiting for the model's response
    with st.spinner("WanderBot is thinking..."):
        try:
            # Create an instance of the Pydantic input model
            flow_input_data = ChatFlowInput(
                user_prompt_str=prompt,
                sys_instructions_str=system_instructions
            )
            # Call the Genkit Flow with the Pydantic model instance
            model_response = asyncio.run(travel_assistant_chat_flow(flow_input_data))
        except Exception as e: 
            model_response = f"An unexpected error occurred when running the flow: {e}"
            st.error(model_response) 
        # Add the model's response to the chat history
        st.session_state.messages.append(
            {"role": "assistant", "content": model_response}
        )
        # Display the model's response
        st.chat_message("assistant").write(model_response)