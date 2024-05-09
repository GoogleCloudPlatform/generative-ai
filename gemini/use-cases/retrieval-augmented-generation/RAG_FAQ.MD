RAG_FAQ.MD
Most questions apply to 
https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/use-cases/retrieval-augmented-generation/intro_multimodal_rag.ipynb

Q: Why do we need both variables: text_embedding_page (the embedding of the entire page) and text_embedding_chunk (the embedding of each text chunk)?
A: We use chunk for most cases in the downstream task in the notebook. This is again from a demonstration purposes that you can either take the whole page or divide them further into smaller chunk. A lot depends on 1) LLM token limit, 2) How would you want your data to be structured and searched. Like, Gemin 1.0 has 8k token limit, so we can very easily do a single page (and multiple as well), and same with Gemini 1.5, where you can probably send a whole document at go. One of the rationale for chunk is to make sure, we don't have too much noise while search for something specific. Hope that clarifies?

Q. The accompanying presentation (and https://github.com/GoogleCloudPlatform/generative-ai/blob/main/embeddings/intro-textemb-vectorsearch.ipynb talks about ANN method of finding closest embeddings match, but the code uses cosine similarity… Should we even mention ANN for this notebook?
A. Yes, In the notebook, we use simple "cosine similarity", but in real world at big scale, you would want something like managed ANN, as given in the presentation.

Q. The cell which calls get_gemini_response()  generates different responses if I run it several times, even with temperature=0 and same 'query' and 'context' variable. Is this expected? Can anything be done to make it generate the same response every time?
A. Yeah, that behavior is expected. Temp=0 doesn't solve it. I am not sure if there is any plan in the roadmap to address it. You can however make prompts do that magic by forcing structure like JSON

Q. Why did we split 14-page PDF into two 7-page PDFs? IS there any limitation that would have prevented us from processing the entire 14-page doc?
A. The pdf is split just to show that you can read multiple pdf’s with the logic. That’s the only reason.

Q. For text embeddings, we are splitting the docs into smaller "chunks". Are we doing the same for images? 
A.  No we are not chuncking images. We have two kinds of image embeddings - one uses ‘multimodal-embeddings’ where we send image directly and the API returns embeddings.
The second method is - we send an image to Gemini - get a description of it as text - and send that text to the ‘text-embeddings’ model and get embeddings back. In the latter case, we send the whole text as is. No chunking. 

Q: Is it a good practice to do a RAG on the LLM-generated summary of text chunks rather than the raw text? Context: for customer-service or “trouble-ticket” use-cases, the docs in the data corpus aren’t always grammatically correct or well-structured syntactically. Would document pre-processing/summarization prior to generating the embeddings lead to a higher accuracy of a RAG-based solution?
A. It depends. This may indeed be helpful to pre-process documents via an LLM before generating the embeddings. One would still want to insert the original documents as prompt context, however. 


