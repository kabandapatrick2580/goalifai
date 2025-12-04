from flask import redirect, render_template, request, jsonify, Blueprint, current_app
from app.models.client.users_model import User, WaitlistUser as Waitlist
from datetime import datetime
import traceback
import re
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from app import redis_client
from app.utils.rate_limiter import rate_limiter
from app.helpers.send_email import send_email


user_blueprint = Blueprint('user_api', __name__, url_prefix='/api/v1/users')
@user_blueprint.route('/create', methods=['POST'])
def create_user():
    try:
        data = request.get_json()
        required_fields = ['email', 'password', 'first_name', 'last_name', 'country_of_residence', 'currency']

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' is required"}), 400

        # Check if user exists
        existing_user = User.get_user_by_email(data['email'])
        if existing_user:
            current_app.logger.info(f"User with email {data['email']} already exists")
            return jsonify({"error": "User with this email already exists"}), 400

        # Create user
        user = User.create_user(
            email=data['email'],
            password=data['password'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            country_of_residence=data['country_of_residence'],
            currency=data['currency']
        )
        if user is None:
            current_app.logger.error(f"An error occurred while creating the user")
            return jsonify({"error": "An error occurred while creating the user"}), 500

        # Log success
        current_app.logger.info(f"User {data['email']} created successfully")

        # Return response including user_id, created_at, etc.
        return jsonify({
            "user_id": str(user.user_id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "country_of_residence": user.country_of_residence,
            "currency": user.currency,
            "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            "updated_at": user.updated_at.strftime("%Y-%m-%d %H:%M:%S")
        }), 201

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500




"""List of all users"""
@user_blueprint.route('/list', methods=['GET'])
def users_list():
    try:
        users = User.get_all_users()
        if not users:
            return jsonify({"error": "No users found"}), 404

        users_list = []
        for user in users:
            users_list.append({
                "user_id": str(user.user_id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "date_of_birth": user.date_of_birth.strftime("%Y-%m-%d") if user.date_of_birth else None,
                "country_of_residence": user.country_of_residence,
                "currency": user.currency,
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": user.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
            })

        return jsonify(
            response = {
                "status": "success",
                "count": len(users_list),        
                "data": users_list,              
                "message": "Users retrieved successfully"
            }
        ), 200

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify(
            {
                "status": "error",
                "message": "User retrieval failed"
            }), 500

"""update user info"""
@user_blueprint.route('/update/<uuid:user_id>', methods=['PUT'])
def update_user(user_id):
    try:
        data = request.get_json()
        user = User.update_user(user_id, **data)
        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify(
            {
                "status": "success",
                "message": "User updated successfully"
            }
        ), 200

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@user_blueprint.route('/add_to_waitlist', methods=['POST'])
@rate_limiter(redis_client, limit=1, window=30, key_prefix="waitlist")
def add_to_waitlist():
    try:
        data = request.get_json() or {}
        email = data.get("email", "").strip().lower()

        # 1️⃣ Validate email presence
        if not email:
            return jsonify({"status": "error", "message": "'email' is required"}), 400

        # 2️⃣ Validate email format
        email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
        if not re.match(email_regex, email):
            return jsonify({"status": "error", "message": "Invalid email format"}), 400

        # 3️⃣ Redis rate limit (1 request / 30 sec)
        rate_key = f"rate:waitlist:{email}"
        if redis_client.get(rate_key):
            return jsonify({"status": "error", "message": "Too many requests. Please wait before retrying."}), 429
        redis_client.setex(rate_key, 30, "1")

        # 4️⃣ Prevent duplicates
        existing_user = Waitlist.get_waitlist_user_by_email(email)
        if existing_user:
            current_app.logger.info(f"Email {email} already in waitlist")
            return jsonify({"status": "error", "message": "User with this email already exists"}), 400

        # 5️⃣ Generate verification token
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        token = s.dumps(email)

        # Store in Redis for 15 min (until user verifies)
        redis_client.setex(f"verify:{token}", 900, email)

        # 6️⃣ Send verification email
        verify_url = f"{current_app.config['FRONTEND_URL']}/verify-email?token={token}"
        email_sent = send_verification_email(email, verify_url)

        if not email_sent:
            return jsonify({"status": "error", "message": "Failed to send verification email"}), 500

        current_app.logger.info(f"Verification email sent for waitlist: {email}")

        return jsonify({
            "status": "success",
            "message": "Verification email sent. You will be added to the waitlist after confirming your email."
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error adding to waitlist: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "Internal server error"}), 500
# Email sender stub
def send_verification_email(email, verify_url):
    subject = "Please verify your email address"
    html_content = render_template(
        "email/verify_email.html",
        verify_url=verify_url,
        email=email
    )
    success, message = send_email(email, subject, html_content)
    if not success:
        current_app.logger.error(f"Failed to send verification email: {message}")
        return False
    current_app.logger.info(f"Verification email sent to {email}")
    return True

@user_blueprint.route("/verify-email/<token>", methods=["GET"])
def verify_email_get(token):
    try:
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        try:
            email = s.loads(token, max_age=900)  # 15 min expiration
        except SignatureExpired:
            return redirect(f"{current_app.config['FRONTEND_URL']}/verify-email-result?status=expired")
        except BadSignature:
            return redirect(f"{current_app.config['FRONTEND_URL']}/verify-email-result?status=invalid")

        redis_key = f"verify:{token}"
        if not redis_client.get(redis_key):
            return redirect(f"{current_app.config['FRONTEND_URL']}/verify-email-result?status=used")

        # Prevent duplicates
        if Waitlist.get_waitlist_user_by_email(email):
            redis_client.delete(redis_key)
            return redirect(f"{current_app.config['FRONTEND_URL']}/verify-email-result?status=exists")

        # Add to waitlist
        user = Waitlist.add_to_waitlist(email)
        if not user:
            return redirect(f"{current_app.config['FRONTEND_URL']}/verify-email-result?status=error")

        # Remove token from Redis
        redis_client.delete(redis_key)
        current_app.logger.info(f"User added to waitlist after verification: {email}")

        return redirect(f"{current_app.config['FRONTEND_URL']}/verify-email-result?status=success")

    except Exception as e:
        current_app.logger.error(f"Error verifying email: {str(e)}")
        return redirect(f"{current_app.config['FRONTEND_URL']}/verify-email-result?status=error")