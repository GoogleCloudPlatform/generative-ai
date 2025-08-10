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

from src.repository.big_query import BigQueryRepository, CHATS_TABLE
from src.model.chats import Chat
import datetime

class ChatsService:

    def __init__(self):
        self.repository = BigQueryRepository()

    def insert_chat(self, chat: Chat):
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
