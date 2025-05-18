from src.repository.big_query import BigQueryRepository, CHATS_TABLE, CHATS_ID_COLUMN
from src.model.chats import Chat

class ChatsService:

    def __init__(self):
        self.repository = BigQueryRepository()

    def insert_chat(self, chat: Chat):
        values = chat.to_insert_string()
        self.repository.insert_row(CHATS_TABLE, values)