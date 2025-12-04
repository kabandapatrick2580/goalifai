# utils/rate_limiter.py

from functools import wraps
from flask import request, jsonify

def rate_limiter(redis_client, limit=5, window=10, key_prefix="rl"):
    """
    Docstring for rate_limiter
    
    :param redis_client: Redis client instance for storing request counts
    :param limit: Maximum number of requests allowed within the window
    :param window: Time window in seconds for rate limiting
    :param key_prefix: Prefix for Redis keys to avoid collisions
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            ip = request.remote_addr
            key = f"{key_prefix}:{ip}"

            current = redis_client.incr(key)

            if current == 1:
                redis_client.expire(key, window)

            if current > limit:
                return jsonify({
                    "message": f"Too many requests, please try after {window} seconds.",
                    "status": "error"
                }), 429

            return f(*args, **kwargs)
        return wrapper
    return decorator
# Example usage:
# @app.route('/some_endpoint')
# @rate_limiter(redis_client, limit=10, window=60)
# def some_endpoint():