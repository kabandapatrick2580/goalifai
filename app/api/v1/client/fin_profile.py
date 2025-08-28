from flask import request, jsonify, Blueprint, current_app
from app.models.users_model import UserFinancialProfile
from app import db 
from datetime import datetime
import traceback 
from sqlalchemy.orm.exc import NoResultFound

fin_profile = Blueprint('financial_profile', __name__)

@fin_profile.route('/api/v1/financial_profile', methods=['POST'])
def create_profile():
    """API endpoint to create a financial profile."""
    data = request.get_json()
    user_id = data.get('user_id')
    expected_monthly_income = data.get('expected_monthly_income')
    expected_monthly_expenses = data.get('expected_monthly_expenses')
    existing_profile = UserFinancialProfile.get_financial_profile_by_user_id(user_id)
    if existing_profile:
        return jsonify({"error": "Profile already exists for this user"}), 400
    missing_fields = [field for field, value in {
        "user_id": user_id,
        "expected_monthly_income": expected_monthly_income,
        "expected_monthly_expenses": expected_monthly_expenses
    }.items() if not value]

    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400


    profile = UserFinancialProfile.create_financial_profile(
        user_id, expected_monthly_income, expected_monthly_expenses
    )
    
    if profile:
        return jsonify({"message": "Financial profile created successfully", "profile": profile.id}), 201
    return jsonify({"error": "Failed to create financial profile"}), 500

@fin_profile.route('/api/v1/financial_profile/<profile_id>', methods=['GET'])
def get_profile(profile_id):
    """API endpoint to get a financial profile by ID."""
    profile = UserFinancialProfile.get_financial_profile_by_id(profile_id)
    
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    
    return jsonify({
        "id": profile.id,
        "user_id": profile.user_id,
        "expected_monthly_income": profile.expected_monthly_income,
        "expected_monthly_expenses": profile.expected_monthly_expenses,
        "expected_monthly_savings": profile.expected_monthly_savings
    }), 200

@fin_profile.route('/api/v1/financial_profile/user/<user_id>', methods=['GET'])
def get_profile_by_user(user_id):
    """API endpoint to get a financial profile by user ID."""
    profile = UserFinancialProfile.get_financial_profile_by_user_id(user_id)
    
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    
    return jsonify({
        "id": profile.id,
        "user_id": profile.user_id,
        "expected_monthly_income": profile.expected_monthly_income,
        "expected_monthly_expenses": profile.expected_monthly_expenses,
        "expected_monthly_savings": profile.expected_monthly_savings
    }), 200

@fin_profile.route('/api/v1/financial_profile/<profile_id>', methods=['PUT'])
def update_profile(profile_id):
    """API endpoint to update a financial profile."""
    data = request.get_json()
    
    try:
        profile = UserFinancialProfile.update_financial_profile(profile_id, **data)
        return jsonify({
            "message": "Profile updated successfully",
            "id": profile.id,
            "expected_monthly_income": profile.expected_monthly_income,
            "expected_monthly_expenses": profile.expected_monthly_expenses,
            "expected_monthly_savings": profile.expected_monthly_savings
        }), 200
    except NoResultFound:
        return jsonify({"error": "Profile not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating financial profile: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500

@fin_profile.route('/api/v1/financial_profile/<profile_id>', methods=['DELETE'])
def delete_profile(profile_id):
    """API endpoint to delete a financial profile."""
    profile = UserFinancialProfile.get_financial_profile_by_id(profile_id)
    
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    
    try:
        db.session.delete(profile)
        db.session.commit()
        return jsonify({"message": "Profile deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting financial profile: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Failed to delete profile"}), 500
