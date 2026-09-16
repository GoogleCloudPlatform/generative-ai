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

from google.cloud import spanner
import uuid
import logging
from decimal import Decimal
import json

logger = logging.getLogger("ecommerce-db")

class SpannerDatabase:
    def __init__(self, instance_id: str, database_id: str, project_id: str):
        self.client = spanner.Client(project=project_id)
        self.instance = self.client.instance(instance_id)
        self.db = self.instance.database(database_id)

    def search_products(self, query_vector: list[float], limit: int = 5, min_price: float = None, max_price: float = None, threshold: float = 0.45) -> list[dict]:
        """
        Retrieves products matching the semantic search query vector using cosine distance
        and optional price bounds, filtered by a maximum distance threshold.
        """
        query = """
            SELECT p.product_id, p.name, p.description, p.price, p.inventory_level, p.image_url,
                   COSINE_DISTANCE(p.embedding, @query_vector) AS distance,
                   COALESCE((SELECT AVG(r.rating) FROM reviews r WHERE r.product_id = p.product_id), 0.0) AS avg_rating,
                   COALESCE((SELECT COUNT(1) FROM reviews r WHERE r.product_id = p.product_id), 0) AS reviews_count
            FROM products p
            WHERE p.inventory_level > 0
              AND COSINE_DISTANCE(p.embedding, @query_vector) <= @threshold
              AND (@min_price IS NULL OR p.price >= @min_price)
              AND (@max_price IS NULL OR p.price <= @max_price)
            ORDER BY distance ASC
            LIMIT @limit
        """
        
        results = []
        with self.db.snapshot() as snapshot:
            query_params = {
                "query_vector": query_vector,
                "limit": limit,
                "min_price": Decimal(str(min_price)) if min_price is not None else None,
                "max_price": Decimal(str(max_price)) if max_price is not None else None,
                "threshold": threshold
            }
            param_types = {
                "query_vector": spanner.param_types.Array(spanner.param_types.FLOAT32),
                "limit": spanner.param_types.INT64,
                "min_price": spanner.param_types.NUMERIC,
                "max_price": spanner.param_types.NUMERIC,
                "threshold": spanner.param_types.FLOAT64
            }
            
            result_set = snapshot.execute_sql(
                query,
                params=query_params,
                param_types=param_types
            )
            
            for row in result_set:
                results.append({
                    "product_id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "price": str(row[3]),
                    "inventory": row[4],
                    "image_url": f"/api/products/{row[0]}/image",
                    "score": 1 - row[6], # Reconstruct similarity score
                    "rating": float(row[7]) if row[7] is not None else 0.0,
                    "reviews_count": row[8]
                })
        return results

    def get_products(self, limit: int = 8, offset: int = 0) -> list[dict]:
        """
        Retrieves products from the database up to the specified limit starting from offset.
        """
        query = """
            SELECT p.product_id, p.name, p.description, p.price, p.inventory_level, p.image_url,
                   COALESCE((SELECT AVG(r.rating) FROM reviews r WHERE r.product_id = p.product_id), 0.0) AS avg_rating,
                   COALESCE((SELECT COUNT(1) FROM reviews r WHERE r.product_id = p.product_id), 0) AS reviews_count
            FROM products p
            WHERE p.inventory_level > 0
            ORDER BY p.product_id
            LIMIT @limit OFFSET @offset
        """
        results = []
        with self.db.snapshot() as snapshot:
            query_params = {
                "limit": limit,
                "offset": offset
            }
            param_types = {
                "limit": spanner.param_types.INT64,
                "offset": spanner.param_types.INT64
            }
            result_set = snapshot.execute_sql(
                query,
                params=query_params,
                param_types=param_types
            )
            for row in result_set:
                results.append({
                    "product_id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "price": str(row[3]),
                    "inventory": row[4],
                    "image_url": f"/api/products/{row[0]}/image",
                    "rating": float(row[6]) if row[6] is not None else 0.0,
                    "reviews_count": row[7]
                })
        return results

    def get_product(self, product_id: str) -> dict | None:
        """
        Retrieves a single product from the database by its product_id.
        """
        query = """
            SELECT p.product_id, p.name, p.description, p.price, p.inventory_level, p.image_url,
                   COALESCE((SELECT AVG(r.rating) FROM reviews r WHERE r.product_id = p.product_id), 0.0) AS avg_rating,
                   COALESCE((SELECT COUNT(1) FROM reviews r WHERE r.product_id = p.product_id), 0) AS reviews_count
            FROM products p
            WHERE p.product_id = @product_id
        """
        with self.db.snapshot() as snapshot:
            result_set = snapshot.execute_sql(
                query,
                params={"product_id": product_id},
                param_types={"product_id": spanner.param_types.STRING}
            )
            for row in result_set:
                return {
                    "product_id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "price": str(row[3]),
                    "inventory": row[4],
                    "image_url": f"/api/products/{row[0]}/image",
                    "rating": float(row[6]) if row[6] is not None else 0.0,
                    "reviews_count": row[7]
                }
        return None


    def add_to_cart(self, session_id: str, product_id: str, quantity: int) -> dict:
        """
        Adds a product to the ephemeral cart table inside a Spanner transaction,
        asserting inventory sufficiency first.
        """
        def _add_to_cart_tx(transaction):
            # 1. Read inventory level
            row = transaction.execute_sql(
                "SELECT name, inventory_level, price FROM products WHERE product_id = @id",
                params={"id": product_id},
                param_types={"id": spanner.param_types.STRING}
            ).one()
            
            product_name, inventory, price = row[0], row[1], row[2]
            
            if inventory < quantity:
                raise ValueError(f"Insufficient stock for {product_name}. Available: {inventory}, Requested: {quantity}")
            
            # 2. Check if item already in cart
            cart_rows = list(transaction.execute_sql(
                "SELECT quantity FROM shopping_carts WHERE session_id = @session AND product_id = @product",
                params={"session": session_id, "product": product_id},
                param_types={"session": spanner.param_types.STRING, "product": spanner.param_types.STRING}
            ))
            
            new_quantity = quantity
            if cart_rows:
                new_quantity += cart_rows[0][0]
                
            if inventory < new_quantity:
                 raise ValueError(f"Adding this item exceeds available stock ({inventory}). Cart has: {cart_rows[0][0]}")

            # 3. Upsert cart using DML
            if cart_rows:
                transaction.execute_update(
                    "UPDATE shopping_carts SET quantity = @qty, updated_at = PENDING_COMMIT_TIMESTAMP() WHERE session_id = @session AND product_id = @product",
                    params={"qty": new_quantity, "session": session_id, "product": product_id},
                    param_types={"qty": spanner.param_types.INT64, "session": spanner.param_types.STRING, "product": spanner.param_types.STRING}
                )
            else:
                transaction.execute_update(
                    "INSERT INTO shopping_carts (session_id, product_id, quantity, updated_at) VALUES (@session, @product, @qty, PENDING_COMMIT_TIMESTAMP())",
                    params={"session": session_id, "product": product_id, "qty": new_quantity},
                    param_types={"session": spanner.param_types.STRING, "product": spanner.param_types.STRING, "qty": spanner.param_types.INT64}
                )
            
            return {
                "items": self._get_cart_items_tx(transaction, session_id),
                "last_action": {
                    "type": "add",
                    "product_id": product_id,
                    "name": product_name,
                    "quantity": quantity,
                    "price": str(price)
                }
            }

        return self.db.run_in_transaction(_add_to_cart_tx)

    def _get_cart_items_tx(self, transaction, session_id: str) -> list:
        cart_rows = list(transaction.execute_sql(
            """
            SELECT c.product_id, c.quantity, p.name, p.price
            FROM shopping_carts c
            JOIN products p ON c.product_id = p.product_id
            WHERE c.session_id = @session
            """,
            params={"session": session_id},
            param_types={"session": spanner.param_types.STRING}
        ))
        return [
            {
                "product_id": r[0],
                "quantity": r[1],
                "name": r[2],
                "price": str(r[3])
            }
            for r in cart_rows
        ]

    def get_cart_items(self, session_id: str) -> list:
        with self.db.snapshot() as snapshot:
            return self._get_cart_items_tx(snapshot, session_id)

    def checkout_cart(self, session_id: str, customer_id: str) -> dict:
        """
        Converts the active cart items into a finalized order, decrements inventories,
        and cleans up the cart in a single atomic transaction.
        """
        def _checkout_tx(transaction):
            # 1. Read cart items and joining product specs
            cart_items = list(transaction.execute_sql(
                """
                SELECT c.product_id, c.quantity, p.price, p.inventory_level, p.name 
                FROM shopping_carts c
                JOIN products p ON c.product_id = p.product_id
                WHERE c.session_id = @session
                """,
                params={"session": session_id},
                param_types={"session": spanner.param_types.STRING}
            ))
            
            if not cart_items:
                raise ValueError("Shopping cart is empty.")
                
            order_id = f"ORD-{uuid.uuid4().hex[:10].upper()}"
            total_amount = 0
            order_lines = []
            
            for item in cart_items:
                product_id, quantity, price, inventory, name = item[0], item[1], item[2], item[3], item[4]
                
                if inventory < quantity:
                    raise ValueError(f"Stock for '{name}' fell to {inventory}. Cannot complete checkout.")
                
                # Decrement product inventory
                transaction.execute_update(
                    "UPDATE products SET inventory_level = inventory_level - @qty WHERE product_id = @id",
                    params={"qty": quantity, "id": product_id},
                    param_types={"qty": spanner.param_types.INT64, "id": spanner.param_types.STRING}
                )
                
                line_total = price * quantity
                total_amount += line_total
                
                order_lines.append({
                    "product_id": product_id,
                    "quantity": quantity,
                    "unit_price": price
                })

            # Create Order header
            transaction.execute_update(
                """
                INSERT INTO orders (order_id, customer_id, total_amount, created_at)
                VALUES (@order, @customer, @total, PENDING_COMMIT_TIMESTAMP())
                """,
                params={"order": order_id, "customer": customer_id, "total": total_amount},
                param_types={"order": spanner.param_types.STRING, "customer": spanner.param_types.STRING, "total": spanner.param_types.NUMERIC}
            )
            
            # Create Order items
            for line in order_lines:
                transaction.execute_update(
                    """
                    INSERT INTO order_items (order_id, product_id, quantity, unit_price)
                    VALUES (@order, @product, @qty, @price)
                    """,
                    params={"order": order_id, "product": line["product_id"], "qty": line["quantity"], "price": line["unit_price"]},
                    param_types={"order": spanner.param_types.STRING, "product": spanner.param_types.STRING, "qty": spanner.param_types.INT64, "price": spanner.param_types.NUMERIC}
                )
                
            # Clear shopping cart
            transaction.execute_update(
                "DELETE FROM shopping_carts WHERE session_id = @session",
                params={"session": session_id},
                param_types={"session": spanner.param_types.STRING}
            )
            
            return {
                "order_id": order_id,
                "total_amount": str(total_amount),
                "items_count": len(order_lines)
            }

        return self.db.run_in_transaction(_checkout_tx)

    def update_cart_item(self, session_id: str, product_id: str, quantity: int) -> dict:
        """
        Updates the quantity of a product in the cart to a specific value.
        If quantity is <= 0, the item is removed.
        Asserts inventory sufficiency first.
        """
        if quantity <= 0:
            return self.remove_from_cart(session_id, product_id)

        def _update_cart_tx(transaction):
            # 1. Read inventory level
            row = transaction.execute_sql(
                "SELECT name, inventory_level, price FROM products WHERE product_id = @id",
                params={"id": product_id},
                param_types={"id": spanner.param_types.STRING}
            ).one()
            
            product_name, inventory, price = row[0], row[1], row[2]
            
            if inventory < quantity:
                raise ValueError(f"Cannot update quantity to {quantity}. Only {inventory} in stock for {product_name}.")
            
            # 2. Check if item already in cart
            cart_rows = list(transaction.execute_sql(
                "SELECT quantity FROM shopping_carts WHERE session_id = @session AND product_id = @product",
                params={"session": session_id, "product": product_id},
                param_types={"session": spanner.param_types.STRING, "product": spanner.param_types.STRING}
            ))

            # 3. Update cart using DML
            if cart_rows:
                transaction.execute_update(
                    "UPDATE shopping_carts SET quantity = @qty, updated_at = PENDING_COMMIT_TIMESTAMP() WHERE session_id = @session AND product_id = @product",
                    params={"qty": quantity, "session": session_id, "product": product_id},
                    param_types={"qty": spanner.param_types.INT64, "session": spanner.param_types.STRING, "product": spanner.param_types.STRING}
                )
            else:
                transaction.execute_update(
                    "INSERT INTO shopping_carts (session_id, product_id, quantity, updated_at) VALUES (@session, @product, @qty, PENDING_COMMIT_TIMESTAMP())",
                    params={"session": session_id, "product": product_id, "qty": quantity},
                    param_types={"session": spanner.param_types.STRING, "product": spanner.param_types.STRING, "qty": spanner.param_types.INT64}
                )
            
            # 4. Fetch the entire current cart list
            items = self._get_cart_items_tx(transaction, session_id)

            return {
                "items": items,
                "last_action": {
                    "type": "update",
                    "product_id": product_id,
                    "name": product_name,
                    "quantity": quantity,
                    "price": str(price)
                }
            }

        return self.db.run_in_transaction(_update_cart_tx)

    def remove_from_cart(self, session_id: str, product_id: str) -> dict:
        """
        Removes a product completely from the user's shopping cart.
        """
        def _remove_tx(transaction):
            row = list(transaction.execute_sql(
                "SELECT name FROM products WHERE product_id = @id",
                params={"id": product_id},
                param_types={"id": spanner.param_types.STRING}
            ))
            product_name = row[0][0] if row else "Unknown Product"

            transaction.execute_update(
                "DELETE FROM shopping_carts WHERE session_id = @session AND product_id = @product",
                params={"session": session_id, "product": product_id},
                param_types={"session": spanner.param_types.STRING, "product": spanner.param_types.STRING}
            )

            # Fetch the entire current cart list
            items = self._get_cart_items_tx(transaction, session_id)

            return {
                "items": items,
                "last_action": {
                    "type": "remove",
                    "product_id": product_id,
                    "name": product_name,
                    "removed": True
                }
            }

        return self.db.run_in_transaction(_remove_tx)

    def get_active_retailer_settings(self) -> dict:
        """
        Retrieves the active retailer configuration and theme from Spanner.
        """
        query = """
            SELECT retailer_name, theme_config, assistant_persona
            FROM retailer_settings
            WHERE config_id = 'active_config'
        """
        with self.db.snapshot() as snapshot:
            result_set = list(snapshot.execute_sql(query))
            if result_set:
                row = result_set[0]
                theme_val = row[1]
                persona_val = row[2]
                if isinstance(theme_val, str):
                    theme_config = json.loads(theme_val)
                else:
                    theme_config = theme_val
                
                # Retrieve persona from new column with fallback to nested JSON or default
                persona = persona_val or theme_config.get("persona", "shopper")
                
                return {
                    "name": row[0],
                    **theme_config,
                    "persona": persona
                }
        return None

    def save_retailer_settings(self, retailer_name: str, theme_config: dict) -> None:
        """
        Saves the active retailer configuration and theme to Spanner.
        """
        def _save_tx(transaction):
            theme_data = {
                "primary": theme_config.get("primary", "#1976d2"),
                "secondary": theme_config.get("secondary", "#ffffff"),
                "font": theme_config.get("font", "sans-serif")
            }
            persona = theme_config.get("persona", "shopper")
            transaction.insert_or_update(
                table='retailer_settings',
                columns=['config_id', 'retailer_name', 'theme_config', 'assistant_persona', 'updated_at'],
                values=[['active_config', retailer_name, json.dumps(theme_data), persona, spanner.COMMIT_TIMESTAMP]]
            )
        self.db.run_in_transaction(_save_tx)
        logger.info(f"Saved active retailer '{retailer_name}' settings to Spanner.")

    def get_reviews(self, product_id: str) -> list[dict]:
        """
        Retrieves reviews for a given product_id.
        """
        query = """
            SELECT review_id, customer_name, rating, comment, created_at
            FROM reviews
            WHERE product_id = @product_id
            ORDER BY created_at DESC
        """
        results = []
        with self.db.snapshot() as snapshot:
            result_set = snapshot.execute_sql(
                query,
                params={"product_id": product_id},
                param_types={"product_id": spanner.param_types.STRING}
            )
            for row in result_set:
                results.append({
                    "review_id": row[0],
                    "customer_name": row[1],
                    "rating": row[2],
                    "comment": row[3],
                    "created_at": row[4].isoformat() if row[4] else None
                })
        return results

    def add_review(self, product_id: str, customer_name: str, rating: int, comment: str) -> dict:
        """
        Adds a product review inside a transaction.
        """
        review_id = f"REV-{uuid.uuid4().hex[:10].upper()}"
        def _add_review_tx(transaction):
            # Assert product exists
            row = list(transaction.execute_sql(
                "SELECT name FROM products WHERE product_id = @id",
                params={"id": product_id},
                param_types={"id": spanner.param_types.STRING}
            ))
            if not row:
                raise ValueError(f"Product with id {product_id} does not exist.")

            transaction.execute_update(
                """
                INSERT INTO reviews (product_id, review_id, customer_name, rating, comment, created_at)
                VALUES (@product, @review, @name, @rating, @comment, PENDING_COMMIT_TIMESTAMP())
                """,
                params={
                    "product": product_id,
                    "review": review_id,
                    "name": customer_name,
                    "rating": rating,
                    "comment": comment
                },
                param_types={
                    "product": spanner.param_types.STRING,
                    "review": spanner.param_types.STRING,
                    "name": spanner.param_types.STRING,
                    "rating": spanner.param_types.INT64,
                    "comment": spanner.param_types.STRING
                }
            )
            return {
                "review_id": review_id,
                "product_id": product_id,
                "customer_name": customer_name,
                "rating": rating,
                "comment": comment
            }
        return self.db.run_in_transaction(_add_review_tx)

    def truncate_tables(self):
        """
        Clears all shopping cart, orders, order items, customers, reviews, and product data from Spanner.
        """
        def _truncate_tx(transaction):
            logger.info("De-seeding Spanner database tables (deleting records)...")
            transaction.execute_update("DELETE FROM shopping_carts WHERE TRUE")
            transaction.execute_update("DELETE FROM order_items WHERE TRUE")
            transaction.execute_update("DELETE FROM orders WHERE TRUE")
            transaction.execute_update("DELETE FROM reviews WHERE TRUE")
            transaction.execute_update("DELETE FROM customers WHERE TRUE")
            transaction.execute_update("DELETE FROM products WHERE TRUE")
        
        self.db.run_in_transaction(_truncate_tx)
        logger.info("Successfully truncated all database tables.")

