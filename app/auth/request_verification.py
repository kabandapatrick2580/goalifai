from itsdangerous import URLSafeTimedSerializer
from flask import current_app

def generate_token(email):
    s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return s.dumps(email)
