from flask import request, jsonify, Blueprint, current_app
from app.models.client.users_model import User
from app import db
from datetime import datetime
import traceback

user_blueprint = Blueprint('user_api', __name__)
@user_blueprint.route('/api/v1/users', methods=['POST'])
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
@user_blueprint.route('/api/v1/users', methods=['GET'])
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
                "updated_at": user.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })

        return jsonify(
            {
                "status": "success",
                "data": {
                    "users": users_list
                },
                "message": "Users retrieved successfully"
            }
        ), 200

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500