from flask import request, jsonify, Blueprint, current_app
from app.models.financial import FinancialRecord
from app import db
from datetime import datetime
import traceback
from sqlalchemy.orm.exc import NoResultFound

financial_records_blueprint = Blueprint('financial_record_api', __name__)
@financial_records_blueprint.route('/api/v1/users/<uuid:user_id>/financial-records', methods=['POST'])
def create_financial_record(user_id):
    """Creates a new financial record for a specific user."""
    try:
        data = request.get_json()
        required_fields = ['category_id', 'record_type', 'amount', 'recorded_at']

        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' is required"}), 400

        if data['record_type'] not in {'Income', 'Expense'}:
            return jsonify({"error": "Invalid record type. Must be 'Income' or 'Expense'"}), 400

        new_record = FinancialRecord.create_record(
            user_id=user_id,
            category_id=data['category_id'],
            record_type=data['record_type'],
            amount=data['amount'],
            recorded_at=datetime.fromisoformat(data['recorded_at']),
            description=data.get('description')
        )

        if new_record:
            return jsonify(new_record.to_dict()), 201
        return jsonify({"error": "Failed to create financial record"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500




@financial_records_blueprint.route('/api/v1/financial-records/<uuid:user_id>', methods=['GET'])
def get_financial_records(user_id):
    """Fetch all financial records for a user."""
    try:
        records = FinancialRecord.get_records_by_user(user_id)
        return jsonify([record.to_dict() for record in records]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@financial_records_blueprint.route('/api/v1/financial-records/<uuid:record_id>', methods=['PUT'])
def update_financial_record(record_id):
    """Updates an existing financial record."""
    try:
        data = request.get_json()
        updated_record = FinancialRecord.update_record(record_id, **data)
        return jsonify(updated_record.to_dict()), 200
    except NoResultFound:
        return jsonify({"error": "Financial record not found"}), 404
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@financial_records_blueprint.route('/api/v1/financial-records/<uuid:record_id>', methods=['DELETE'])
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
