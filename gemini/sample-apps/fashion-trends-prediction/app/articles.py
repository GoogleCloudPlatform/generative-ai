import json
import pickle

import vertexai
from config import config
from langchain.docstore.document import Document
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.vectorstores import VectorStore
from sentence_transformers import SentenceTransformer
from vertexai.language_models import ChatModel, InputOutputTextPair

PROJECT_ID = config["PROJECT_ID"]  # @param {type:"string"}
LOCATION = config["LOCATION"]  # @param {type:"string"}
mode = config["mode"]


class Articles:
    def __init__(self, data):
        """Initializes the Articles class.

        Args:
            data (dict): A dictionary of articles.
        """
        self.data = data
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

        if mode == 0:
            with open("data/chunks_local.json", "r") as f:
                chunks = json.load(f)
        else:
            with open("data/chunks_prod.json", "r") as f:
                chunks = json.load(f)

        chunks = [Document(**chunk) for chunk in chunks]
        bm25_retriever = BM25Retriever.from_documents(chunks)
        bm25_retriever.k = 3

        if mode == 0:
            with open("data/vectorstore_local.pkl", "rb") as f:
                global vectorstore
                local_vectorstore: VectorStore = pickle.load(f)
        else:
            with open("data/vectorstore_prod.pkl", "rb") as f:
                global vectorstore
                local_vectorstore: VectorStore = pickle.load(f)

        faiss_retriever = local_vectorstore.as_retriever(search_kwargs={"k": 3})

        # initialize the ensemble retriever
        p = 0.6
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever], weights=[p, 1 - p]
        )

        vertexai.init(project=PROJECT_ID, location=LOCATION)

        self.chat_model = ChatModel.from_pretrained("chat-bison")
        self.parameters = {
            "candidate_count": 1,
            "max_output_tokens": 1024,
            "temperature": 0.2,
            "top_p": 0.8,
            "top_k": 40,
        }
        self.chat = self.chat_model.start_chat(
            context="""You are a fashion journalist and want to know whether an article is talking about a given fashion clothing item. Answer this by searching for the presence of the item or a similar item in the text.""",
            examples=[
                InputOutputTextPair(
                    input_text="""Is the following article related to White tie dye dress - Tie-dye, known for its vibrant and carefree nature, has evolved through different eras, from the 60s hippie movement to the 90s stoner culture, and recently, the \"scumbro\" style. Alia Bhatt showcased a tie-dye lounge set, representing the hedonistic and relaxed spirit of the trend. While it may not dominate red carpets as before, tie-dye is making a comeback in subtle ways, such as Bhatt\'s outfit, symbolizing fun and carefree vibes.""",
                    output_text="""Yes, since the article contains the main component of the query item that is tie dye.""",
                ),
                InputOutputTextPair(
                    input_text="""Is the following article related to Off the shoulder knit brown dress - While some Bollywood celebrities are attending Diwali events, Shanaya Kapoor is vacationing in the Maldives. She showcased several stylish outfits during her trip, including a cobalt blue bikini top with a checkered skirt, a ruffled bralette and skirt set, a bustier with a chunky knit skirt, and a crochet dress. Kapoor\'s vacation style is reminiscent of the knitwear and crochet trend seen in recent years, popularized by celebrities like Kim Kardashian and Kylie Jenner.""",
                    output_text="""Yes, since the article mentions knitwear which is the main component of the query item.""",
                ),
                InputOutputTextPair(
                    input_text="""Is the following article related to white cotton jacket - It was a big weekend for Kylie Jenner and Timothée Chalamet. The actor hosted Saturday Night Live last night in New York City, where he was joined by the musical guest Boygenius. And while the star nailed his comedic sketches on-screen—did you catch him as a Troye Sivan sleep demon?—it was the show’s after-party that we’re particularly intrigued by. Stepping out with the rest of the SNL cast, Chalamet was joined by girlfriend Kylie Jenner—and they both embraced polar-opposite date night style for the affair, no less.Photo: Getty ImagesWhile Jenner and Chalamet have kept things coy and have rarely stepped out in public, the couple hit the town together last night, and they couldn’t be dressed more differently. Jenner continued her winning style streak of sleek, all-black looks: She wore an off-the-shoulder mini dress with shiny leggings and black strappy pumps. Chalamet, meanwhile, went a sportier and more colorful route: He sported a purple zip-up jacket with a colour-blocked hoodie and grey jeans.Photo: Getty ImagesTheir juxtaposing fashion vibe is something we’ve seen other A-list couples, like the Biebers, pull off. Who says couples have to match? As they’ve proven with their clashing outfits, individuality rules.This article first appeared on vogue.comTimothée Chalamet and Zendaya illustrate two different ways to pull off a vestKylie Jenner picks up her first fashion designer plaudit with Timothée in towThe pantless trend really is happening—and Kylie Jenner is hopping on the trend""",
                    output_text="""No, this article is not talking about white cotton jacket. At the maximum, the article mentions jacket but that is a very generic item and should not be given that much importance.""",
                ),
            ],
        )

    def getArticles(self, outfit):
        """Gets articles related to a given outfit.

        Args:
            outfit (str): The outfit to search for.

        Returns:
            list: A list of articles related to the outfit.
        """
        docs = self.ensemble_retriever.get_relevant_documents(outfit)

        answers = []
        included = set()
        for doc in docs:
            id = doc.metadata["id"]
            if id not in included:
                included.add(id)
                article_s = self.data[id][1]
                if len(self.data[id][1]) > 8000:
                    article_s = self.data[id][1][:8000]

                try:
                    response = self.chat.send_message(
                        "Is the following article related to "
                        + outfit
                        + " - "
                        + article_s
                        + " Respond in Yes or No",
                        **self.parameters
                    )
                    if response.text.split()[0][0] == "Y":
                        # [summary, link]
                        answers.append([self.data[id][1], self.data[id][0]])
                except Exception as e:
                    print(e)

                    # [summary, link]
                    answers.append([self.data[id][1], self.data[id][0]])

        return answers
