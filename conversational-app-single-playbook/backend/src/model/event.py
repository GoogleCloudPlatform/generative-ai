"""Defines data models for events used within the application.

These models represent specific occurrences or messages, often used for
asynchronous processing via task queues or pub/sub systems.
"""

from pydantic import BaseModel


class IntentCreateEvent(BaseModel):
    """Represents the data required to trigger the processing of a new intent.

    This event is typically created after an intent configuration is saved
    and is used to initiate background tasks like creating vector search indexes
    or processing associated data.

    Attributes:
        intent_name: The unique name of the intent being processed.
        index_endpoint_resource: The full resource name of the Vertex AI
                                 Matching Engine Index Endpoint associated
                                 with this intent.
    """

    intent_name: str
    index_endpoint_resource: str

    def to_dict(self):
        """Serializes the event data into a dictionary format.

        Useful for converting the event object into a format suitable for
        JSON serialization, often needed for task queue payloads or API responses.

        Returns:
            A dictionary representation of the IntentCreateEvent instance.
        """
        return {
            "intent_name": self.intent_name,
            "index_endpoint_resource": self.index_endpoint_resource,
        }
