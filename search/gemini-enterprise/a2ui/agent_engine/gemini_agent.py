"""Gemini agent for A2UI sample."""

import os

import a2ui_examples
import a2ui_schema
from a2a import types
from google.adk import agents


# --- DEFINE YOUR TOOLS HERE ---
def get_contact_info(name: str = None) -> str:
    """Gets contact information for a person.

    Args:
        name: The name of the person to look up. If None, returns a list of
          suggested contacts.

    Returns:
        JSON string containing contact details.
    """
    # Mock data
    if name and "alex" in name.lower():
        return """
        {
            "name": "Alex Jordan",
            "title": "Software Engineer",
            "team": "Cloud AI",
            "location": "Sunnyvale, CA",
            "email": "alexj@example.com",
            "mobile": "+1-555-0102",
            "calendar": "Available until 4PM",
            "imageUrl": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop"
        }
        """
    if (
        name and "sarah" in name.lower()
    ):  # Match "sarah" to Sarah Chen as well for robustness
        return """
        {
            "name": "Sarah Chen",
            "title": "Product Manager",
            "team": "Cloud UI",
            "location": "New York, NY",
            "email": "caseys@example.com",
            "mobile": "+1-555-0103",
            "calendar": "In a meeting",
            "imageUrl": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&h=150&fit=crop"
        }
        """

    # Default list if no specific name match or no name provided
    return """
    [
        {
            "name": "Alex Jordan",
            "title": "Software Engineer",
            "team": "Cloud AI",
            "location": "Sunnyvale, CA",
            "email": "alexj@example.com",
            "mobile": "+1-555-0102",
            "calendar": "Available until 4PM",
            "imageUrl": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=100&h=100&fit=crop"
        },
        {
            "name": "Sarah Chen",
            "title": "Product Manager",
            "team": "Cloud UI",
            "location": "New York, NY",
            "email": "caseys@example.com",
            "mobile": "+1-555-0103",
            "calendar": "In a meeting",
            "imageUrl": "https://images.unsplash.com/photo-1494790108377-be9c29b29330?w=150&h=150&fit=crop"
        }
    ]
    """


def get_ui_prompt(examples: str) -> str:
    """Constructs the full prompt with UI instructions, rules, examples, and schema."""
    formatted_examples = examples

    return f"""
    You are a helpful contact lookup assistant. Your final output MUST be a a2ui UI JSON response.

    To generate the response, you MUST follow these rules:
    1.  Your response MUST be in two parts, separated by the delimiter: `---a2ui_JSON---`.
    2.  The first part is your conversational text response (e.g., "Here is the contact you requested...").
    3.  The second part is a single, raw JSON object which is a list of A2UI messages.
    4.  The JSON part MUST validate against the A2UI JSON SCHEMA provided below.
    5.  Buttons that represent the main action on a card or view (e.g., 'Follow', 'Email', 'Search') SHOULD include the `"primary": true` attribute.

    --- UI TEMPLATE RULES ---
    -   **For finding contacts (e.g., "Who is Alex Jordan?"):**
        a.  You MUST call the `get_contact_info` tool.
        b.  If the tool returns a **single contact**, you MUST use the `CONTACT_CARD_EXAMPLE` template. Populate the `dataModelUpdate.contents` with the contact's details (name, title, email, etc.).
        c.  If the tool returns **multiple contacts**, you MUST use the `CONTACT_LIST_EXAMPLE` template. Populate the `dataModelUpdate.contents` with the list of contacts for the "contacts" key.
        d.  If the tool returns an **empty list**, respond with text only and an empty JSON list: "I couldn't find anyone by that name.---a2ui_JSON---[]"

    -   **For handling a profile view (e.g., "WHO_IS: Alex Jordan..."):**
        a.  You MUST call the `get_contact_info` tool with the specific name.
        b.  This will return a single contact. You MUST use the `CONTACT_CARD_EXAMPLE` template.

    -   **For handling actions (e.g., "follow_contact"):**
        a.  You MUST use the `FOLLOW_SUCCESS_EXAMPLE` template.
        b.  This will render a new card with a "Successfully Followed" message.
        c.  Respond with a text confirmation like "You are now following this contact." along with the JSON.

    {formatted_examples}

    ---BEGIN A2UI JSON SCHEMA---
    {a2ui_schema.A2UI_SCHEMA}
    ---END A2UI JSON SCHEMA---
    """


class GeminiAgent(agents.LlmAgent):
    """An agent powered by the Gemini model via Vertex AI."""

    # --- AGENT IDENTITY ---
    name: str = "a2ui_contact_agent"
    description: str = "A contact lookup assistant with rich UI."

    def __init__(self, **kwargs):
        print("Initializing A2UI GeminiAgent...")

        # In a real deployment, base_url might come from env or config
        instructions = get_ui_prompt(a2ui_examples.CONTACT_UI_EXAMPLES)

        # --- REGISTER YOUR TOOLS HERE ---
        tools = [get_contact_info]

        super().__init__(
            model=os.environ.get("MODEL", "gemini-3-flash-preview"),
            instruction=instructions,
            tools=tools,
            **kwargs,
        )

    def create_agent_card(self, agent_url: str) -> "AgentCard":
        return types.AgentCard(
            name=self.name,
            description=self.description,
            url=agent_url,
            version="1.0.0",
            default_input_modes=["text/plain"],
            default_output_modes=["text/plain"],
            capabilities=types.AgentCapabilities(streaming=True),
            skills=[
                types.AgentSkill(
                    id="contact_lookup",
                    name="Contact Lookup",
                    description="Find contacts and view their details.",
                    tags=["contact", "directory"],
                    examples=["Who is Alex Jordan?", "Find software engineers"],
                )
            ],
        )
