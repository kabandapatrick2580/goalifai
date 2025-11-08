from flask import request, jsonify, Blueprint, current_app
from app.models.client.users_model import UserFinancialProfile
from app import db 
from datetime import datetime
import traceback 
from sqlalchemy.orm.exc import NoResultFound

fin_profile = Blueprint('financial_profile', __name__, url_prefix='/api/v1/financial_profile')

@fin_profile.route('/create/<uuid:user_id>', methods=['POST'])
def create_profile(user_id):
    """API endpoint to create a financial profile.
    Example:
    {
        "expected_monthly_income": 5000,
        "expected_monthly_expenses": 3000,
        "base_allocation_percentage": 50
    }
    
    """
    data = request.get_json()
    expected_monthly_income = data.get('expected_monthly_income')
    expected_monthly_expenses = data.get('expected_monthly_expenses')
    base_allocation_percentage = data.get('base_allocation_percentage', 50)  # Default to 50% if not provided
    existing_profile = UserFinancialProfile.get_financial_profile_by_user_id(user_id)
    
    if existing_profile:
        current_app.logger.error("Financial profile already exists for this user")
        return jsonify({
            "status": "error",
            "message": "Financial profile already exists for this user"
            }), 400
    
    missing_fields = [field for field, value in {
        "user_id": user_id,
        "expected_monthly_income": expected_monthly_income,
        "expected_monthly_expenses": expected_monthly_expenses
    }.items() if not value]

    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"Missing required fields: {', '.join(missing_fields)}"
            }), 400


    profile = UserFinancialProfile.create_financial_profile(
        user_id, expected_monthly_income, expected_monthly_expenses, base_allocation_percentage)
    
    if profile:
        return jsonify({"message": "Financial profile created successfully", "profile": profile.id}), 201
    return jsonify({"status": "error", "message": "Failed to create financial profile"}), 500

@fin_profile.route('/<uuid:profile_id>', methods=['GET'])
def get_profile(profile_id):
    """API endpoint to get a financial profile by ID."""
    profile = UserFinancialProfile.get_financial_profile_by_id(profile_id)
    
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    
    profile_data = profile.to_dict()
    return jsonify({
        "message": "Profile fetched successfully",
        "status": "success",
        "data": profile_data
    }), 200
        

@fin_profile.route('/user/<user_id>', methods=['GET'])
def get_profile_by_user(user_id):
    """API endpoint to get a financial profile by user ID."""
    profile = UserFinancialProfile.get_financial_profile_by_user_id(user_id)
    profile_data = profile.to_dict() if profile else None
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    
    return jsonify({
        "message": "Profile fetched successfully",
        "status": "success",
        "data": profile_data
    }), 200

@fin_profile.route('/update/<uuid:profile_id>', methods=['PUT'])
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
            "expected_monthly_savings": profile.expected_monthly_savings,
            "base_allocation_percentage": profile.base_allocation_percentage,
        }), 200
    except NoResultFound:
        return jsonify({"error": "Profile not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error updating financial profile: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": "Internal server error"}), 500

@fin_profile.route('/update_financial_profile/<uuid:user_id>', methods=['PUT'])
def update_profile_by_user(user_id):
    """API endpoint to update a financial profile by user ID."""
    data = request.get_json()
    try:
        profile = UserFinancialProfile.update_financial_profile_by_user(user_id, **data)
        if profile:
            profile_data = profile.to_dict()
            return jsonify({
                "message": "Profile updated successfully",
                "status": "success",
                "data": profile_data
            }), 200
        return jsonify({"message": "Profile not found", "status": "error"}), 404
    except ValueError as e:
        current_app.logger.error(f"Something went wrong while updating profile for user {user_id}: {str(e)}")
        return jsonify({"message": "something went wrong, check your entries and try again later", "status": "error"}), 400


@fin_profile.route('/delete/<uuid:profile_id>', methods=['DELETE'])
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
