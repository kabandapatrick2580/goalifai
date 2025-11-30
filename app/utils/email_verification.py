# utils/email_verification.py
import uuid
from flask import current_app, url_for
from datetime import timedelta

def generate_verification_token(redis_client, email, expire_seconds=600):
    """
    Generates a temporary token stored in Redis.
    """
    token = uuid.uuid4().hex
    key = f"verify:{token}"
    redis_client.setex(key, expire_seconds, email)
    return token


def send_verification_email(email, token):
    """
    Sends a verification email containing a link.
    Modify to match your email provider.
    """
    verify_url = url_for("user.verify_email", token=token, _external=True)

    subject = "Verify your email"
    body = f"Click this link to verify your email:\n\n{verify_url}"

    # Example using Flask-Mail
    mail = current_app.mail

    msg = mail.Message(
        subject=subject,
        recipients=[email],
        body=body
    )
    mail.send(msg)
    current_app.logger.info(f"Sent verification email to {email}")