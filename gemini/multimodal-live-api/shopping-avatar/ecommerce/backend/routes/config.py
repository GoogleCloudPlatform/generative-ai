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
import logging
from fastapi import APIRouter
import json
from services import VERTEX_PROJECT_ID, VERTEX_LOCATION, GEMINI_LIVE_MODEL, ai_client, db
from config import settings

logger = logging.getLogger("ecommerce-routes-config")
router = APIRouter()

RETAILER_THEMES = {
    "Retail": {
        "name": "Retail",
        "primary": "#000000",
        "secondary": "#ffffff",
        "font": "Inter, sans-serif"
    },
    "Target": {
        "name": "Target",
        "primary": "#cc0000",
        "secondary": "#ffffff",
        "font": "Inter, sans-serif"
    },
    "Best Buy": {
        "name": "Best Buy",
        "primary": "#0046be",
        "secondary": "#ffe000",
        "font": "Roboto, sans-serif"
    },
    "Sephora": {
        "name": "Sephora",
        "primary": "#000000",
        "secondary": "#ffffff",
        "font": "Georgia, serif"
    }
}

def fetch_dynamic_brand_theme(retailer: str) -> dict:
    if retailer in RETAILER_THEMES:
        return RETAILER_THEMES[retailer]
    
    try:
        prompt = (
            f"Analyze the brand colors and typography style of the retailer '{retailer}'. "
            f"Suggest a matching color palette and typography font. "
            f"Return a raw JSON object containing:\n"
            f"- 'primary': Hex code string for the primary brand color (e.g. '#cc0000')\n"
            f"- 'secondary': Hex code string for the secondary brand color (e.g. '#ffffff')\n"
            f"- 'font': Web font family string (e.g. 'Roboto, sans-serif')\n"
            f"Output raw JSON only, no markdown."
        )
        response = ai_client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt
        )
        clean_text = response.text.replace("```json", "").replace("```", "").replace("```JSON", "").strip()
        data = json.loads(clean_text)
        return {
            "name": retailer,
            "primary": data.get("primary", "#1976d2"),
            "secondary": data.get("secondary", "#ffffff"),
            "font": data.get("font", "sans-serif")
        }
    except Exception as e:
        logger.error(f"Dynamic branding generation failed: {e}", exc_info=True)
        return {
            "name": retailer,
            "primary": "#1976d2",
            "secondary": "#ffffff",
            "font": "sans-serif"
        }
SYSTEM_PROMPTS = {
    "shopper": (
        "You are a helpful e-commerce shopping assistant. "
        "Help customers discover products and manage their shopping cart. "
        "Speak in short, conversational sentences (3-4 sentences max). "
        "Do not use markdown, bold text, or bullet points in your speech output. "
        "If the user asks about specific types of clothes, styles, or products, "
        "you MUST trigger the `search_products` tool. "
        "If they ask for details, price, description, reviews, or information about a specific product, call `get_product_details` with the product's ID. "
        "If they want to buy or keep an item, call `add_to_cart`. "
        "If they want to update the quantity of a product in their cart, call `update_cart_item`. "
        "If they want to remove a product from their cart, call `remove_from_cart`. "
        "If they want to see what is currently in their cart, call `get_cart`. "
        "If they are ready to purchase, call `checkout_cart`."
    ),
    "teenager": (
        "You are a disgruntled teenage e-commerce shopping assistant who would rather be anywhere else. "
        "You use terms like 'Yasss Queeen' and 'NOooooah', smirk a lot (indicated by *smirks* or text descriptions of smirking), "
        "and act generally bored or annoyed, but you still get things done. "
        "Help customers discover products and manage their shopping cart, but maintain your teenage attitude. "
        "Speak in short, conversational sentences (3-4 sentences max). "
        "Do not use markdown, bold text, or bullet points in your speech output. "
        "If the user asks about specific types of clothes, styles, or products, "
        "you MUST trigger the `search_products` tool. "
        "If they ask for details, price, description, reviews, or information about a specific product, call `get_product_details` with the product's ID. "
        "If they want to buy or keep an item, call `add_to_cart`. "
        "If they want to update the quantity of a product in their cart, call `update_cart_item`. "
        "If they want to remove a product from their cart, call `remove_from_cart`. "
        "If they want to see what is currently in their cart, call `get_cart`. "
        "If they are ready to purchase, call `checkout_cart`. "
        "DO NOT MENTION action like smirks, eye rolls or any other action/emotion in your response. "
    )
}


@router.get("/api/config")
async def get_config(mode: str = "google_1p", avatar: str = "Vera"):
    """
    Returns bootstrapped connection parameters and configurations for the e-commerce session.
    """
    use_vertex_live = True
    model_name = GEMINI_LIVE_MODEL
    location_to_return = VERTEX_LOCATION or "global"
    
    # Resolve branding theme config dynamically with Spanner persistence
    try:
        theme = db.get_active_retailer_settings()
    except Exception as read_err:
        logger.warning(f"Failed to read retailer settings from Spanner: {read_err}")
        theme = None

    if not theme:
        fallback_retailer = "Retail"
        theme = fetch_dynamic_brand_theme(fallback_retailer)
        theme["persona"] = "shopper"
        try:
            db.save_retailer_settings(fallback_retailer, theme)
        except Exception as save_err:
            logger.warning(f"Failed to persist default settings to Spanner: {save_err}")
    
    persona = theme.get("persona", "shopper") if theme else "shopper"
    system_prompt = SYSTEM_PROMPTS.get(persona, SYSTEM_PROMPTS["shopper"])
    
    AVATAR_VOICES = {
        "Vera": "Aoede",     # Female
        "Kira": "Kore",      # Female
        "Ingrid": "Aoede",   # Female
        "Sam": "Charon",     # Male
        "Jay": "Fenrir",     # Male
        "Paul": "Puck",      # Male
        "Ben": "Charon",     # Male
        "Kai": "Fenrir",     # Male
        "Carmen": "Kore",    # Female
        "Leo": "Puck",       # Male
        "Piper": "Aoede"     # Female
    }
    avatar_to_use = avatar if avatar in AVATAR_VOICES else "Vera"
    voice_to_use = AVATAR_VOICES.get(avatar_to_use, "Aoede")

    return {
        "apiKey": "",
        "modelName": model_name,
        "systemPrompt": system_prompt,
        "useVertexAI": True,
        "vertexProjectID": VERTEX_PROJECT_ID,
        "vertexLocation": location_to_return,
        "avatarMode": mode,
        "google1PAvatarName": avatar_to_use if mode == "google_1p" else "none",
        "google1PVoiceName": voice_to_use if mode == "google_1p" else "Aoede",
        "vadSilenceDurationMs": 400,
        "theme": theme
    }

