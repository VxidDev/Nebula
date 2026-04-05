import functools
import time # Import time module for timestamp

class Cache:
    """
    A simple in-memory cache with optional TTL (Time-To-Live).
    """
    def __init__(self):
        self._cache = {}

    def get(self, key):
        """
        Retrieve an item from the cache.
        Returns the value if not expired, else None.
        """
        item = self._cache.get(key)
        if item is None:
            return None

        value, expiry_timestamp = item
        if expiry_timestamp is not None and time.time() > expiry_timestamp:
            self.delete(key) # Delete expired item
            return None
        return value

    def set(self, key, value, ttl=None):
        """
        Store an item in the cache with an optional TTL.
        `ttl` is in seconds. If None, the item does not expire.
        """
        expiry_timestamp = time.time() + ttl if ttl is not None else None
        self._cache[key] = (value, expiry_timestamp)

    def clear(self):
        """
        Clear all items from the cache.
        """
        self._cache.clear()

    def delete(self, key):
        """
        Delete a specific item from the cache.
        """
        if key in self._cache:
            del self._cache[key]

cache = Cache()

def cached(ttl=None):
    """
    A decorator to cache the results of a function.
    The cache key is generated from the function's arguments.
    
    Args:
        ttl (int, optional): Time-To-Live in seconds. If None, cache never expires.
                             Defaults to None.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from the function's name and its arguments
            key_parts = [func.__module__, func.__name__]
            key_parts.extend(str(arg) for arg in args)
            key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
            cache_key = ":".join(key_parts)

            result = cache.get(cache_key)
            if result is not None:
                return result
            
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)
            return result
        return wrapper
    return decorator
