from typing import Dict, List, Any
from smolagents import (
    CodeAgent, 
    Tool, 
    DuckDuckGoSearchTool,
    Model,
    ChatMessage
)
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel
from dataset_generator import DatasetGenerator
from evaluator import AgentEvaluator
import json
import pandas as pd
from customer_support_agent import create_customer_support_agent

def setup_sample_data():
    """Create sample datasets for products and orders"""
    # Sample product data
    products = pd.DataFrame({
        'product_id': range(1, 11),
        'name': [
            'Dell XPS 13 Laptop', 'iPhone 15 Pro', 'Samsung Galaxy Tab S9',
            'Sony WH-1000XM5', 'Apple Watch Series 9', 'iPad Air 5',
            'Microsoft Surface Pro 9', 'AirPods Pro 2', 'Galaxy S24 Ultra',
            'MacBook Pro 16'
        ],
        'category': [
            'Laptops', 'Smartphones', 'Tablets', 'Headphones', 'Smartwatches',
            'Tablets', 'Laptops', 'Earbuds', 'Smartphones', 'Laptops'
        ],
        'price': [
            1299.99, 999.99, 699.99, 349.99, 399.99,
            599.99, 1099.99, 249.99, 1199.99, 2499.99
        ],
        'stock': [
            45, 100, 75, 200, 150,
            80, 60, 300, 90, 40
        ],
        'description': [
            '13-inch premium ultrabook with Intel Core i7',
            'Pro-grade smartphone with advanced camera system',
            'Premium Android tablet with S Pen support',
            'Industry-leading noise cancelling headphones',
            'Advanced health and fitness tracking smartwatch',
            'Powerful and portable iPad with M1 chip',
            'Versatile 2-in-1 laptop with Windows 11',
            'Premium wireless earbuds with active noise cancellation',
            'Flagship Android phone with S Pen',
            'Professional laptop with M3 Pro chip'
        ]
    })
    
    # Sample order data
    orders = pd.DataFrame({
        'order_id': [f'ORD{i:04d}' for i in range(1, 11)],
        'customer_id': range(1, 11),
        'product_id': [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        'status': [
            'Delivered', 'Shipped', 'Processing', 'Delivered', 'Shipped',
            'Processing', 'Cancelled', 'Delivered', 'Processing', 'Shipped'
        ],
        'order_date': [
            '2024-03-01', '2024-03-05', '2024-03-08', '2024-02-28', '2024-03-06',
            '2024-03-09', '2024-03-02', '2024-02-25', '2024-03-10', '2024-03-07'
        ],
        'delivery_date': [
            '2024-03-05', '2024-03-10', '2024-03-13', '2024-03-03', '2024-03-11',
            '2024-03-14', None, '2024-02-28', '2024-03-15', '2024-03-12'
        ]
    })
    
    # Save to CSV files
    products.to_csv('data/products.csv', index=False)
    orders.to_csv('data/orders.csv', index=False)

def main():
    # Setup sample data
    setup_sample_data()
    
    # Initialize dataset generator with Gemini agent
    project_id = "your-project-id"  # Replace with your GCP project ID
    location = "us-central1"        # Replace with your region
    
    # Create customer support agent
    agent = create_customer_support_agent(project_id, location)
    
    # Initialize dataset generator
    generator = DatasetGenerator(agent=agent)
    
    print("Generating customer support evaluation dataset...")
    
    # Generate dataset with customer support scenarios
    dataset = generator.generate_comprehensive_dataset(num_samples=10)
    
    # Save generated dataset
    generator.save_dataset(dataset, "customer_support_eval")
    
    print("Dataset generation complete!")
    
    # Run evaluations
    evaluator = AgentEvaluator()
    
    for eval_type, examples in dataset.items():
        print(f"\nEvaluating {eval_type}...")
        eval_dataset = evaluator.format_dataset_for_eval(examples)
        results = evaluator.run_evaluation(eval_dataset)
        
        # Save evaluation results
        with open(f"evaluation_results_{eval_type}.json", "w") as f:
            json.dump(results, f, indent=2)
        
        print(f"Summary metrics for {eval_type}:")
        for metric, score in results["summary_metrics"].items():
            print(f"- {metric}: {score:.3f}")

if __name__ == "__main__":
    main()