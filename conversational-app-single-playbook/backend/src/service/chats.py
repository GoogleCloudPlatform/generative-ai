# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Service layer for managing chat interactions.

This module provides the ChatsService class, which handles the logic
for persisting chat records (questions and answers) to the database.
It interacts primarily with the BigQuery repository.
"""

import datetime
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
        schema_fields = Chat.__schema__()
        column_names = [field.name for field in schema_fields]

        # Prepare values as a tuple, matching the order of schema_fields
        # If chat.timestamp is None, we'll insert the current UTC time.
        # BigQueryRepository will handle the Python datetime object.
        timestamp_value = chat.timestamp if chat.timestamp else datetime.datetime.now(datetime.timezone.utc)

        # Ensure the order here matches the order in Chat.__schema__
        values_tuple = (
            chat.id,
            chat.question,
            chat.answer,
            chat.intent,
            chat.suggested_questions,
            timestamp_value
        )

        self.repository.insert_row(CHATS_TABLE, column_names, values_tuple)
