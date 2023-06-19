import json

from typing import List
from langchain.schema import Document

from google.cloud import discoveryengine_v1beta
from google.protobuf.json_format import MessageToDict


class EnterpriseSearchRetriever():
  """Retriever class to fetch documents or snippets from a search engine."""
  def __init__(self,
               project,
               search_engine,
               location='global',
               serving_config_id='default_config'):
    self.search_client = discoveryengine_v1beta.SearchServiceClient()
    self.serving_config: str = self.search_client.serving_config_path(
            project=project,
            location=location,
            data_store=search_engine,
            serving_config=serving_config_id,
            )

  def _search(self, query:str):
    """Helper function to run a search"""
    request = discoveryengine_v1beta.SearchRequest(serving_config=self.serving_config, query=query)
    return self.search_client.search(request)

  def get_relevant_documents(self, query: str) -> List[Document]:
    """Retrieve langchain Documents from a search response"""
    res = self._search(query)
    documents = []
    for result in res.results:
        data = MessageToDict(result.document._pb)
        metadata = data.copy()
        del metadata['derivedStructData']
        del metadata['structData']
        if data.get('derivedStructData') is None:
            content = json.dumps(data.get('structData', {}))
        else:
            content = json.dumps([d.get('snippet') for d in data.get('derivedStructData', {}).get('snippets', []) if d.get('snippet') is not None])
        documents.append(Document(page_content=content, metadata=metadata))
    return documents

  def get_relevant_snippets(self, query: str) -> List[str]:
    """Retrieve snippets from a search query"""
    res = self._search(query)
    snippets = []
    for result in res.results:
        data = MessageToDict(result.document._pb)
        if data.get('derivedStructData', {}) == {}:
            snippets.append(json.dumps(data.get('structData', {})))
        else:
            snippets.extend([d.get('snippet') for d in data.get('derivedStructData', {}).get('snippets', []) if d.get('snippet') is not None])
    return snippets

