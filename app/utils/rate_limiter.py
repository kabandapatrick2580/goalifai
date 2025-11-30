# utils/rate_limiter.py

from functools import wraps
from flask import request, jsonify

def rate_limiter(redis_client, limit=5, window=60, key_prefix="rl"):
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
                    "error": "Too many requests. Slow down."
                }), 429

            return f(*args, **kwargs)
        return wrapper
    return decorator
# Example usage:
# @app.route('/some_endpoint')
# @rate_limiter(redis_client, limit=10, window=60)
# def some_endpoint():