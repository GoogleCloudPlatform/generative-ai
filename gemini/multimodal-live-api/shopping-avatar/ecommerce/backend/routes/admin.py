import os
import sys
import json
import logging
import subprocess
import urllib.request
import urllib.parse
from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
from config import settings
from services import db, auth_svc

logger = logging.getLogger("ecommerce-routes-admin")
router = APIRouter()

class RetailerUpdate(BaseModel):
    retailer: str
    products_count: int = 15
    customers_count: int = 50
    orders_count: int = 100
    truncate_db: bool = False
    category: str = ""
    persona: str = "shopper"


# The .env file updates are removed as settings are now persisted dynamically in Spanner.

def run_seeding_task(retailer_name: str, products_count: int, customers_count: int, orders_count: int, category: str = ""):
    logger.info(f"Seeding catalog products for retailer '{retailer_name}' (products={products_count}, customers={customers_count}, orders={orders_count}, category={category}) in background...")
    try:
        cwd_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        scratch_dir = os.path.join(cwd_dir, "scratch")
        os.makedirs(scratch_dir, exist_ok=True)
        log_path = os.path.join(scratch_dir, "seeding_run.log")

        # Overwrite previous logs with a header line
        with open(log_path, "w") as log_file:
            log_file.write(f"=== Seeding process started for '{retailer_name}' ===\n")
            log_file.flush()

            # Execute generate_data.py and write stdout/stderr directly to file in real-time
            cmd = [
                sys.executable, "-u", "DataGenerator/generate_data.py", 
                "--products", str(products_count), 
                "--customers", str(customers_count), 
                "--orders", str(orders_count)
            ]
            if category:
                cmd.extend(["--category", category])
            
            env = os.environ.copy()
            env["RETAILER"] = retailer_name
            result = subprocess.run(
                cmd,
                cwd=cwd_dir,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                env=env
            )
            
            if result.returncode == 0:
                logger.info("Successfully finished background database seeding.")
                log_file.write("=== Seeding process finished successfully! ===\n")
            else:
                logger.error(f"Background database seeding failed with exit code: {result.returncode}")
                log_file.write(f"=== Seeding process failed with exit code: {result.returncode} ===\n")
    except Exception as e:
        logger.error(f"Failed to launch background seeding subprocess: {e}")

@router.post("/api/admin/retailer")
async def update_retailer(data: RetailerUpdate, background_tasks: BackgroundTasks):
    retailer_name = data.retailer.strip()
    if not retailer_name:
        return {"status": "error", "message": "Retailer name cannot be empty."}
        
    logger.info(f"Updating retailer config to '{retailer_name}', truncate_db={data.truncate_db}, products={data.products_count}, customers={data.customers_count}, orders={data.orders_count}")
    
    # 1. Update in-memory configuration settings
    settings.retailer = retailer_name
    
    # Clear backend in-memory product image cache to prevent serving old images
    try:
        from routes.products import image_cache
        image_cache.clear()
        logger.info("Cleared backend product image memory cache.")
    except Exception as e:
        logger.warning(f"Failed to clear image cache: {e}")
    
    # 2. Persist to .env file has been removed; we rely on Spanner singleton configuration row.
    
    # Save the brand theme to Spanner immediately
    try:
        from routes.config import fetch_dynamic_brand_theme
        theme = fetch_dynamic_brand_theme(retailer_name)
        theme["persona"] = data.persona
        db.save_retailer_settings(retailer_name, theme)
    except Exception as theme_err:
        logger.warning(f"Failed to pre-generate brand theme configuration: {theme_err}")
    
    # 3. Synchronously truncate tables if requested
    if data.truncate_db:
        try:
            db.truncate_tables()
            # Clear any stale status file
            scratch_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
            status_path = os.path.join(scratch_dir, "seeding_status.json")
            if os.path.exists(status_path):
                 os.remove(status_path)
            # Clear stale log file
            log_path = os.path.join(scratch_dir, "seeding_run.log")
            if os.path.exists(log_path):
                 os.remove(log_path)

            # Clear GCS bucket images and memory cache via REST API
            try:
                from routes.products import image_cache
                image_cache.clear()
                
                token = auth_svc.get_token()
                list_url = f"https://storage.googleapis.com/storage/v1/b/{settings.gcs_bucket_name}/o?prefix=products/"
                req = urllib.request.Request(list_url, headers={"Authorization": f"Bearer {token}"})
                res_data = json.loads(urllib.request.urlopen(req).read().decode('utf-8'))
                items = res_data.get('items', [])
                for item in items:
                    try:
                        enc_name = urllib.parse.quote(item['name'], safe='')
                        del_url = f"https://storage.googleapis.com/storage/v1/b/{settings.gcs_bucket_name}/o/{enc_name}"
                        del_req = urllib.request.Request(del_url, headers={"Authorization": f"Bearer {token}"}, method="DELETE")
                        urllib.request.urlopen(del_req)
                    except Exception:
                        pass
                logger.info(f"Deleted {len(items)} product images from GCS bucket '{settings.gcs_bucket_name}' via REST API.")
            except Exception as gcs_err:
                logger.warning(f"Failed to delete blobs from GCS via REST API: {gcs_err}")

            # Clear local output_images directory
            try:
                root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                output_dir = os.path.join(root_dir, "output_images")
                if os.path.exists(output_dir):
                    for f in os.listdir(output_dir):
                        if f.endswith(".png") or f.endswith(".webp"):
                            try:
                                os.remove(os.path.join(output_dir, f))
                            except Exception:
                                pass
            except Exception as img_err:
                logger.warning(f"Failed to clear local output_images: {img_err}")
        except Exception as e:
            logger.error(f"Failed to truncate Spanner database: {e}")
            return {"status": "error", "message": f"Failed to truncate database: {str(e)}"}
    
    # 4. Trigger seeding task in the background
    background_tasks.add_task(
        run_seeding_task, 
        retailer_name, 
        data.products_count, 
        data.customers_count,
        data.orders_count,
        data.category
    )
    
    return {
        "status": "success", 
        "message": f"Active retailer updated to '{retailer_name}'. Database operations are executing in the background."
    }

@router.get("/api/admin/status")
async def get_status():
    scratch_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
    status_path = os.path.join(scratch_dir, "seeding_status.json")
    if os.path.exists(status_path):
        try:
            with open(status_path, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read seeding_status.json: {e}")
            return {"is_running": False, "message": "Failed to read seeding progress."}
    return {"is_running": False, "message": "Idle"}

@router.get("/api/admin/logs")
async def get_logs():
    scratch_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scratch")
    log_path = os.path.join(scratch_dir, "seeding_run.log")
    if os.path.exists(log_path):
        try:
            with open(log_path, "r") as f:
                lines = f.readlines()
            return {"logs": lines[-40:]} # Return last 40 lines of shell logs
        except Exception as e:
            logger.error(f"Failed to read seeding_run.log: {e}")
            return {"logs": [f"Error reading log file: {str(e)}"]}
    return {"logs": ["No logging output generated yet."]}
