from pydantic import BaseModel, Field
from typing import List, Optional


class TableColumn(BaseModel):
    description: str
    name: str
    type: str
    mode: str
    policyTag: Optional[str] = None
    fields: Optional[List['TableColumn']] = None

class TableSchema(BaseModel):
    fields: List[TableColumn]

class BQTable(BaseModel):
    description: str = Field(
        # description="",
        # examples=[""],
    )
    overview: str
    tags: str
    schema: TableSchema

    def write_to_json(self, filename: str):
        with open(f"{filename}.json", 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=4))


