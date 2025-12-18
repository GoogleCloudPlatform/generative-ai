"""Response Cache Manager - Efficient caching for Gemini responses.

Manage and cache API responses to reduce costs and improve performance.
"""

import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Optional, Any


class ResponseCache:
    """LRU cache manager for Gemini API responses."""

    def __init__(self, max_size: int = 100, ttl_hours: int = 24):
        """Initialize cache.

        Args:
            max_size: Maximum cache entries (default: 100).
            ttl_hours: Cache time-to-live in hours (default: 24).
        """
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.max_size = max_size
        self.ttl = timedelta(hours=ttl_hours)

    def _generate_key(self, prompt: str, model: str) -> str:
        """Generate cache key from prompt and model.

        Args:
            prompt: Input prompt.
            model: Model name.

        Returns:
            Hash-based cache key.
        """
        key_data = f"{model}:{prompt}"
        return hashlib.sha256(key_data.encode()).hexdigest()

    def get(self, prompt: str, model: str = 'gemini-pro') -> Optional[str]:
        """Retrieve cached response.

        Args:
            prompt: Input prompt.
            model: Model name.

        Returns:
            Cached response or None if not found/expired.
        """
        key = self._generate_key(prompt, model)
        if key not in self.cache:
            return None

        entry = self.cache[key]
        if datetime.now() - entry['timestamp'] > self.ttl:
            del self.cache[key]
            return None

        return entry['response']

    def set(self, prompt: str, response: str, model: str = 'gemini-pro') -> None:
        """Cache a response.

        Args:
            prompt: Input prompt.
            response: API response.
            model: Model name.
        """
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(),
                           key=lambda k: self.cache[k]['timestamp'])
            del self.cache[oldest_key]

        key = self._generate_key(prompt, model)
        self.cache[key] = {
            'response': response,
            'timestamp': datetime.now(),
        }

    def clear(self) -> None:
        """Clear all cache entries."""
        self.cache.clear()

    def get_size(self) -> int:
        """Get current cache size."""
        return len(self.cache)
