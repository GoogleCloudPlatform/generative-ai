from chromaWrapper import *
import vertexai
from vertexai.generative_models import GenerativeModel, Part, SafetySetting


class marketingRag():
  def __init__(self):
    marketing_folder = "./Marketing/"
    self.chroma = chroma_db("Marketing Chroma Client")
    self.chroma.create_collection("chroma_marketing", Vanilla_Embedding_Model(), {"hnsw:space": "cosine"})
    self.load_marketing_flyers(marketing_folder)

  def load_marketing_flyers(self, marketing_folder = "./Marketing/"):
    self.chroma.add_pdfs(marketing_folder)

  def return_marketing_doc(self, produce_name):
    rag_response = self.chroma.collection.query(query_texts=[produce_name], n_results=1)
    #rag_doc_name = self.chroma.collection.query(query_texts=[prompt], n_results=1)['ids'][0][0]
    return rag_response['documents'][0][0]

  def return_marketing_ad(self, produce_name, rating_dict):
    # NOTE The Doc Name is not coming from the PDF Title (Can pull from chunk_id in rag), it is pulling the first line of the chunk as the title.
    doc_info =  self.return_marketing_doc(produce_name)

    model = GenerativeModel(model_name="gemini-1.5-pro-002", safety_settings=safety_settings, generation_config=generation_config)
    ad_prompt = get_ad_prompt(rating_dict, doc_info)
    response = model.generate_content([ad_prompt])
    return  response.text
    # Call Imagen 3 for Picture
    # return marketing_image , marketing_text


def get_ad_prompt(rating_dict, chunk_from_chroma):
  advertisement_prompt = f"""
  Objective: Create a humorous personalized advertisement for a potential customer based on feedback they got about their current produce from a competitor.
  Input:
  rating: A numerical rating (1-5 stars; With 5 stars being the best rating) of the customer's current produce.
  quality_reasoning: A brief explanation of their produce from a competitor.
  pros: A few jokes about the hypothetical pros of the customer's current produce (e.g., "so ripe, it's practically pre-composted," "perfect for training your bite strength").
  cons: A few cons of the customer's current produce (e.g., "requires a hazmat suit to handle," "doubles as a projectile weapon").
  market_flyer: Our grocery store/market's weekly flyer in text format, including current deals and promotions.
  Output:
  A 100 word personalized advertisement that is fully utilizing Markdown and start with a title:
  Acknowledges the customer's feedback: Start by empathizing with the customer's produce woes in a humorous way, referencing their rating, quality_reasoning, pros, and cons.
  Highlights relevant deals: Use the market_flyer to showcase specific produce deals that address the customer's concerns. For example, if the customer complains about "bruised apples," highlight a deal on apples and emphasize their freshness and quality.
  Emphasizes quality and freshness: Use persuasive language to convey the superiority of the market's produce.
  Includes a call to action: Encourage the customer to visit the store or website to take advantage of the deals.
  Input:
  rating: {rating_dict['rating']}
  quality_reasoning: {rating_dict['quality_reasoning']}
  pros: {rating_dict['pros']}
  cons: {rating_dict['cons']}
  market_flyer: {chunk_from_chroma}
  """
  return advertisement_prompt





generation_config = {
    "max_output_tokens": 8192,
    "temperature": 1,
    "top_p": 0.95,
}

safety_settings = [
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE
    ),
    SafetySetting(
        category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=SafetySetting.HarmBlockThreshold.BLOCK_NONE
    ),
]

