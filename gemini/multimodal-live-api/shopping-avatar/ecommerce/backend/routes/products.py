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
import asyncio
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, Field
from services import db, auth_svc, settings, VERTEX_PROJECT_ID

logger = logging.getLogger("ecommerce-routes-products")
router = APIRouter()

# Global in-memory image cache (product_id -> bytes)
image_cache = {}

@router.get("/api/products")
async def get_products(limit: int = 8, offset: int = 0):
    """
    Returns a list of products from the catalog.
    """
    try:
        products = db.get_products(limit=limit, offset=offset)
        return products
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/products/{product_id}/image")
async def get_product_image(product_id: str):
    """
    Serves the product image from GCS bucket with browser and backend memory caching.
    """
    import urllib.request
    import urllib.parse
    import urllib.error

    # 1. Check in-memory cache first to eliminate GCS API calls
    if product_id in image_cache:
        img_bytes = image_cache[product_id]
        media_type = "image/webp" if img_bytes.startswith(b"RIFF") else "image/png"
        return Response(
            content=img_bytes, 
            media_type=media_type,
            headers={"Cache-Control": "public, max-age=2592000, immutable"}
        )

    # 1.5. Check container local disk output_images directory
    local_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output_images", f"{product_id}.png")
    if os.path.exists(local_path):
        try:
            with open(local_path, "rb") as f:
                img_bytes = f.read()
            image_cache[product_id] = img_bytes
            media_type = "image/webp" if img_bytes.startswith(b"RIFF") else "image/png"
            return Response(
                content=img_bytes, 
                media_type=media_type,
                headers={"Cache-Control": "public, max-age=2592000, immutable"}
            )
        except Exception as local_err:
            logger.warning(f"Failed to read local image {local_path}: {local_err}")

    try:
        token = auth_svc.get_token()
        bucket_name = settings.gcs_bucket_name
        object_name = f"products/{product_id}.png"
        
        # URL encode the object path to build standard REST API endpoint
        encoded_object = urllib.parse.quote(object_name, safe='')
        url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o/{encoded_object}?alt=media"
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        
        req = urllib.request.Request(url, headers=headers)
        
        # Run blocking network call inside standard thread pool to prevent event loop blocking
        def perform_request():
            with urllib.request.urlopen(req) as response:
                return response.read()
                
        img_bytes = await asyncio.to_thread(perform_request)
        
        # 2. Store in cache for subsequent requests
        image_cache[product_id] = img_bytes
        
        media_type = "image/webp" if img_bytes.startswith(b"RIFF") else "image/png"
        return Response(
            content=img_bytes, 
            media_type=media_type,
            headers={"Cache-Control": "public, max-age=2592000, immutable"}
        )
    except Exception as e:
        logger.warning(f"Error fetching product image from GCS for {product_id}: {e}")
        placeholder_svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="140" height="140" viewBox="0 0 24 24" fill="none" stroke="#ccc" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" style="background-color:#f5f5f5;border-radius:8px;">'
            '<rect x="3" y="3" width="18" height="18" rx="2" ry="2" fill="#fafafa"/>'
            '<circle cx="8.5" cy="8.5" r="1.5"/>'
            '<polyline points="21 15 16 10 5 21"/>'
            '<text x="50%" y="85%" font-family="sans-serif" font-size="3px" fill="#888" text-anchor="middle">No Image</text>'
            '</svg>'
        )
        return Response(content=placeholder_svg, media_type="image/svg+xml")


@router.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """
    Returns the details of a single product.
    """
    try:
        product = db.get_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        return product
    except Exception as e:
        logger.error(f"Error fetching product {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class ReviewCreate(BaseModel):
    customer_name: str = Field(..., min_length=1, max_length=255)
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field("", max_length=5000)


@router.get("/api/products/{product_id}/reviews")
async def get_product_reviews(product_id: str):
    """
    Returns a list of reviews for the product.
    """
    try:
        reviews = db.get_reviews(product_id)
        return reviews
    except Exception as e:
        logger.error(f"Error fetching reviews for {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api/products/{product_id}/reviews")
async def create_product_review(product_id: str, review: ReviewCreate):
    """
    Submits a new review for the product.
    """
    try:
        new_review = db.add_review(
            product_id=product_id,
            customer_name=review.customer_name,
            rating=review.rating,
            comment=review.comment
        )
        return new_review
    except ValueError as val_err:
        raise HTTPException(status_code=400, detail=str(val_err))
    except Exception as e:
        logger.error(f"Error creating review for {product_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
