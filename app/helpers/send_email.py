#from sendgrid import SendGridAPIClient
#from sendgrid.helpers.mail import Mail, To, Email
import os
import re
#from flask import logging, request
import requests
import logging
from dotenv import load_dotenv
from flask import current_app
load_dotenv()

def send_email(to_email, subject, html_content):
    """Send an email using netpipo's email service."""
    service_url = os.getenv("NETPIPO_EMAIL_URL")
    current_app.logger.info(f"Service URL: {service_url}")
    
    if not service_url:
        current_app.logger.error("NETPIPO_EMAIL_URL is not set in environment variables.")
        return False, "Missing email service URL"
    
    try:
        response = requests.post(
            service_url,
            json={
                'subject': subject,
                'recipients': to_email,
                'body': html_content
            }
        )
        current_app.logger.info(f"response: {response}")
        current_app.logger.info(f"response status code: {response.status_code}")
        
        if response.status_code == 200:
            current_app.logger.info(f"Email sent via API successfully to {to_email}.")
            return True, "Email sent successfully"
        else:
            message = f"Failed to send email. Status code: {response.status_code}, Response: {response.text}"
            current_app.logger.error(message)
            return False, message
    except requests.RequestException as e:
        message = f"An error occurred while sending email: {e}"
        current_app.logger.error(message)
        return False, message

