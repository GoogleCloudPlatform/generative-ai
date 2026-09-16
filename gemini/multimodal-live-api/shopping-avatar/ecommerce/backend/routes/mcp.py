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

import json
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from google.genai import types
from services import db, get_ai_client, get_embedding_client, MULTIMODAL_EMBEDDING_MODEL, settings

class StructuredSearchQuery(BaseModel):
    semantic_query: str = Field(description="The semantic search query without price range filters, e.g., 'blue cotton shirt'.")
    min_price: Optional[float] = Field(None, description="The minimum price filter if specified, e.g. 20.0 for 'above $20'.")
    max_price: Optional[float] = Field(None, description="The maximum price filter if specified, e.g. 50.0 for 'under $50'.")

logger = logging.getLogger("ecommerce-routes-mcp")
router = APIRouter()

class RPCRequest(BaseModel):
    jsonrpc: str
    id: int
    method: str
    params: dict = {}

@router.post("/api/mcp")
async def handle_mcp(rpc_req: RPCRequest, persona: str = "default"):
    """
    Exposes e-commerce catalog catalog search and cart execution APIs over standard JSON-RPC 2.0 protocol.
    """
    if rpc_req.jsonrpc != "2.0":
         raise HTTPException(status_code=400, detail="Invalid JSON-RPC version")

    method = rpc_req.method
    args = rpc_req.params.get("arguments", {})
    session_id = rpc_req.params.get("session_id", "default_session")

    try:
        if method == "tools/list":
            tools = [
                {
                    "name": "search_products",
                    "description": "SILENT EXECUTION. Search for products in the catalog using semantic description.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "The search query (e.g. 'blue cotton shirt')."}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "add_to_cart",
                    "description": "SILENT EXECUTION. Adds a product to the user's shopping cart after verifying inventory.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string"},
                            "quantity": {"type": "number"}
                        },
                        "required": ["product_id", "quantity"]
                    }
                },
                {
                    "name": "checkout_cart",
                    "description": "SILENT EXECUTION. Converts the items in the cart into a finalized purchase order.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "update_cart_item",
                    "description": "SILENT EXECUTION. Updates the quantity of a product in the user's shopping cart to a specific number. Setting quantity to 0 removes the item.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string"},
                            "quantity": {"type": "number"}
                        },
                        "required": ["product_id", "quantity"]
                    }
                },
                {
                    "name": "remove_from_cart",
                    "description": "SILENT EXECUTION. Removes a product completely from the user's shopping cart.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "product_id": {"type": "string"}
                        },
                        "required": ["product_id"]
                    }
                },
                {
                    "name": "get_cart",
                    "description": "SILENT EXECUTION. Retrieves all current items in the user's shopping cart.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                },
                {
                    "name": "change_theme",
                    "description": "SILENT EXECUTION. Changes the active retailer name, generating and updating the brand colors, font family and persisting the settings in Spanner.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "retailer": {
                                "type": "string",
                                "description": "The name of the retailer/brand to switch to (e.g. 'Home Depot', 'Target', 'Best Buy', 'Sephora')."
                            }
                        },
                        "required": ["retailer"]
                    }
                },
                {
                    "name": "get_product_reviews",
                    "description": "Retrieves customer reviews and star ratings for a specific product ID. Use this when the user asks what other customers think of a product.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "The product ID to get reviews for (e.g. 'PROD-XXXX')."
                            }
                        },
                        "required": ["product_id"]
                    }
                },
                {
                    "name": "get_product_details",
                    "description": "Retrieves comprehensive details for a specific product ID, including description, price, rating, inventory, and reviews count.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "product_id": {
                                "type": "string",
                                "description": "The product ID to retrieve details for (e.g. 'PROD-XXXX')."
                            }
                        },
                        "required": ["product_id"]
                    }
                }
            ]
            return {"jsonrpc": "2.0", "id": rpc_req.id, "result": {"tools": tools}}

        elif method == "tools/call":
            tool_name = rpc_req.params.get("name")
            
            if tool_name == "search_products":
                query = args.get("query")
                logger.info(f"Original search query: '{query}'")
                
                semantic_query = query
                min_price = None
                max_price = None
                
                try:
                    client = get_ai_client()
                    parse_response = client.models.generate_content(
                        model=settings.vqa_model,
                        contents=f"Extract the semantic query and price range limits from: '{query}'",
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=StructuredSearchQuery,
                            temperature=0.0
                        )
                    )
                    
                    structured_data = json.loads(parse_response.text)
                    semantic_query = structured_data.get("semantic_query") or query
                    min_price = structured_data.get("min_price")
                    max_price = structured_data.get("max_price")
                    logger.info(f"Structured search parameters extracted: semantic_query='{semantic_query}', min_price={min_price}, max_price={max_price}")
                except Exception as parse_err:
                    logger.error(f"Failed to parse query structure via Gemini: {parse_err}. Falling back to standard semantic search.")

                logger.info(f"Computing real embedding for query: '{semantic_query}'")
                formatted_query = f"task: search result | query: {semantic_query}"
                query_vector = [0.0] * 768
                try:
                    client = get_embedding_client()
                    response = client.models.embed_content(
                        model=MULTIMODAL_EMBEDDING_MODEL,
                        contents=formatted_query,
                        config=types.EmbedContentConfig(output_dimensionality=768)
                    )
                    if response.embeddings:
                        query_vector = response.embeddings[0].values
                except Exception as e:
                    logger.error(f"Failed to generate query embedding: {e}. Falling back to default mock vector.")
                    query_vector[0] = 1.0

                results = db.search_products(query_vector, min_price=min_price, max_price=max_price)
                
                return {
                    "jsonrpc": "2.0", 
                    "id": rpc_req.id, 
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(results)}],
                        "isError": False
                    }
                }

            elif tool_name == "add_to_cart":
                product_id = args.get("product_id")
                qty = int(args.get("quantity", 1))
                
                result = db.add_to_cart(session_id, product_id, qty)
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False
                    }
                }

            elif tool_name == "checkout_cart":
                customer_id = "CUST-TEST-001" # Mocked customer reference
                result = db.checkout_cart(session_id, customer_id)
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False
                    }
                }

            elif tool_name == "update_cart_item":
                product_id = args.get("product_id")
                qty = int(args.get("quantity", 0))
                result = db.update_cart_item(session_id, product_id, qty)
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False
                    }
                }

            elif tool_name == "remove_from_cart":
                product_id = args.get("product_id")
                result = db.remove_from_cart(session_id, product_id)
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False
                    }
                }

            elif tool_name == "get_cart":
                result = {"items": db.get_cart_items(session_id)}
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False
                    }
                }

            elif tool_name == "change_theme":
                retailer = args.get("retailer")
                if not retailer:
                    raise ValueError("Retailer name is required.")
                
                # Update settings in memory
                settings.retailer = retailer
                
                # Clear backend product image cache
                try:
                    from routes.products import image_cache
                    image_cache.clear()
                except Exception:
                    pass
                
                # Generate dynamic brand theme and save it to Spanner
                from routes.config import fetch_dynamic_brand_theme
                theme = fetch_dynamic_brand_theme(retailer)
                
                # Retain the active assistant persona
                try:
                    active_settings = db.get_active_retailer_settings()
                    if active_settings:
                        theme["persona"] = active_settings.get("persona", "shopper")
                except Exception:
                    pass
                
                db.save_retailer_settings(retailer, theme)
                
                result = {"status": "success", "retailer": retailer, "theme": theme}
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False
                    }
                }

            elif tool_name == "get_product_reviews":
                product_id = args.get("product_id")
                if not product_id:
                    raise ValueError("product_id is required.")
                result = db.get_reviews(product_id)
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False
                    }
                }

            elif tool_name == "get_product_details":
                product_id = args.get("product_id")
                if not product_id:
                    raise ValueError("product_id is required.")
                result = db.get_product(product_id)
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result)}],
                        "isError": False
                    }
                }

            else:
                return {
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "error": {"code": -32601, "message": "Method not found"}
                }

    except Exception as e:
        logger.error(f"Error handling RPC tool call: {str(e)}")
        return {
            "jsonrpc": "2.0",
            "id": rpc_req.id,
            "result": {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }
        }
