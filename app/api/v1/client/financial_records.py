from flask import request, jsonify, Blueprint, current_app
from app.models.client.financial import FinancialRecord
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from app.models.client.financial import Categories
import uuid
from flask_jwt_extended import jwt_required, get_jwt_identity


financial_records_blueprint = Blueprint('financial_record_api', __name__)
@financial_records_blueprint.route('/api/v1/users/<uuid:user_id>/financial-records', methods=['POST'])
@jwt_required()
def create_financial_record(user_id):
    """Creates a new financial record for a specific user."""
    try:
        data = request.get_json()
        required_fields = ['category_id', 'amount', 'recorded_at']

        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"{field} is required"}), 400

        categories = [cat.category_id for cat in Categories.get_all_categories()]
        category_id_uuid = uuid.UUID(data['category_id'])


        if category_id_uuid not in categories:
            print("Invalid category ID")
            return jsonify({"error": "Invalid category ID"}), 400

        new_record = FinancialRecord.create_record(
            user_id=user_id,
            category_id=data['category_id'],
            amount=data['amount'],
            recorded_at= datetime.fromisoformat(data['recorded_at']),
            description= data['description']
        )

        if new_record:
            message = f"{new_record.category.name} {new_record.category.type.name} recorded successfully"
            current_app.logger.info(message)
            return jsonify({"message": message, "status": "success"}), 201
        return jsonify({"error": "Failed to create financial record", "status": "error"}), 500
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500


@financial_records_blueprint.route('/api/v1/financial-records/<uuid:user_id>', methods=['GET'])
@jwt_required()
def get_financial_records(user_id):
    """Fetch all financial records for a user."""
    try:
        records = FinancialRecord.get_records_by_user(user_id)
        return jsonify({
            "message": "Financial records fetched successfully",
            "data":[record.to_dict() for record in records],
            "status": "success"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@financial_records_blueprint.route('/api/v1/financial-records/<uuid:record_id>', methods=['PUT'])
@jwt_required()
def update_financial_record(record_id):
    """Updates an existing financial record."""
    try:
        data = request.get_json()

        cleaned_data = {k: v.strip() if isinstance(v, str) else v for k, v in data.items()}

        updated_record = FinancialRecord.update_record(record_id, **cleaned_data)
        if updated_record:
            return jsonify({
                "message": "Financial record updated successfully",
                "status": "success",
            }), 200
        return jsonify({"error": "Financial record not found"}), 404
    
    except NoResultFound:
        return jsonify({"error": "Financial record not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@financial_records_blueprint.route('/api/v1/financial-records/<uuid:record_id>', methods=['DELETE'])
@jwt_required()
def delete_financial_record(record_id):
    """Deletes a financial record."""
    try:
        if FinancialRecord.delete_record(record_id):
            return jsonify({"message": "Financial record deleted successfully"}), 200
        return jsonify({"error": "Failed to delete financial record"}), 500
    except NoResultFound:
        return jsonify({"error": "Financial record not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
