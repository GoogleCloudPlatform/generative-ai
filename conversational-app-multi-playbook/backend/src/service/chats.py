"""Service layer for managing chat interactions.

This module provides the ChatsService class, which handles the logic
for persisting chat records (questions and answers) to the database.
It interacts primarily with the BigQuery repository.
"""

from src.repository.big_query import (
    BigQueryRepository,
    CHATS_TABLE,
)
from src.model.chats import Chat


class ChatsService:
    """Handles business logic related to chat history.

    This service interacts with the BigQuery repository to save
    chat conversation records.

    Attributes:
        repository: An instance of BigQueryRepository for database operations.
    """

    def __init__(self):
        """Initializes the ChatsService with a BigQueryRepository."""
        self.repository = BigQueryRepository()

    def insert_chat(self, chat: Chat):
        """Inserts a single chat record into the database.

        Args:
            chat: The Chat object containing the conversation details to save.
        """
        values = chat.to_insert_string()
        self.repository.insert_row(CHATS_TABLE, values)
