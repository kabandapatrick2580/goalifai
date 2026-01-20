from flask import request, jsonify, Blueprint, current_app
from app.models.client.users_model import User
from app import db, jwt
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity, create_refresh_token, set_refresh_cookies
from flask import make_response
from datetime import datetime, timedelta
import traceback
import os
from app.models.central.central import Currency
user_access_bp = Blueprint('user_access_api', __name__, url_prefix='/api/v1/auth')

@user_access_bp.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()
        required_fields = ['email', 'user_password', 'first_name', 'last_name', 'country_of_residence', 'currency']
        password = data['user_password']

        if not password:
            return jsonify({"status": "error", "message": "'password' is required"}), 400

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "message": f"'{field}' is required"}), 400
        
        # hash the password
        hashed_password = User.set_password(password)

        # Check if user exists
        existing_user = User.get_user_by_email(data['email'])
        if existing_user:
            current_app.logger.info(f"User with email {data['email']} already exists")
            return jsonify({"error": "User with this email already exists"}), 400

        # Create user
        user = User.create_user(
            email=data['email'],
            password=hashed_password,
            first_name=data['first_name'],
            last_name=data['last_name'],
            country_of_residence=data['country_of_residence'],
            currency=data['currency']
        )
        if user is None:
            current_app.logger.error(f"An error occurred while creating the user")
            return jsonify({"status": "error", "message": "An error occurred while creating the user"}), 500
        
        # Return response including user_id, created_at, etc.

        # Log success
        current_app.logger.info(f"User {data['email']} created successfully")
        return jsonify({
            "status": "success",
            "message": "User created successfully",
            "data": {
                "user_id": user.user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "country_of_residence": user.country_of_residence,
                "currency": user.currency,
                "created_at": user.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": user.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            }
        }), 201             

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
@user_access_bp.route('/login', methods=['POST'])
def login():
    try:

        if request.method == 'OPTIONS':
            # This is the preflight response
            response = make_response()
            response.headers.add("Access-Control-Allow-Origin", "https://www.goalifai.app")
            response.headers.add("Access-Control-Allow-Methods", "POST, OPTIONS")
            response.headers.add("Access-Control-Allow-Headers", "Content-Type")
            return response, 200
        

        data = request.get_json()
        email = data.get('email')
        if email:
            email = email.strip()
        password = data.get('password')
        cors_allowed_origins = os.getenv('CORS_ALLOWED_ORIGINS')
        current_app.logger.info(f"CORS_ALLOWED_ORIGINS: {cors_allowed_origins}")
        if not email or not password:
            return jsonify({"status": "error", "message": "'email' and 'password' are required"}), 400

        user = User.get_user_by_email(email)
        if user is None or not User.check_password(user, password):
            current_app.logger.info(f"Invalid login attempt for email {email}, password {password}")
            return jsonify({"status": "error", "message": "Invalid email or password"}), 401
        
        current_app.logger.info(f"User {email} authenticated successfully")
        # Create JWT token
        access_token = create_access_token(identity=str(user.user_id))
        refresh_token = create_refresh_token(identity=str(user.user_id))
        
        try:
            # hash refresh token in the database
            hashed_refresh_token = User.set_password(refresh_token)
            # save hashed refresh token to the user record
            save_refresh_token = User.set_refresh_token(user.user_id, refresh_token)
        except Exception as e:
            current_app.logger.error(f"An error occurred while saving refresh token: {str(e)}")
            return jsonify({"status": "error", "message": "An error occurred while processing login"}), 500

        currency = Currency.get_currency_by_code(user.currency)
        default_currency = currency.id
        response = jsonify({
            "status": "success", 
            "message": "Login successful", 
            "access_token": access_token,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
            "user_id": user.user_id,
            "currency_id": str(default_currency),
            "timeout": os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 900) #15 minutes
        })
        set_refresh_cookies(response, refresh_token) # Set the refresh token in a secure HttpOnly cookie

        current_app.logger.info(f"User {email} logged in successfully")
        current_app.logger.info(f"Response data: {response.get_json()}")
        current_app.logger.info(f"Response headers: {response.headers}")
        return response, 200

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
    

@user_access_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    try:
        current_user_id = get_jwt_identity()
        user = User.get_user_by_id(current_user_id)
        if user is None:
            return jsonify({"status": "error", "message": "User not found"}), 404

        # Get existing refresh token from db
        existing_hashed_token = user.refresh_token_hash
        
        if existing_hashed_token is None or user.check_password(user, request.cookies.get('refresh_token_cookie')) is False:
            return jsonify({"status": "error", "message": "No refresh token found, please log in again"}), 401  
        # Create new access token
        new_access_token = create_access_token(identity=str(user.user_id))
        response = jsonify({"status": "success", "message": "Token refreshed successfully", "access_token": new_access_token})
        return response, 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@user_access_bp.route('/logout', methods=['POST'])
def logout():
    try:
        response = jsonify({"status": "success", "message": "Logout successful"})
        # Clear the refresh token cookie
        response.set_cookie('refresh_token_cookie', '', expires=0, httponly=True, secure=True if os.getenv('FLASK_ENV') == 'production' else False, samesite='Lax')
        return response, 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500