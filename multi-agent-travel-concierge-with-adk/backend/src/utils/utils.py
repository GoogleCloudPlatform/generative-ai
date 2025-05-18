from hashlib import sha256
from json import dumps
from src.model.intent import Intent
from typing import List


def intents_to_json(intents: List[Intent]):
  """Converts BigQuery results to a JSON string."""
  dictionaries = [intent.to_dict() for intent in intents]
  return dumps(dictionaries, sort_keys=True)

def generate_hash(data):
  """Generates a SHA-256 hash of the input data."""
  hash_object = sha256(data.encode())
  return hash_object.hexdigest()