from datetime import datetime, timedelta
import json
import time

import config
from dotenv import load_dotenv
import pandas as pd
from smolagents import CodeAgent, Tool
from vertex_model import VertexAIServerModel, WeaveVertexAIServerModel
import weave


class ProductSearchTool(Tool):
    """Search product catalog"""

    name = "product_search"
    description = "Search for product information in the catalog by name, category, or description"
    inputs = {
        "query": {
            "type": "string",
            "description": "Product search query (text to search for)",
        }
    }
    output_type = "string"

    def __init__(self):
        super().__init__()
        # Load sample product catalog
        self.products_df = pd.read_csv("data/products.csv")

    def forward(self, query: str) -> str:
        # Handle case where query might be passed as a dict (from error message)
        if isinstance(query, dict):
            if "category" in query:
                query = query["category"]
            elif "query" in query:
                query = query["query"]
            else:
                query = str(query)

        # Search through product database using string matching
        matches = self.products_df[
            self.products_df["name"].str.contains(query, case=False)
            | self.products_df["category"].str.contains(query, case=False)
            | self.products_df["description"].str.contains(query, case=False)
        ]

        if not matches.empty:
            # Return top 3 matches with more details
            results = []
            for _, product in matches.head(3).iterrows():
                results.append(
                    {
                        "product_id": product["product_id"],
                        "name": product["name"],
                        "category": product["category"],
                        "price": f"${product['price']:.2f}",
                        "stock": int(product["stock"]),
                        "description": product["description"],
                        "warranty": product["warranty"],
                        "return_period": f"{product['return_period']} days",
                    }
                )
            return json.dumps(results, indent=2)
        return json.dumps({"error": "Product not found"})


class OrderStatusTool(Tool):
    """Check order status"""

    name = "order_status"
    description = "Check the status of an order by order ID"
    inputs = {"order_id": {"type": "string", "description": "Order ID to look up"}}
    output_type = "string"

    def __init__(self):
        super().__init__()
        # Load sample orders data
        self.orders_df = pd.read_csv("data/orders.csv")
        self.products_df = pd.read_csv("data/products.csv")

    def forward(self, order_id: str) -> str:
        # Handle case where order_id might be passed as a dict
        if isinstance(order_id, dict):
            if "order_id" in order_id:
                order_id = order_id["order_id"]
            else:
                order_id = str(order_id)

        # Look up order in database
        order = self.orders_df[self.orders_df["order_id"] == order_id]
        if not order.empty:
            order_data = order.iloc[0].to_dict()

            # Add product information
            product_id = order_data.get("product_id")
            product = self.products_df[self.products_df["product_id"] == product_id]
            if not product.empty:
                product_data = product.iloc[0].to_dict()
                order_data["product_name"] = product_data.get("name", "Unknown Product")
                order_data["product_category"] = product_data.get(
                    "category", "Unknown Category"
                )
                order_data["product_price"] = f"${product_data.get('price', 0):.2f}"

            # Add delivery estimate for processing/shipped orders
            if order_data.get("status") in ["processing", "shipped"]:
                if pd.notna(order_data.get("estimated_delivery_date")):
                    order_data["delivery_estimate"] = order_data.get(
                        "estimated_delivery_date"
                    )

            # Add tracking info if available
            if pd.notna(order_data.get("tracking_number")):
                order_data["tracking_info"] = {
                    "number": order_data.get("tracking_number"),
                    "carrier": "Olist Logistics",
                    "tracking_url": f"https://tracking.olist.com/{order_data.get('tracking_number')}",
                }

            return json.dumps(order_data, indent=2)
        return json.dumps({"error": "Order not found"})


class CategoryBrowseTool(Tool):
    """Browse products by category"""

    name = "category_browse"
    description = "Browse products by category name"
    inputs = {"category": {"type": "string", "description": "Category name to browse"}}
    output_type = "string"

    def __init__(self):
        super().__init__()
        self.products_df = pd.read_csv("data/products.csv")

    def forward(self, category: str) -> str:
        # Handle case where category might be passed as a dict
        if isinstance(category, dict):
            if "category" in category:
                category = category["category"]
            else:
                category = str(category)

        # Find products in the specified category
        matches = self.products_df[
            self.products_df["category"].str.contains(category, case=False)
        ]

        if not matches.empty:
            # Get category name from the first match for consistent display
            actual_category = matches.iloc[0]["category"]

            # Return summary of products in this category
            result = {
                "category": actual_category,
                "product_count": len(matches),
                "price_range": f"${matches['price'].min():.2f} - ${matches['price'].max():.2f}",
                "top_products": [],
            }

            # Add top 5 products sorted by price
            for _, product in (
                matches.sort_values("price", ascending=False).head(5).iterrows()
            ):
                result["top_products"].append(
                    {
                        "product_id": product["product_id"],
                        "name": product["name"],
                        "price": f"${product['price']:.2f}",
                        "stock": int(product["stock"]),
                    }
                )

            return json.dumps(result, indent=2)
        return json.dumps({"error": "Category not found"})


class PriceCheckTool(Tool):
    """Check product price"""

    name = "price_check"
    description = "Check the price of a specific product by product ID"
    inputs = {
        "product_id": {"type": "string", "description": "Product ID to check price for"}
    }
    output_type = "string"

    def __init__(self):
        super().__init__()
        self.products_df = pd.read_csv("data/products.csv")

    def forward(self, product_id: str) -> str:
        # Handle case where product_id might be passed as a dict
        if isinstance(product_id, dict):
            if "product_id" in product_id:
                product_id = product_id["product_id"]
            else:
                product_id = str(product_id)

        product = self.products_df[self.products_df["product_id"] == product_id]
        if not product.empty:
            product_data = product.iloc[0]
            result = {
                "product_id": product_data["product_id"],
                "name": product_data["name"],
                "price": f"${product_data['price']:.2f}",
                "category": product_data["category"],
                "in_stock": product_data["stock"] > 0,
                "stock_count": int(product_data["stock"]),
            }
            return json.dumps(result, indent=2)
        return json.dumps({"error": "Product not found"})


class CustomerOrderHistoryTool(Tool):
    """Get customer order history"""

    name = "customer_order_history"
    description = "Get order history for a specific customer by customer ID"
    inputs = {
        "customer_id": {
            "type": "string",
            "description": "Customer ID to get order history for",
        }
    }
    output_type = "string"

    def __init__(self):
        super().__init__()
        self.orders_df = pd.read_csv("data/orders.csv")

    def forward(self, customer_id: str) -> str:
        # Handle case where customer_id might be passed as a dict
        if isinstance(customer_id, dict):
            if "customer_id" in customer_id:
                customer_id = customer_id["customer_id"]
            else:
                customer_id = str(customer_id)

        # Find all orders for this customer
        customer_orders = self.orders_df[self.orders_df["customer_id"] == customer_id]

        if not customer_orders.empty:
            result = {
                "customer_id": customer_id,
                "order_count": len(customer_orders),
                "recent_orders": [],
            }

            # Add the 5 most recent orders
            for _, order in (
                customer_orders.sort_values("order_date", ascending=False)
                .head(5)
                .iterrows()
            ):
                order_data = {
                    "order_id": order["order_id"],
                    "date": order["order_date"],
                    "status": order["status"],
                    "product_id": order["product_id"],
                }

                # Add delivery info if available
                if pd.notna(order["delivery_date"]):
                    order_data["delivery_date"] = order["delivery_date"]

                result["recent_orders"].append(order_data)

            return json.dumps(result, indent=2)
        return json.dumps({"error": "No orders found for this customer"})


def create_customer_support_agent(
    project_id: str = None,
    location: str = None,
    endpoint_id: str = None,
    model_id: str = "google/gemini-1.5-pro",
    use_weave: bool = True,
    temperature: float = 0.7,
    planning_interval: int = 1,
    max_steps: int = 3,
) -> CodeAgent:
    """Create a Gemini-powered customer support agent

    Args:
        project_id: GCP project ID (defaults to env var VERTEX_PROJECT_ID)
        location: GCP region (defaults to env var VERTEX_LOCATION or 'us-central1')
        endpoint_id: Vertex AI endpoint ID (defaults to env var VERTEX_ENDPOINT_ID)
        model_id: Model identifier (defaults to 'google/gemini-1.5-pro')
        use_weave: Whether to use Weave for model tracking (default: True)
        temperature: Model temperature (default: 0.7)
        planning_interval: Number of steps between planning (default: 1)
        max_steps: Maximum number of steps the agent can take (default: 3)
    Returns:
        A configured customer support agent
    """

    # Initialize Vertex AI model with Weave tracking if requested
    if use_weave:
        # Create model with Weave tracking
        model = WeaveVertexAIServerModel(
            model_id=model_id,
            project_id=project_id,
            location=location,
            endpoint_id=endpoint_id,
            temperature=temperature,
        )
    else:
        model = VertexAIServerModel(
            model_id=model_id,
            project_id=project_id,
            location=location,
            endpoint_id=endpoint_id,
            temperature=temperature,
        )

    # Create tools for the agent
    product_search_tool = ProductSearchTool()
    order_status_tool = OrderStatusTool()
    category_browse_tool = CategoryBrowseTool()
    price_check_tool = PriceCheckTool()
    customer_order_history_tool = CustomerOrderHistoryTool()

    # Define tools
    tools = [
        product_search_tool,
        order_status_tool,
        category_browse_tool,
        price_check_tool,
        customer_order_history_tool,
        # DuckDuckGoSearchTool()  # For general knowledge queries
    ]

    # Create agent with planning capabilities
    agent = CodeAgent(
        tools=tools,
        model=model,
        planning_interval=planning_interval,  # Enable planning every step
        max_steps=max_steps,  # Allow more steps for complex queries
        additional_authorized_imports=["numpy", "json"],
    )

    return agent


def load_realistic_datasets(
    products_path: str = "data/products.csv",
    orders_path: str = "data/orders.csv",
    overwrite: bool = True,
    language: str = "en",
):
    """Load realistic product and order datasets, creating them if they don't exist

    Args:
        products_path: Path to products CSV file
        orders_path: Path to orders CSV file
        overwrite: Whether to overwrite existing datasets (default: True)
        language: Language code to filter reviews by (default: 'en' for English)
    """
    import glob
    import os
    import random
    import re
    import zipfile

    import pandas as pd

    # Create data directory if it doesn't exist
    os.makedirs(os.path.dirname(products_path), exist_ok=True)

    # Check if datasets already exist and whether to overwrite
    if overwrite or not (os.path.exists(products_path) and os.path.exists(orders_path)):
        try:
            # Define paths
            kaggle_dataset = "mexwell/amazon-reviews-multi"
            dataset_dir = "data/amazon-reviews-multi"
            zip_path = f"{dataset_dir}.zip"

            # Create dataset directory if it doesn't exist
            os.makedirs(dataset_dir, exist_ok=True)

            # Download dataset using Kaggle API if needed
            print("Downloading Amazon Reviews Multi dataset from Kaggle...")

            try:
                from kaggle.api.kaggle_api_extended import KaggleApi

                # Initialize the Kaggle API
                api = KaggleApi()
                api.authenticate()

                # Download the dataset
                api.dataset_download_files(kaggle_dataset, path="data")
                print(f"Dataset URL: https://www.kaggle.com/datasets/{kaggle_dataset}")

                # Extract the zip file
                if os.path.exists(zip_path):
                    with zipfile.ZipFile(zip_path, "r") as zip_ref:
                        zip_ref.extractall("data")

                    # Remove the zip file after extraction
                    os.remove(zip_path)

                print("Dataset downloaded and extracted successfully.")
            except Exception as e:
                print(f"Error downloading dataset from Kaggle: {str(e)}")
                print(
                    "Make sure you have the Kaggle API credentials set up (~/.kaggle/kaggle.json)"
                )
                raise

            print(f"Loading Amazon Reviews Multi dataset (language: {language})...")

            # Find the train.csv file using glob pattern matching
            csv_files = glob.glob("data/**/train.csv", recursive=True)

            if not csv_files:
                raise FileNotFoundError(
                    "Could not find train.csv in the extracted dataset"
                )

            # Use the first matching CSV file
            csv_path = csv_files[0]
            print(f"Found dataset file: {csv_path}")

            # Load the dataset
            reviews_df = pd.read_csv(csv_path)

            # Filter by language
            if "language" in reviews_df.columns:
                reviews_df = reviews_df[reviews_df["language"] == language]
                print(f"Filtered to {len(reviews_df)} reviews in {language} language")

            # Limit to a reasonable number of reviews for processing
            if len(reviews_df) > 1000:
                reviews_df = reviews_df.sample(1000, random_state=42)
                print("Sampled 1000 reviews for processing")

            # Extract product information
            product_data = []

            # Group by product_id to aggregate information
            for product_id, group in reviews_df.groupby("product_id"):
                # Create a proper product name based on category and ID
                category = group["product_category"].iloc[0]

                # Clean up the category name for better readability
                clean_category = category.replace("_", " ").title()

                # Extract a short ID from the product_id
                short_id = product_id.split("_")[-1][-4:]

                # Create a descriptive product name
                product_name = f"{clean_category} Item {short_id}"

                # Calculate average star rating
                avg_rating = group["stars"].mean()

                # Extract price if available in the review text
                price = None
                for review in group["review_body"]:
                    price_match = re.search(r"\$(\d+\.?\d*)", review)
                    if price_match:
                        try:
                            price = float(price_match.group(1))
                            break
                        except:
                            continue

                # If no price found, generate a reasonable one based on rating
                if price is None:
                    price = round(20 + (avg_rating * 10) + random.uniform(-10, 30), 2)

                # Generate stock based on popularity (star rating)
                stock = int(max(5, 50 + (avg_rating * 20) + random.randint(-20, 40)))

                # Create a simple description
                description = (
                    f"Quality {clean_category.lower()} product with ID {short_id}."
                )

                # Add warranty and return period based on price
                if price > 100:
                    warranty = "2 year limited"
                    return_period = 30
                elif price > 50:
                    warranty = "1 year limited"
                    return_period = 14
                else:
                    warranty = "90 days"
                    return_period = 7

                product_data.append(
                    {
                        "product_id": product_id,
                        "name": product_name,
                        "category": category,
                        "price": price,
                        "stock": stock,
                        "description": description,
                        "warranty": warranty,
                        "return_period": return_period,
                    }
                )

            # Create products DataFrame
            products = pd.DataFrame(product_data)

            # Generate orders data
            # Extract customer IDs
            customer_data = reviews_df[["reviewer_id", "product_id"]].copy()
            customer_data.rename(columns={"reviewer_id": "customer_id"}, inplace=True)

            # Create orders from reviews (assuming each review corresponds to a purchase)
            orders_data = []

            for _, purchase in customer_data.iterrows():
                # Generate a random order date (since review_date isn't available)
                # Use a date from the last 6 months
                days_ago = random.randint(1, 180)
                order_date = (datetime.now() - timedelta(days=days_ago)).strftime(
                    "%Y-%m-%d"
                )

                # Randomly assign order status with a realistic distribution
                status_choice = random.random()

                if status_choice < 0.7:  # 70% delivered
                    status = "delivered"
                    delivery_date = (
                        datetime.strptime(order_date, "%Y-%m-%d")
                        + timedelta(days=random.randint(1, 7))
                    ).strftime("%Y-%m-%d")
                    tracking_number = f"TRK{random.randint(10000000, 99999999)}"
                    estimated_delivery_date = None
                elif status_choice < 0.85:  # 15% shipped
                    status = "shipped"
                    delivery_date = None
                    tracking_number = f"TRK{random.randint(10000000, 99999999)}"
                    estimated_delivery_date = (
                        datetime.strptime(order_date, "%Y-%m-%d")
                        + timedelta(days=random.randint(1, 7))
                    ).strftime("%Y-%m-%d")
                elif status_choice < 0.95:  # 10% processing
                    status = "processing"
                    delivery_date = None
                    tracking_number = None
                    estimated_delivery_date = (
                        datetime.strptime(order_date, "%Y-%m-%d")
                        + timedelta(days=random.randint(3, 10))
                    ).strftime("%Y-%m-%d")
                else:  # 5% cancelled
                    status = "cancelled"
                    delivery_date = None
                    tracking_number = None
                    estimated_delivery_date = None

                orders_data.append(
                    {
                        "order_id": f"OD{random.randint(100000, 999999)}",
                        "customer_id": purchase["customer_id"],
                        "product_id": purchase["product_id"],
                        "status": status,
                        "order_date": order_date,
                        "delivery_date": delivery_date,
                        "estimated_delivery_date": estimated_delivery_date,
                        "tracking_number": tracking_number,
                    }
                )

            # Create orders DataFrame
            orders = pd.DataFrame(orders_data)

            # Limit to a reasonable number of products and orders if needed
            if len(products) > 100:
                products = products.head(100)

            if len(orders) > 200:
                orders = orders.head(200)

            # Save to CSV files
            products.to_csv(products_path, index=False)
            orders.to_csv(orders_path, index=False)

            print(
                f"Created product ({len(products)} items) and order ({len(orders)} orders) datasets from Amazon Reviews Multi data"
            )

        except Exception as e:
            print(f"Error loading dataset from Kaggle: {str(e)}")
            raise  # Raise the exception instead of falling back to a simpler dataset
    else:
        print(f"Using existing datasets at {products_path} and {orders_path}")


@weave.op()
def main():
    """
    Run the customer support agent with both Gemini and DeepSeek models
    for demonstration and testing purposes.
    """
    # Ensure we have realistic datasets (overwrite=False to keep existing datasets)
    load_realistic_datasets(language="en")

    # Common test queries to demonstrate agent capabilities
    test_queries = [
        "Best item in the category of book?",
    ]

    # Run with Gemini model
    print("\n" + "=" * 50)
    print("RUNNING CUSTOMER SUPPORT AGENT WITH GEMINI MODEL")
    print("=" * 50)

    gemini_agent = create_customer_support_agent(
        model_id="google/gemini-1.5-pro",
        use_weave=True,
        temperature=0.2,  # Lower temperature for more consistent responses
    )

    for i, query in enumerate(test_queries):
        print(f"\nQuery {i+1}: {query}")
        print("-" * 40)

        # Use the correct method to interact with the agent
        response = gemini_agent.run(query)
        print(f"Response: {response}")
        time.sleep(1)  # Brief pause between queries


if __name__ == "__main__":
    load_dotenv()
    weave.init(config.WEAVE_PROJECT_NAME)
    main()
