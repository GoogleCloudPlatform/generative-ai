from typing import List
from google.cloud.discoveryengine_v1 import (
    EngineServiceClient,
    ListEnginesRequest,
)
from google.api_core.client_options import ClientOptions

from src.model.search import PROJECT_ID, Engine

LOCATIONS = [
    "global",
    "us",
]


class EngineService:

    def get_all(self) -> List[Engine]:
        engines = []
        for location in LOCATIONS:
            client_options = (
                ClientOptions(
                    api_endpoint=f"{location}-discoveryengine.googleapis.com"
                )
                if location != "global"
                else None
            )

            # Create a client
            client = EngineServiceClient(client_options=client_options)
            list_engines = client.list_engines(
                ListEnginesRequest(
                    parent=f"projects/{PROJECT_ID}/locations/{location}/collections/default_collection"
                )
            )
            for engine in list_engines.engines:
                engines.append(
                    Engine(
                        name=engine.display_name,
                        engine_id=engine.name.split("/")[-1],
                        region=location,
                    )
                )
        return engines
