import os
import threading
import time
from typing import Dict, List

from config import WEAVE_PROJECT_NAME
from dotenv import load_dotenv
import openai
from smolagents import ChatMessage, Model
import weave


class VertexAIServerModel(Model):
    """This model connects to a Vertex AI-compatible API server."""

    def __init__(
        self,
        model_id: str = None,
        project_id: str = None,
        location: str = None,
        endpoint_id: str = None,
        use_deepseek: bool = False,
        **kwargs,
    ):
        # Initialize parent class with any additional keyword arguments
        super().__init__(**kwargs)

        # Use provided values or fall back to environment variables
        self.model_id = model_id or os.getenv("VERTEX_MODEL_ID")
        self.project_id = project_id or os.getenv("VERTEX_PROJECT_ID")
        self.location = location or os.getenv("VERTEX_LOCATION", "us-central1")

        # Use DeepSeek endpoint if specified, otherwise use default Vertex endpoint
        if use_deepseek:
            self.endpoint_id = endpoint_id or os.getenv("DEEPSEEK_ENDPOINT_ID")
        else:
            self.endpoint_id = endpoint_id or os.getenv("VERTEX_ENDPOINT_ID")

        self.kwargs = kwargs

        # Set up authentication and token refresh
        self._setup_auth()
        self._start_refresh_loop()
        self._setup_client()

    def predict(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> openai.types.chat.ChatCompletion:
        # Combine instance kwargs with call-specific kwargs
        completion_kwargs = {**self.kwargs, **kwargs}

        # Remove stop_sequences if present (not supported by OpenAI client)
        if "stop_sequences" in completion_kwargs:
            stop_sequences = completion_kwargs.pop("stop_sequences")
            # If stop_sequences is present but stop is not, convert it to stop
            if "stop" not in completion_kwargs and stop_sequences:
                completion_kwargs["stop"] = stop_sequences

        # Process messages using smolagents' role conversion mechanism
        from smolagents.models import get_clean_message_list, tool_role_conversions

        # Get clean message list with proper role conversions
        processed_messages = get_clean_message_list(
            messages,
            role_conversions=tool_role_conversions,
            convert_images_to_image_urls=True,
        )

        try:
            # Use OpenAI client to make the API call to Vertex AI with processed messages
            response = self.client.chat.completions.create(
                model=self.model_id, messages=processed_messages, **completion_kwargs
            )

            return response

        except Exception as e:
            # Handle any errors that occur during the API call
            print(f"Error calling Vertex AI: {e}")
            raise

    def __call__(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> ChatMessage:
        # Get the full response from predict
        response = self.predict(messages, **kwargs)

        # Convert the response to a ChatMessage
        return self._response_to_chat_message(response)

    def _response_to_chat_message(self, response) -> ChatMessage:
        """Convert an OpenAI API response to a ChatMessage object."""
        # Try to safely extract message data
        try:
            message_data = response.choices[0].message
            message_dict = message_data.model_dump(
                include={"role", "content", "tool_calls"}
            )
        except Exception:
            # Fallback: manually create a dict with available attributes
            message_data = response.choices[0].message
            message_dict = {
                "role": getattr(message_data, "role", "assistant"),
                "content": getattr(message_data, "content", ""),
            }
            if hasattr(message_data, "tool_calls"):
                message_dict["tool_calls"] = message_data.tool_calls

        # Convert to ChatMessage format
        return ChatMessage.from_dict(message_dict)

    def _setup_auth(self):
        """Setup Google Cloud authentication with required permissions"""
        try:
            from google.auth import default

            # Initialize credentials with required scopes
            self.credentials, _ = default(
                scopes=["https://www.googleapis.com/auth/cloud-platform"]
            )
            self._refresh_token()

        except ModuleNotFoundError:
            raise ModuleNotFoundError(
                "Please install 'google-auth and requests' to use VertexAIServerModel"
            ) from None

    def _setup_client(self):
        """Setup OpenAI client with current credentials"""
        self.client = openai.OpenAI(
            base_url=f"https://{self.location}-aiplatform.googleapis.com/v1beta1/projects/{self.project_id}/locations/{self.location}/endpoints/{self.endpoint_id}",
            api_key=self.credentials.token,
        )

    def _refresh_token(self):
        """Refresh the Google Cloud token"""
        try:
            import google.auth.transport.requests

            self.credentials.refresh(google.auth.transport.requests.Request())
            self._setup_client()  # Update client with new token
        except Exception as e:
            print(f"Token refresh failed: {e}")

    def _start_refresh_loop(self):
        """Start the token refresh loop"""

        def refresh_loop():
            while True:
                time.sleep(3600)  # Refresh token every hour
                self._refresh_token()

        self._refresh_thread = threading.Thread(target=refresh_loop, daemon=True)
        self._refresh_thread.start()


class WeaveVertexAIServerModel(weave.Model):
    """A model that connects to Vertex AI and is tracked by Weave."""

    # Define only the essential Weave-tracked attributes
    model_id: str
    project_id: str
    location: str
    endpoint_id: str

    # Private field to hold the actual model implementation
    _vertex_model: object = None

    def __init__(
        self,
        model_id: str = None,
        project_id: str = None,
        location: str = None,
        endpoint_id: str = None,
        use_deepseek: bool = False,
        **kwargs,
    ):
        # Initialize the weave.Model parent
        super().__init__(
            model_id=model_id or os.getenv("VERTEX_MODEL_ID"),
            project_id=project_id or os.getenv("VERTEX_PROJECT_ID"),
            location=location or os.getenv("VERTEX_LOCATION", "us-central1"),
            endpoint_id=(
                endpoint_id or os.getenv("DEEPSEEK_ENDPOINT_ID")
                if use_deepseek
                else endpoint_id or os.getenv("VERTEX_ENDPOINT_ID")
            ),
        )

        # Create the actual VertexAIServerModel instance
        self._vertex_model = VertexAIServerModel(
            model_id=self.model_id,
            project_id=self.project_id,
            location=self.location,
            endpoint_id=self.endpoint_id,
            use_deepseek=use_deepseek,
            **kwargs,
        )

    @weave.op()
    def predict(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> openai.types.chat.ChatCompletion:
        return self._vertex_model.predict(messages, **kwargs)

    def __call__(
        self,
        messages: List[Dict[str, str]],
        **kwargs,
    ) -> ChatMessage:
        # Use the Weave-tracked predict method
        response = self.predict(messages, **kwargs)

        # Use the shared response conversion method from the underlying model
        return self._vertex_model._response_to_chat_message(response)


def main():
    """Test function for VertexAIServerModel"""
    # Now load the environment variables
    load_dotenv()

    weave.init(WEAVE_PROJECT_NAME)

    # Test with Gemini model (default)
    print("Testing with Gemini model...")
    vertex_model = WeaveVertexAIServerModel(
        project_id=os.getenv("VERTEX_PROJECT_ID"),  # Explicitly set project_id
        location=os.getenv("VERTEX_LOCATION", "us-central1"),  # Explicitly set location
        endpoint_id=os.getenv("VERTEX_ENDPOINT_ID"),  # Explicitly set endpoint_id
        temperature=0.7,  # Optional: add any additional parameters
    )

    # Test messages
    messages = [
        {"role": "system", "content": "You are a helpful AI assistant."},
        {"role": "user", "content": "Tell me about Vertex AI in 2-3 sentences."},
    ]

    # Call the model
    try:
        response = vertex_model.predict(messages)
        print("Response received:")
        print(f"Role: {response.choices[0].message.role}")
        print(f"Content: {response.choices[0].message.content}")

    except Exception as e:
        print(f"Error during Gemini test: {e}")

    # Test with DeepSeek model
    print("\nTesting with DeepSeek model...")
    deepseek_model = WeaveVertexAIServerModel(
        use_deepseek=True,
        project_id=os.getenv("VERTEX_PROJECT_ID"),  # Explicitly set project_id
        location=os.getenv("VERTEX_LOCATION", "us-central1"),  # Explicitly set location
        model_id="deepseek-ai/DeepSeek-R1-Distill-Qwen-7B",
        temperature=0.7,
    )

    # Call the model
    try:
        response = deepseek_model.predict(messages)
        print("Response received:")
        print(f"Role: {response.choices[0].message.role}")
        print(f"Content: {response.choices[0].message.content}")

    except Exception as e:
        print(f"Error during DeepSeek test: {e}")


if __name__ == "__main__":
    main()
