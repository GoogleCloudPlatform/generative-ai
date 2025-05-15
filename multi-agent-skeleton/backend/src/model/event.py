from pydantic import BaseModel


class IntentCreateEvent(BaseModel):

    intent_name: str
    index_endpoint_resource: str

    def to_dict(self):
        return {
            "intent_name": self.intent_name,
            "index_endpoint_resource": self.index_endpoint_resource,
        }