# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

# Resolve parent directory path to import the local backend modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import random
import argparse
import logging
from decimal import Decimal
from datetime import datetime, timezone
from google.cloud import spanner
from google.cloud import storage
from faker import Faker
import urllib.request
from auth import AuthService
from config import settings

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("DataGenerator")

# Base Prompts list
BASE_PROMPTS = [
    "A modern matte black smart coffee maker on a wooden kitchen counter",
    "A sleek minimalist tan leather backpack, front view",
    "An ergonomic aluminum alloy laptop stand on a clean desk",
    "A copper double-walled insulated travel mug",
    "A retro mechanical keyboard with pastel keycaps",
    "A high-fidelity noise-canceling wireless headphones in slate gray",
    "A minimalist concrete desktop organizer tray",
    "A portable glass water bottle with a cork sleeve",
    "A woven bamboo laundry basket with handles",
    "A brass desk lamp with an adjustable arm and Edison bulb",
    "An organic cotton waffle-weave bath towel in olive green",
    "A pair of modern cork-soled house slippers",
    "A ceramic pour-over coffee dripper in speckled white",
    "A natural wood wall clock with black metal hands",
    "A set of three matte ceramic succulent planter pots",
    "A portable solar-powered camping lantern in forest green",
    "A sleek magnetic aluminum phone mount for a car vent",
    "A handcrafted leather journal with a wrap strap",
    "A modern smart watch with a dark green silicone band",
    "An ultrasonic essential oil diffuser with a light wood base"
]

PROMPT_COLORS = [
    ["matte black", "stainless steel", "crimson red", "emerald green"],
    ["tan", "olive green", "charcoal gray", "navy blue"],
    ["aluminum alloy", "matte black", "space gray", "rose gold"],
    ["copper", "stainless steel", "matte black", "polar white"],
    ["pastel", "retro beige", "neon RGB", "monochrome gray"],
    ["slate gray", "polar white", "matte black", "navy blue"],
    ["concrete", "terrazzo", "charcoal", "terracotta"],
    ["cork", "charcoal silicone", "sage green silicone", "blush pink silicone"],
    ["woven bamboo", "woven dark wood", "gray wicker", "white cotton"],
    ["brass", "matte black", "polished chrome", "antique bronze"],
    ["olive green", "slate gray", "polar white", "mustard yellow"],
    ["cork-soled", "wool-soled", "suede-soled", "leather-soled"],
    ["speckled white", "matte black", "terracotta", "cobalt blue"],
    ["natural wood", "dark walnut", "weathered gray", "painted white"],
    ["matte ceramic", "rustic terracotta", "pastel pink", "sage green"],
    ["forest green", "safety orange", "matte black", "coyote tan"],
    ["aluminum", "matte black", "space gray", "carbon fiber"],
    ["leather", "suede", "canvas", "waxed canvas"],
    ["dark green", "matte black", "sand pink", "navy blue"],
    ["light wood", "dark walnut", "white ceramic", "black marble"]
]

PROMPT_DEFAULT_COLORS = [
    "matte black", "tan", "aluminum alloy", "copper", "pastel",
    "slate gray", "concrete", "cork", "woven bamboo", "brass",
    "olive green", "cork-soled", "speckled white", "natural wood",
    "matte ceramic", "forest green", "aluminum", "leather",
    "dark green", "light wood"
]

# Attempt to import Google GenAI library, with dynamic mock fallbacks
try:
    from google import genai
    from google.genai import types
    HAS_GENAI = True
except ImportError:
    logger.warn("Google GenAI library not installed. Falling back to simulated mocks.")
    HAS_GENAI = False

def write_status(stage: str, current: int, total: int, message: str, is_running: bool = True):
    try:
        scratch_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
        os.makedirs(scratch_dir, exist_ok=True)
        status_path = os.path.join(scratch_dir, "seeding_status.json")
        with open(status_path, "w") as f:
            json.dump({
                "is_running": is_running,
                "stage": stage,
                "current": current,
                "total": total,
                "message": message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }, f)
    except Exception as e:
        logger.error(f"Failed to write status file: {e}")

def generate_ai_products(count: int, project_id: str, location: str, category_filter: str = "") -> list[dict]:
    """
    Executes the multi-step AI product generation pipeline.
    1. Generates product images (Imagen).
    2. Runs Visual Question Answering (VQA) using Gemini to draft details.
    3. populates description and image vector embeddings (Multimodalembedding).
    """
    client = None
    gcs_token = None
    if HAS_GENAI:
        try:
            # Initialize the unified google-genai Client for Cloud / Vertex AI mode
            client = genai.Client(vertexai=True, project=project_id, location=location)
        except Exception as e:
            logger.error(f"Failed to initialize AI SDK: {e}. Mocks active.")
            
    try:
        auth_svc = AuthService()
        gcs_token = auth_svc.get_token()
    except Exception as e:
        logger.error(f"Failed to retrieve GCS auth token: {e}")

    # Step 0: Generate dynamic product prompts based on the retailer using Gemini
    prompts = []
    retailer = settings.retailer
    write_status("prompts", 0, count, f"Generating product image prompts for '{retailer}' using Gemini...")
    if client:
        try:
            vqa_model = os.getenv("VQA_MODEL", "gemini-3.5-flash")
            logger.info(f"Generating {count} product prompts for retailer '{retailer}' using Gemini ({vqa_model})...")
            prompt_instructions = (
                f"Generate a list of {count} unique, high-quality, aesthetic product image prompts "
                f"typical of what a customer would buy at '{retailer}'. "
                f"Each prompt should describe a distinct product in a clean, professional, "
                f"e-commerce catalog style with rich details (colors, materials, backgrounds). "
            )
            if category_filter:
                prompt_instructions += f"All generated products MUST strictly belong to the '{category_filter}' category. "
            prompt_instructions += (
                f"Example: 'A modern matte black smart coffee maker on a wooden kitchen counter'. "
                f"Return a raw JSON array of strings only, no markdown formatting."
            )
            response = client.models.generate_content(
                model=vqa_model,
                contents=prompt_instructions
            )
            clean_text = response.text.replace("```json", "").replace("```", "").replace("```JSON", "").strip()
            prompts = json.loads(clean_text)
            if not isinstance(prompts, list) or len(prompts) < count:
                logger.warning("Gemini did not return enough prompts. Falling back to base prompts.")
                prompts = []
        except Exception as ex:
            logger.warning(f"Failed to generate dynamic prompts via Gemini: {ex}. Falling back to base prompts.")

    # Fallback to static base prompts
    if not prompts:
        prompts = []
        for i in range(count):
            prompt_idx = i % len(BASE_PROMPTS)
            base_prompt = BASE_PROMPTS[prompt_idx]
            
            color_options = PROMPT_COLORS[prompt_idx]
            color_idx = (i // len(BASE_PROMPTS)) % len(color_options)
            new_color = color_options[color_idx]
            
            default_color = PROMPT_DEFAULT_COLORS[prompt_idx]
            prompt = base_prompt.replace(default_color, new_color)
            prompts.append(prompt)

    import uuid
    products = []
    for i in range(count):
        prompt = prompts[i]
        unique_suffix = uuid.uuid4().hex[:8].upper()
        product_id = f"PROD-{unique_suffix}"
        write_status("products", i + 1, count, f"Generating product {i+1} of {count} using Gemini Imagen & VQA...")
        logger.info(f"[{i+1}/{count}] Generating metadata for product {product_id} using prompt: '{prompt}'")

        image_bytes = None
        gcs_bucket_name = os.getenv("GCS_BUCKET_NAME", "gen-ai-4all-live-retail-images")
        image_url = f"https://storage.googleapis.com/{gcs_bucket_name}/products/{product_id}.png"
        
        # Step 1: Gemini Image Generation (using gemini-3.1-flash-image)
        if client:
            try:
                img_model = os.getenv("IMAGE_GENERATION_MODEL", "gemini-3.1-flash-image")
                logger.info(f"Generating image with model {img_model} for prompt: '{prompt}'")
                response = client.models.generate_content(
                    model=img_model,
                    contents=[prompt],
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                        image_config=types.ImageConfig(
                            aspect_ratio="1:1"
                        )
                    )
                )
                
                # Extract generated image bytes
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        raw_data = part.inline_data.data
                        import base64
                        if isinstance(raw_data, str):
                            image_bytes = base64.b64decode(raw_data)
                        else:
                            image_bytes = raw_data
                        break
                
                if image_bytes:
                    # Keep raw PNG image_bytes for downstream VQA and Embeddings steps
                    # But convert to WebP for disk storage and GCS upload to optimize storage/bandwidth
                    import io
                    from PIL import Image
                    try:
                        img = Image.open(io.BytesIO(image_bytes))
                        webp_io = io.BytesIO()
                        img.save(webp_io, format="WEBP", quality=80)
                        storage_bytes = webp_io.getvalue()
                        logger.info(f"Compressed generated image from {len(image_bytes)} bytes to {len(storage_bytes)} bytes WebP")
                    except Exception as compress_err:
                        logger.warning(f"Failed to compress image to WebP: {compress_err}")
                        storage_bytes = image_bytes

                    os.makedirs("output_images", exist_ok=True)
                    with open(f"output_images/{product_id}.png", "wb") as f:
                        f.write(storage_bytes)
                    logger.info(f"Generated and saved image output_images/{product_id}.png")
                    
                    if gcs_token:
                        try:
                            object_name = f"products/{product_id}.png"
                            upload_url = f"https://storage.googleapis.com/upload/storage/v1/b/{gcs_bucket_name}/o?uploadType=media&name={object_name}"
                            mime_type = "image/webp" if storage_bytes != image_bytes else "image/png"
                            headers = {
                                "Authorization": f"Bearer {gcs_token}",
                                "Content-Type": mime_type
                            }
                            req = urllib.request.Request(upload_url, data=storage_bytes, headers=headers, method="POST")
                            with urllib.request.urlopen(req) as res:
                                logger.info(f"Uploaded product image to gs://{gcs_bucket_name}/products/{product_id}.png via REST API.")
                        except Exception as gcs_err:
                            logger.error(f"GCS Image upload failed for bucket '{gcs_bucket_name}' via REST: {gcs_err}")
            except Exception as ex:
                logger.warn(f"Gemini image generation failed, using mock placeholder: {ex}")

        # Step 2: VQA Details via Gemini
        title = f"Premium {prompt.split('on')[0].split(',')[0].strip()}"
        description = f"High quality product generated based on prompt: {prompt}"
        price = Decimal(str(round(random.uniform(15.99, 149.99), 2)))
        category = "E-Commerce Goods"

        if client:
            try:
                vqa_instructions = (
                    "Act as an e-commerce merchandiser. Based on the provided image/prompt, output a structured JSON containing:\n"
                    "1. 'title': A catchy, marketing-friendly product title.\n"
                    "2. 'description': A detailed product description outlining features.\n"
                    "3. 'price': A realistic decimal price (between 5.00 and 500.00).\n"
                )
                if category_filter:
                    vqa_instructions += f"4. 'category': Must be exactly '{category_filter}'.\n"
                else:
                    vqa_instructions += "4. 'category': An e-commerce category name (e.g. Kitchen, Home, Apparel).\n"
                vqa_instructions += "Output raw JSON only, no markdown formatting."
                
                content_inputs = [prompt, vqa_instructions]
                if image_bytes:
                    content_inputs.append(
                        types.Part.from_bytes(data=image_bytes, mime_type="image/png")
                    )
                
                vqa_model = os.getenv("VQA_MODEL", "gemini-3.5-flash")
                response = client.models.generate_content(
                    model=vqa_model,
                    contents=content_inputs
                )
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
                
                title = data.get("title", title)
                description = data.get("description", description)
                price = Decimal(str(data.get("price", price)))
                category = data.get("category", category)
                logger.info(f"Gemini VQA completed. Title: '{title}', Category: '{category}'")
            except Exception as ex:
                logger.warn(f"Gemini VQA step failed, using default info template: {ex}")

        # Step 3: Embeddings generation
        embedding = [0.0] * 768
        image_embedding = [0.0] * 1408

        if client:
            try:
                emb_model_name = os.getenv("MULTIMODAL_EMBEDDING_MODEL", "gemini-embedding-2")
                emb_location = os.getenv("MULTIMODAL_EMBEDDING_LOCATION", "global")
                emb_client = genai.Client(vertexai=True, project=project_id, location=emb_location)
                # Text embedding (768 length)
                formatted_doc = f"title: {title} | text: {description}"
                text_response = emb_client.models.embed_content(
                    model=emb_model_name,
                    contents=formatted_doc,
                    config=types.EmbedContentConfig(output_dimensionality=768)
                )
                if text_response.embeddings:
                    embedding = text_response.embeddings[0].values

                # Image embedding (1408 length)
                if image_bytes:
                    image_response = emb_client.models.embed_content(
                        model=emb_model_name,
                        contents=types.Part.from_bytes(data=image_bytes, mime_type="image/png"),
                        config=types.EmbedContentConfig(output_dimensionality=1408)
                    )
                    if image_response.embeddings:
                        image_embedding = image_response.embeddings[0].values
                logger.info(f"Multimodal vector embeddings generated via {emb_model_name} in location {emb_location}.")
            except Exception as ex:
                logger.warn(f"Embedding calculation step failed, using zeroed vector arrays: {ex}")

        products.append({
            "product_id": product_id,
            "name": title,
            "description": description,
            "price": price,
            "inventory_level": random.randint(5, 150),
            "image_url": image_url,
            "embedding": embedding,
            "image_embedding": image_embedding
        })

    return products


from pydantic import BaseModel, Field
from typing import List

class GeneratedReview(BaseModel):
    customer_name: str = Field(description="A realistic customer name")
    rating: int = Field(description="Star rating from 1 to 5")
    comment: str = Field(description="Review text comment contextually relevant to the product description")

class ProductReviewsList(BaseModel):
    reviews: List[GeneratedReview]


def generate_synthetic_data(products_count: int, customers_count: int, orders_count: int, project_id: str, location: str, category: str = "") -> tuple[list, list, list, list, list]:
    """
    Orchestrates e-commerce catalog generation using Faker.
    """
    fake = Faker()
    
    # 1. Products Layer
    products = generate_ai_products(products_count, project_id, location, category)
    product_ids = [p["product_id"] for p in products]

    # 2. Customers Layer
    write_status("customers", 0, customers_count, f"Generating {customers_count} customer profiles using Faker...")
    customers = []
    for i in range(customers_count):
        customers.append({
            "customer_id": f"CUST-{2000 + i}",
            "name": fake.name(),
            "email": fake.email(),
            "created_at": datetime.now(timezone.utc)
        })
    customer_ids = [c["customer_id"] for c in customers]

    # 3. Orders & Items Layer
    write_status("orders", 0, orders_count, f"Generating {orders_count} mock customer orders...")
    orders = []
    order_items = []
    
    for i in range(orders_count):
        order_id = f"ORD-{3000 + i}"
        customer_id = random.choice(customer_ids)
        
        # Pick 1-4 random products for this order (capped by total products)
        num_items = random.randint(1, min(4, len(products)))
        selected_products = random.sample(products, num_items)
        
        total_amount = Decimal("0.00")
        for p in selected_products:
            qty = random.randint(1, 3)
            unit_price = p["price"]
            total_amount += unit_price * qty
            
            order_items.append({
                "order_id": order_id,
                "product_id": p["product_id"],
                "quantity": qty,
                "unit_price": unit_price
            })

        orders.append({
            "order_id": order_id,
            "customer_id": customer_id,
            "total_amount": total_amount,
            "created_at": fake.date_time_between(start_date='-30d', end_date='now', tzinfo=timezone.utc)
        })

    # 4. Reviews Layer
    reviews = []
    reviews_comments = {
        5: [
            "Absolutely love this product! The quality is top-notch.",
            "Highly recommended. Exceeded all my expectations.",
            "Super fast shipping, works exactly as described.",
            "Beautiful design and great functionality!",
            "Perfect! Couldn't be happier with this purchase."
        ],
        4: [
            "Really good product, but the shipping took a bit longer.",
            "Works well. Good value for money.",
            "Satisfied with the purchase. Product is fine.",
            "Decent quality, matching description.",
            "Good build quality and performance."
        ],
        3: [
            "It is okay, but not as premium as it looks.",
            "Average product. Does the job but nothing special.",
            "Mediocre quality for the price.",
            "Functional, but has some minor design flaws.",
            "It's fine, but I expected slightly more features."
        ],
        2: [
            "Disappointed. Did not work as expected.",
            "Not very durable. Already showing signs of wear.",
            "Poor quality. Would not buy again.",
            "Felt cheap and performance was subpar.",
            "Hard to use and instructions were unclear."
        ],
        1: [
            "Terrible product. Arrived broken.",
            "Waste of money. Avoid at all costs!",
            "Absolutely horrible. Stopped working after one day.",
            "Defective on arrival and very poor quality.",
            "Completely useless. Do not buy."
        ]
    }
    
    # Initialize the unified google-genai Client for reviews if available
    client = None
    if HAS_GENAI:
        try:
            client = genai.Client(vertexai=True, project=project_id, location=location)
        except Exception as e:
            logger.error(f"Failed to initialize AI Client for reviews: {e}")

    write_status("reviews", 0, len(products), f"Generating synthetic reviews using Gemini...")
    import uuid
    for idx, p in enumerate(products):
        product_id = p["product_id"]
        title = p["name"]
        description = p["description"]
        
        # Choose positive/neutral combo or negative combo
        sentiment_bucket = random.choice(["positive", "negative"])
        generated_reviews = []
        
        if client:
            try:
                if sentiment_bucket == "positive":
                    prompt = (
                        f"Generate exactly 3 customer reviews for the product '{title}' based on its description: '{description}'.\n"
                        f"- Two reviews must have a high rating (4 or 5 stars) expressing satisfaction.\n"
                        f"- One review must have a neutral rating (3 stars) expressing mixed thoughts.\n"
                        f"Provide a realistic name for each reviewer."
                    )
                else:
                    prompt = (
                        f"Generate exactly 2 customer reviews for the product '{title}' based on its description: '{description}'.\n"
                        f"- Both reviews must have a low rating (1 or 2 stars) complaining about features mentioned in the description.\n"
                        f"Provide a realistic name for each reviewer."
                    )
                
                vqa_model = os.getenv("VQA_MODEL", "gemini-3.5-flash")
                response = client.models.generate_content(
                    model=vqa_model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=ProductReviewsList,
                        temperature=0.7
                    )
                )
                
                clean_text = response.text.replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
                for rev in data.get("reviews", []):
                    generated_reviews.append({
                        "product_id": product_id,
                        "review_id": f"REV-{uuid.uuid4().hex[:10].upper()}",
                        "customer_name": rev.get("customer_name") or fake.name(),
                        "rating": int(rev.get("rating") or 5),
                        "comment": rev.get("comment") or "",
                        "created_at": fake.date_time_between(start_date='-15d', end_date='now', tzinfo=timezone.utc)
                    })
            except Exception as ex:
                logger.warning(f"Failed to generate dynamic reviews via Gemini for {product_id}: {ex}. Falling back to templates.")
                generated_reviews = []
                
        if not generated_reviews:
            # Fallback to offline template list
            num_reviews = 3 if sentiment_bucket == "positive" else 2
            for i in range(num_reviews):
                if sentiment_bucket == "positive":
                    rating = 3 if i == 2 else random.choice([4, 5])
                else:
                    rating = random.choice([1, 2])
                
                comment = random.choice(reviews_comments[rating])
                generated_reviews.append({
                    "product_id": product_id,
                    "review_id": f"REV-{uuid.uuid4().hex[:10].upper()}",
                    "customer_name": fake.name(),
                    "rating": rating,
                    "comment": comment,
                    "created_at": fake.date_time_between(start_date='-15d', end_date='now', tzinfo=timezone.utc)
                })
                
        reviews.extend(generated_reviews)

    return products, customers, orders, order_items, reviews


def ingest_to_spanner(instance_id: str, database_id: str, project_id: str, data: tuple):
    """
    Ingests e-commerce records into Spanner using batch mutations.
    Strict execution order: Products -> Customers -> Orders -> OrderItems -> Reviews.
    """
    products, customers, orders, order_items, reviews = data
    
    spanner_client = spanner.Client(project=project_id)
    instance = spanner_client.instance(instance_id)
    db = instance.database(database_id)

    logger.info("Initializing Spanner Ingestion Pipeline...")

    # 1. Ingest Products
    write_status("spanner", 10, 100, f"Ingesting {len(products)} products into Spanner...")
    logger.info(f"Ingesting {len(products)} products into Spanner...")
    with db.batch() as batch:
        batch.insert_or_update(
            table='products',
            columns=['product_id', 'name', 'description', 'price', 'inventory_level', 'image_url', 'embedding', 'image_embedding'],
            values=[
                [
                    p["product_id"], p["name"], p["description"], p["price"], p["inventory_level"], p["image_url"], p["embedding"], p["image_embedding"]
                ] for p in products
            ]
        )

    # 2. Ingest Customers
    write_status("spanner", 30, 100, f"Ingesting {len(customers)} customers into Spanner...")
    logger.info(f"Ingesting {len(customers)} customers into Spanner...")
    with db.batch() as batch:
        batch.insert_or_update(
            table='customers',
            columns=['customer_id', 'name', 'email', 'created_at'],
            values=[
                [c["customer_id"], c["name"], c["email"], c["created_at"]] for c in customers
            ]
        )

    # 3. Ingest Orders
    write_status("spanner", 50, 100, f"Ingesting {len(orders)} orders into Spanner...")
    logger.info(f"Ingesting {len(orders)} orders into Spanner...")
    with db.batch() as batch:
        batch.insert_or_update(
            table='orders',
            columns=['order_id', 'customer_id', 'total_amount', 'created_at'],
            values=[
                [o["order_id"], o["customer_id"], o["total_amount"], o["created_at"]] for o in orders
            ]
        )

    # 4. Ingest Order Items
    write_status("spanner", 70, 100, f"Ingesting {len(order_items)} order items into Spanner...")
    logger.info(f"Ingesting {len(order_items)} order items into Spanner...")
    with db.batch() as batch:
        batch.insert_or_update(
            table='order_items',
            columns=['order_id', 'product_id', 'quantity', 'unit_price'],
            values=[
                [oi["order_id"], oi["product_id"], oi["quantity"], oi["unit_price"]] for oi in order_items
            ]
        )

    # 5. Ingest Reviews
    write_status("spanner", 90, 100, f"Ingesting {len(reviews)} reviews into Spanner...")
    logger.info(f"Ingesting {len(reviews)} reviews into Spanner...")
    with db.batch() as batch:
        batch.insert_or_update(
            table='reviews',
            columns=['product_id', 'review_id', 'customer_name', 'rating', 'comment', 'created_at'],
            values=[
                [r["product_id"], r["review_id"], r["customer_name"], r["rating"], r["comment"], r["created_at"]] for r in reviews
            ]
        )

    write_status("complete", 100, 100, "Spanner Data Seeding Complete!", is_running=False)
    logger.info("Spanner Data Seeding Complete!")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic data pipeline for Cloud Spanner.")
    parser.add_argument("--products", type=int, default=20, help="Number of products to generate.")
    parser.add_argument("--customers", type=int, default=50, help="Number of customers to generate.")
    parser.add_argument("--orders", type=int, default=100, help="Number of orders to generate.")
    parser.add_argument("--category", type=str, default="", help="Optional category filter to generate products under.")
    
    parser.add_argument("--instance", type=str, default=settings.spanner_instance, help="Cloud Spanner Instance ID.")
    parser.add_argument("--database", type=str, default=settings.spanner_database, help="Cloud Spanner Database ID.")
    parser.add_argument("--project", type=str, default=settings.google_cloud_project or settings.vertex_project_id, help="Google Cloud Project ID.")
    parser.add_argument("--location", type=str, default=settings.google_cloud_location or settings.vertex_location, help="GCP Region Location.")
    
    args = parser.parse_args()

    project_id = args.project
    if not project_id:
        logger.error("GCP Project ID must be specified via --project CLI arg, GOOGLE_CLOUD_PROJECT/VERTEX_PROJECT_ID environment variable, or in .env.")
        exit(1)

    try:
        logger.info(f"Starting Seeding Pipeline: Products={args.products}, Customers={args.customers}, Orders={args.orders}")
        
        # 1. Run Data Generation Loops
        generated_data = generate_synthetic_data(
            args.products, args.customers, args.orders, project_id, args.location, args.category
        )
        
        # 2. Ingest into Spanner Instance
        ingest_to_spanner(args.instance, args.database, project_id, generated_data)
    except Exception as e:
        logger.error(f"Seeding pipeline crashed with exception: {e}")
        write_status("error", 0, 100, f"Seeding failed: {str(e)}", is_running=False)
        sys.exit(1)
