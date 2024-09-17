# RAG Backend

## Indexing and Storage

`src/indexing/run_parse_embed_index.py` contains the master script for parsing documents from a cloud storage bucket using Document AI, creating LlamaIndex indices which manage relationships between chunks, source documents, and parent chunks and storing the resulting indices in Google Cloud native storage modalities (e.g. Vector Search, Firestore, Vertex AI Search). Before running this script, adjust the `common/config.yaml` file to your specs.

```yaml
# Project and environment settings
project_id: "<my-project>"
location: "us-central1"

# Data and storage settings
input_bucket_name: "ken-rag-datasets"
docstore_bucket_name: "ken-rag-datasets"
bucket_prefix: "raw_pdfs/" # Where raw data files to be indexed live
vector_data_prefix: "vector_data"
rag_eval_dataset: "ken-rag-datasets"

# Index settings
vector_index_name: "google_hierarchical"
index_endpoint_name: "google_hierarchical_endpoint"
indexing_method: "hierarchical" # "hierarchal" or "flat"
qa_index_name: "google_qa"
qa_endpoint_name: "google_qa_endpoint"
firestore_db_name: "rag-docstore"
firestore_namespace: "hierarchical_docs"

# Chunking and embedding settings
chunk_sizes: [4096, 2048, 1024, 512] # For indexing_method == "hierarchical"
chunk_size: 512
embeddings_model_name: "text-embedding-004"
approximate_neighbors_count: 100

# Document AI settings
docai_location: "us"
docai_processor_id: "f1713ecadbbf91ab"
document_ai_processor_display_name: "layout-parser"
create_docai_processor: false
```

### Indexing Methods

There are two primary indexing methods used: `hierarchical` and `flat`.

- `hierarchical` will create a hierarchy of chunks based on chunk sizes where chunks lower in the hierarchy are smaller progressing to larger chunks up the hierarchy. The relationships among chunks are managed through metadata associated with each chunk. The leaf chunks are embedded and stored in the vector index while all chunks are stored in a Firestore document store. This index is created to be compatible with the `auto_merging` retrieval technique.
- `flat` will chunk all documents to the specified chunk size and simply embed them in the vector store. It will then store all parsed documents in Firestore so they can be accessed by ID as well.

### Firestore

Firestore is used to store chunks and entire documents for retrieval via metadata or ID. This is useful as a companion to vector search, as vector search can only query documents by vector similarity by design. By adding a docstore, retrieval techniques can augment vector search by retrieving additional chunks that surround the current set of retrieved chunks or through some other algorithm (e.g. BM25).

### "Questions-Answered" Index

The parameters `qa_index_name` and `qa_endpoint_name` determine if an additional vector search index will be created based on LLM-generated questions which each document can answer. When these are set, each parsed document will be passed to Gemini who will generate a set of questions which that document can answer. The generated questions are then associated with the source_id of the parsed document, embedded and stored in a vector search index. At retrieval time, users can opt to query this vector index which will compare the user's query with the generated questions to obtain document IDs which could potentially answers the users question. Then, those documents are retrieved from Firestore and returned to the LLM for response generation.

## RAG

## FastAPI Backend

This FastAPI application provides an API for querying and evaluating a Retrieval-Augmented Generation (RAG) system. It includes endpoints for updating prompts, managing vector search indices, querying the RAG system, and performing batch evaluations.

- Query RAG system with customizable parameters
- Update and manage prompts
- List and update vector search indices and endpoints
- Perform batch evaluations using various metrics
- Integration with Google Cloud services (Vertex AI, Firestore, Secret Manager)

### Endpoints

1. `/`: Root endpoint
2. `/get_all_prompts`: Retrieve all prompts
3. `/update_prompt`: Update a specific prompt
4. `/list_vector_search_indices`: List available vector search indices
5. `/list_vector_search_endpoints`: List available vector search endpoints
6. `/list_firestore_databases`: List Firestore databases
7. `/list_firestore_collections`: List collections in a Firestore database
8. `/get_current_index_info`: Get information about the current index
9. `/update_index`: Update the current index
10. `/query_rag`: Query the RAG system in one-shot mode
11. `/eval_batch`: Perform batch evaluation of the RAG system

### Data Source and RAG Pipeline State Management

`rag.index_manager.IndexManager` is the main class which manages state for vector indices, docstores, query engines and chat engines
across the app's lifecycle (e.g. through UI manipulations). The `index_manager` (instantiated)
will be injected into all API routes that need to access its state or manipulate its state.

This includes:

- Switching out vector indices or docstores
- Changing retrieval parameters (e.g. temperature, llm model, etc.)

Users can set/get the index state through making API calls to:

```python
class IndexUpdate(BaseModel):
    base_index_name: str
    base_endpoint_name: str
    qa_index_name: Optional[str]
    qa_endpoint_name: Optional[str]
    firestore_db_name: Optional[str]
    firestore_namespace: Optional[str]

@app.get("/get_current_index_info")
async def get_current_index_info(index_manager=Depends(get_index_manager)):
    return index_manager.get_current_index_info()

@app.post("/update_index")
async def update_index(index_update: IndexUpdate, index_manager=Depends(get_index_manager)):
    try:
        index_manager.set_current_indices(index_update.base_index_name,
                                          index_update.base_endpoint_name,
                                          index_update.qa_index_name,
                                          index_update.qa_endpoint_name,
                                          index_update.firestore_db_name,
                                          index_update.firestore_namespace)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

### Prompt State Management

`rag.prompts.Prompts` is the main state management class for prompts throughout the app's lifecycle. It is injected into all API routes which
require manipulating prompts or accessing their state (e.g. `QueryEngines` or `ChatEngines` in `IndexManager`).

### Asynchronous Execution

`rag.async_extensions` contains classes which extend some of llamaindex's core primitives to be fully asynchronous. Some of llamaindex's classes
are not fully asynchronous (e.g. node postprocessing and query transformation) making operations like batch evaluation very slow.

### Retrieval Techniques

`rag.index_manager.IndexManager.get_query_engine()` contains the core logic for setting up the llamaindex `QueryEngine` for RAG over the current set of indices
in `rag.index_manager.IndexManager`. A `QueryEngine` is a stateless interface to the RAG pipeline useful for one-shot Q&A over the current set of indices.

There are three basic retrieval techniques: `baseline`, `auto_merging` and `parent` on top of which additional retrieval, query transformation, and re-ranking can be applied.
| RAG Hyper-paramater | Description |
| ------------------- | ----------- |
| `use_rerank` | make a call to an LLM to re-rank the retrieved nodes in order of relevance according to the `prompts.choice_select_prompt_tmpl` |
| `use_hyde` | embed a hallucinated response to the initial query _without retrieved context_ and retrieve chunks based on that hallucinated response |
| `use_refine` | refine the initial answer by calling an LLM to critique the response's correctness according to `prompts.refine_prompt_tmpl` |
| `qa_followup` | In addition to the retrieval done in the base retriever, retrieves document IDs based on "questions that document can answer" by performing vector similarity of the query against the "questions answered" vector store. It will then retrieve the full document content from the associated collection in Firestore. Logic for this retriever is contained in `rag.qa_followup_retriever` |
| `hybrid_retrieval` | In addition to the retrieval done in the base retriever, retrieves document IDs based on BM25 search algorithm |

```python
def get_query_engine(self,
                        prompts: Prompts,
                        llm_name: str = "gemini-1.5-flash",
                        temperature: float = 0.0,
                        similarity_top_k: int = 5,
                        retrieval_strategy: str = "auto_merging",
                        use_hyde: bool = True,
                        use_refine: bool = True,
                        use_node_rerank: bool = False,
                        qa_followup: bool = True,
                        hybrid_retrieval: bool = True):
        '''
        Creates a llamaindex QueryEngine for single-shot Q&A over data
        '''
        llm = self.get_vertex_llm(llm_name=llm_name,
                                  temperature=temperature,
                                  system_prompt=Prompts.system_prompt)
        Settings.llm = llm

        qa_prompt = PromptTemplate(prompts.qa_prompt_tmpl)
        refine_prompt = PromptTemplate(prompts.refine_prompt_tmpl)

        if use_refine:
            synth = get_response_synthesizer(text_qa_template=qa_prompt,
                                            refine_template=refine_prompt,
                                            response_mode="compact",
                                            use_async=True)
        else:
            synth = get_response_synthesizer(text_qa_template=qa_prompt,
                                            response_mode="compact",
                                            use_async=True)

        base_retriever = self.base_index.as_retriever(similarity_top_k=similarity_top_k)
        qa_vector_retriever = self.qa_index.as_retriever(similarity_top_k=similarity_top_k)
        query_engine = None  # Default initialization

        # Choose between retrieval strategies and configurations.
        if retrieval_strategy == "auto_merging":
            logger.info(self.base_index.storage_context.docstore)
            retriever = AutoMergingRetriever(base_retriever,
                                                self.base_index.storage_context,
                                                verbose=True)
        elif retrieval_strategy == "parent":
            retriever = ParentRetriever(base_retriever, docstore=self.base_index.docstore)
        elif retrieval_strategy == "baseline":
            retriever=base_retriever

        if qa_followup:
            qa_retriever = QARetriever(qa_vector_retriever=qa_vector_retriever,
                                    docstore=self.qa_index.docstore)
            retriever = QAFollowupRetriever(qa_retriever=qa_retriever,
                                            base_retriever=retriever)

        if hybrid_retrieval:
            bm25_retriever = BM25Retriever.from_defaults(
                docstore=self.base_index.docstore,
                similarity_top_k=similarity_top_k,
                # Optional: We can pass in the stemmer and set the language for stop words
                # This is important for removing stop words and stemming the query + text
                # The default is english for both
                stemmer=Stemmer.Stemmer("english"),
                language="english",
            )
            retriever = QueryFusionRetriever(
                [retriever, bm25_retriever],
                similarity_top_k=similarity_top_k,
                num_queries=1,  # set this to 1 to disable query generation
                mode="reciprocal_rerank",
                use_async=True,
                verbose=True,
                # query_gen_prompt="...",  # we could override the query generation prompt here
            )

        if use_node_rerank:
            reranker_llm = Vertex(model="gemini-1.5-flash",
                                max_tokens=8192,
                                temperature=temperature,
                                system_prompt=prompts.system_prompt)
            choice_select_prompt = PromptTemplate(prompts.choice_select_prompt_tmpl)
            llm_reranker = CustomLLMRerank(choice_batch_size=10, top_n=5, choice_select_prompt=choice_select_prompt, llm=reranker_llm)
        else:
            llm_reranker = None

        query_engine = AsyncRetrieverQueryEngine.from_args(retriever,
                                                            response_synthesizer=synth,
                                                            node_postprocessors=[llm_reranker] if llm_reranker else None)

        if use_hyde:
            hyde_prompt = PromptTemplate(prompts.hyde_prompt_tmpl)
            hyde = AsyncHyDEQueryTransform(include_original=True, hyde_prompt=hyde_prompt)
            query_engine = AsyncTransformQueryEngine(query_engine=query_engine, query_transform=hyde)

        self.query_engine = query_engine
        return query_engine
```

## Running Tests

`tests/` contains unit tests for the FastAPI backend. To run tests, simply run

```bash
pytest -s
```
