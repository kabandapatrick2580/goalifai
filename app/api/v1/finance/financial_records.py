from flask import request, jsonify, Blueprint, current_app
from app.models.client.financial import FinancialRecord
from datetime import datetime
from sqlalchemy.orm.exc import NoResultFound
from app.models.client.financial import Categories
import uuid
from flask_jwt_extended import jwt_required, get_jwt_identity
from decimal import Decimal, InvalidOperation
from app.models.central.central import Currency
from app.models.client.users_model import User
# Validate amount
from decimal import Decimal, InvalidOperation
from app.models.central.central import ExpenseOrientation, ExpenseBeneficiary


financial_records_blueprint = Blueprint('financial_record_api', __name__, url_prefix='/api/v1/financial_records')
@financial_records_blueprint.route('/create/<uuid:user_id>/financial-records', methods=['POST'])
#@jwt_required()
def create_financial_record(user_id):
    """Creates a new financial record for a specific user."""

    """ Validate user authorization
    current_user_id = get_jwt_identity()
    if str(current_user_id) != str(user_id):
        return jsonify({"status": "error", "error": "Unauthorized access"}), 403
    """
    # Fetch user + preferred currency
    user_obj = User.get_user_by_id(user_id)
    user = user_obj.to_dict() if user_obj else None
    if not user:
        return jsonify({"status": "error", "error": "User not found"}), 404

    user_currency_id = None
    if user.get("currency"):
        preffered_currency = Currency.get_currency_by_code(user["currency"])
        if preffered_currency:
            user_currency_id = preffered_currency.id
            

    try:
        data = request.get_json()
        required_fields = ["category_id", "amount", "recorded_at", 'currency_id']

        for field in required_fields:
            if field not in data:
                return jsonify({"status": "error", "error": f"{field} is required"}), 400

        # Validate category UUID exists
        try:
            category_id_uuid = uuid.UUID(data["category_id"])
        except ValueError:
            return jsonify({"status": "error", "message": "Invalid category_id format"}), 400

        category = Categories.query.get(category_id_uuid)
        if not category:
            return jsonify({"status": "error", "message": "Invalid category"}), 400


        try:
            amount = Decimal(str(data["amount"])).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError):
            return jsonify({"status": "error", "message": "Invalid amount format"}), 400

        if amount <= 0:
            return jsonify({"status": "error", "message": "Amount must be positive"}), 400

        # Resolve currency
        currency_id = None
        if data.get("currency_id"):
            try:
                currency_uuid = uuid.UUID(data["currency_id"])
            except ValueError:
                return jsonify({"status": "error", "error": "Invalid currency format"}), 400

            currency = Currency.get_currency_by_id(currency_uuid)
            if not currency:
                return jsonify({"status": "error", "error": "Invalid currency"}), 400
            currency_id = currency.id
        elif user_currency_id:
            currency_id = user_currency_id
        else:
            return jsonify({"status": "error", "message": "Currency is required"}), 400

        expense_orientation_id = None
        if data.get("expense_orientation_id"):
            try:
                expense_orientation_uuid = uuid.UUID(data["expense_orientation_id"])
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid expense_orientation_id format"}), 400

            expense_orientation = ExpenseOrientation.get_orientation_by_id(expense_orientation_uuid)
            if not expense_orientation:
                return jsonify({"status": "error", "message": "Invalid expense orientation"}), 400
            expense_orientation_id = expense_orientation.id
        
        expense_beneficiary_id = None
        if data.get("expense_beneficiary_id"):
            try:
                expense_beneficiary_uuid = uuid.UUID(data["expense_beneficiary_id"])
            except ValueError:
                return jsonify({"status": "error", "message": "Invalid expense_beneficiary_id format"}), 400
            expense_beneficiary = ExpenseBeneficiary.get_beneficiary_by_id(expense_beneficiary_uuid)
            if not expense_beneficiary:
                return jsonify({"status": "error", "message": "Invalid expense beneficiary"}), 400
            expense_beneficiary_id = expense_beneficiary.id
            

        # Create record
        new_record = FinancialRecord.create_record(
            user_id=user_id,
            category_id=category_id_uuid,
            amount=amount,
            recorded_at=datetime.fromisoformat(data["recorded_at"]),
            description=data.get("description"),
            currency_id=currency_id if currency_id else None,
            expected_transaction=data.get("expected_transaction", False),
            expense_orientation_id=expense_orientation_id,
            expense_beneficiary_id=expense_beneficiary_id
        )

        if new_record:
            message = f"{category.name} {category.type.name if hasattr(category, 'type') else ''} recorded successfully"
            current_app.logger.info(message)
            return jsonify({
                "message": message,
                "status": "success",
                "record_id": str(new_record.record_id),
                "amount": str(new_record.amount),
                "currency": str(new_record.currency),
                "recorded_at": new_record.recorded_at.isoformat()
            }), 201

        return jsonify({"status": "error", "error": "Failed to create financial record"}), 500

    except Exception as e:
        current_app.logger.error(f"Error creating financial record: {str(e)}")
        return jsonify({"status": "error", "error": str(e)}), 500



@financial_records_blueprint.route('/all/<uuid:user_id>', methods=['GET', 'OPTIONS'])
@jwt_required(optional=True)
def get_financial_records(user_id):
    """Fetch all financial records for a user."""

    if request.method == 'OPTIONS':
        return jsonify({}), 200

    try:
        records = FinancialRecord.get_records_by_user(user_id)
        return jsonify({
            "message": "Financial records fetched successfully",
            "data":[record.to_dict() for record in records],
            "status": "success"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@financial_records_blueprint.route('/income/<uuid:user_id>', methods=['GET'])
#@jwt_required()
def get_income_records(user_id):
    """Fetch all income financial records for a user."""
    try:
        records = FinancialRecord.get_income_records_by_user(user_id)
        return jsonify({
            "message": "Income financial records fetched successfully",
            "data":[record.to_dict() for record in records],
            "status": "success"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@financial_records_blueprint.route('/expense/<uuid:user_id>', methods=['GET'])
#@jwt_required()
def get_expense_records(user_id):
    """Fetch all expense financial records for a user."""
    try:
        records = FinancialRecord.get_expense_records_by_user(user_id)
        return jsonify({
            "message": "Expense financial records fetched successfully",
            "data":[record.to_dict() for record in records],
            "total": sum(record.amount for record in records),
            "count": len(records),
            "status": "success"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@financial_records_blueprint.route('/monthly_records/<uuid:user_id>/<month_year>', methods=['GET'])
#@jwt_required()
def get_financial_records_by_month(user_id, month_year):
    """Fetch financial records for a user by month and year."""
    try:
        year, month = map(int, month_year.split('-'))
        records = FinancialRecord.get_records_by_user_and_month(user_id, year, month)

        if not records:
            return jsonify({
                "message": "No financial records found for the specified period.",
                "data": {
                    "income": [],
                    "expenses": []
                },
                "total_income": 0,
                "total_expenses": 0,
                "net_amount": 0,
                "income_count": 0,
                "expense_count": 0,
                "status": "success"
            }), 200

        # separate income and expenses
        income_records = [record.to_dict() for record in records if record.category.type.name.lower() == 'income']
        expense_records = [record.to_dict() for record in records if record.category.type.name.lower() == 'expense']
        
        total_income = sum(record['amount'] for record in income_records)
        total_expenses = sum(record['amount'] for record in expense_records)

        return jsonify({
            "message": "Financial records fetched successfully",
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_amount": total_income - total_expenses,
            "income_count": len(income_records),
            "expense_count": len(expense_records),
            "data": {
                "income": income_records,
                "expenses": expense_records
            },
            "status": "success"
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching monthly financial records: {str(e)}")
        return jsonify({"error": str(e)}), 500

@financial_records_blueprint.route('/update/<uuid:record_id>', methods=['PUT'])
#@jwt_required()
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

@financial_records_blueprint.route('/delete/<uuid:record_id>', methods=['DELETE'])
#@jwt_required()
def delete_financial_record(record_id):
    """Deletes a financial record."""
    try:
        if FinancialRecord.delete_record(record_id):
            return jsonify({"message": "Financial record deleted successfully", "status": "success"}), 200
        return jsonify({"error": "Failed to delete financial record", "status": "error"}), 500
    except NoResultFound:
        return jsonify({"error": "Financial record not found", "status": "error"}), 404
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

@financial_records_blueprint.route('/monthly_summary/<uuid:user_id>', methods=['GET'])
#@jwt_required()
def get_monthly_summary(user_id):
    """Fetch monthly summary of financial records for a user."""
    try:
        data = request.get_json() or {}
        year = data.get("year")
        month = data.get("month")
        current_app.logger.info(f"Fetching monthly summary for user {user_id} for {year}-{month}")
        monthly_summary = FinancialRecord.get_monthly_summary(user_id, year, month)
        if not monthly_summary:
            return jsonify({"message": "No financial records found for the specified month."}), 200
        return jsonify({
            "message": "Monthly summary fetched successfully",
            "data": monthly_summary,
            "status": "success"
        }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500