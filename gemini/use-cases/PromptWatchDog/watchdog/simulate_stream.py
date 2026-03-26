import argparse
import base64
import json
import os
import sys
import time
from unittest.mock import patch

from dotenv import load_dotenv
from google.cloud import pubsub_v1

# Add current directory to path to import main safely
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from main import subscribe

# Load environment variables
load_dotenv()

# 1. Define the Conversation Stream
conversation = [
    {"sender": "Alice", "text": "Hey, are you watching the Champions League tonight?"},
    {
        "sender": "Bob",
        "text": "Yes! Real Madrid is playing really well, that attack was fast.",
    },
    {"sender": "Alice", "text": "That pass by Vinicius was incredible. Pure class."},
    {"sender": "Bob", "text": "Agreed. I think they might win the cup this year."},
    {
        "sender": "Alice",
        "text": "By the way, let's order some pizza for the second half.",
    },
    {"sender": "Bob", "text": "Good idea, pepperoni for me."},
]


def publish_cloud():
    PROJECT_ID = os.getenv("GCP_PROJECT")
    TOPIC_ID = os.getenv("PUB_SUB_TOPIC", "messages")

    if not PROJECT_ID:
        print("Error: GCP_PROJECT is not set in your .env file")
        exit(1)

    # Initialize Pub/Sub Publisher Client
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

    print(f"=== Starting Real Publish Stream to {topic_path} ===\n")

    for i, msg in enumerate(conversation):
        print(f"\n[Message {i+1}/{len(conversation)}] From {msg['sender']}: '{msg['text']}'")
        print(f" -> Sending Payload: {json.dumps(msg)}")

        # Encode message as JSON string
        msg_str = json.dumps(msg)
        data = msg_str.encode("utf-8")

        # Publish to the real Cloud Pub/Sub
        try:
            future = publisher.publish(topic_path, data)
            message_id = future.result()
            print(f" -> Successfully published message ID: {message_id}\n")
        except Exception as e:
            print(f" -> Failed to publish message: {e}\n")

        # Wait between messages to simulate a real conversation flow
        time.sleep(1.5)


def simulate_local():
    print("=== Starting Local Conversation Stream Simulation ===\n")

    # Mock Active Prompts (Simulating what lives in Firestore for local execution)
    mock_prompts = [
        {
            "id": "soccer_detector_001",
            "name": "Soccer Match Detector",
            "content": "You are an assistant detecting content. Evaluate if the following message is discussing a soccer/football match, players, scores, or game events. Text: {text}",
        }
    ]

    # Mocking Firestore to avoid database mutations and use controlled test data locally
    with patch("main.fetch_active_prompts_from_firestore", return_value=mock_prompts):
        for i, msg in enumerate(conversation):
            print(f"\n[Message {i+1}/{len(conversation)}] From {msg['sender']}: '{msg['text']}'")
            print(f" -> Created Mock Event with Payload: {json.dumps(msg)}")

            # 1. Encode message as JSON to match what PubSub receives
            msg_str = json.dumps(msg)
            b64_data = base64.b64encode(msg_str.encode("utf-8")).decode("utf-8")

            # 2. Create Mock CloudEvent
            class MockCloudEvent:
                def __init__(self, data):
                    self.data = data

            event = MockCloudEvent({"message": {"data": b64_data}})

            # 3. Trigger Watchdog locally
            print(" -> Triggering Watchdog evaluation flow:")
            subscribe(event)
            print("-" * 40 + "\n")
            time.sleep(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate the PromptWatchDog stream.")
    parser.add_argument(
        "--cloud",
        action="store_true",
        help="If set, pushes messages to actual Cloud Pub/Sub topic. Otherwise runs entirely local.",
    )
    args = parser.parse_args()

    if args.cloud:
        publish_cloud()
    else:
        simulate_local()
