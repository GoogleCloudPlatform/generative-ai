# Gen App Builder Data Store Status Checker
_Using Google Cloud Discovery Engine APIs for Enterprise Search and Conversational AI_

---

## What is a Data Store?
A [Data Store](https://cloud.google.com/generative-ai-app-builder/docs/create-datastore-ingest) in Gen AI App Builder is a collection of websites or documents, both structured and unstructured, that can be indexed for search and retrieval actions.

Data Stores are the fundamental building block behind [Enterprise Search](https://cloud.google.com/enterprise-search) and [Generative AI Agents](https://cloud.google.com/generative-ai-app-builder/docs/agent-usage).

## Data Store Indexing Time
With each website or set of documents added, the Data Store needs to index the site and/or docuemnts in order for them to be searchable. This can take up to 4 hours for new data store web content to be indexed.

Using the attached example notebook, you can query your Data Store ID to see if indexing is complete.
Once complete, you can additionaly use the notebook to search your Data Store for specific pages or documents.
