from flask import Blueprint, request, jsonify, current_app
from app.models.central.central import ExpenseBeneficiary

expense_beneficiary_bp = Blueprint('expense_beneficiary', __name__, url_prefix='/api/v1/expense_beneficiaries')

@expense_beneficiary_bp.route('/create', methods=['POST'])
def create_expense_beneficiary():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    examples = data.get('examples', [])
    try:
        new_beneficiary = ExpenseBeneficiary.create_beneficiary(
            name=name,
            description=description,
            examples=examples
        )
        return jsonify(
            {
                "status": "success",
                "message": "Expense beneficiary created successfully",
                "data": new_beneficiary.to_dict()
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error creating expense beneficiary: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_beneficiary_bp.route('/update/<int:beneficiary_id>', methods=['PUT'])
def update_expense_beneficiary(beneficiary_id):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    examples = data.get('examples', [])
    try:
        updated_beneficiary = ExpenseBeneficiary.update_beneficiary(
            beneficiary_id=beneficiary_id,
            name=name,
            description=description,
            examples=examples
        )
        return jsonify(
            {
                "status": "success",
                "message": "Expense beneficiary updated successfully",
                "data": updated_beneficiary.to_dict()
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error updating expense beneficiary: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_beneficiary_bp.route('/update_by_user/<uuid:user_id>', methods=['PUT'])
def update_expense_beneficiary_by_user(user_id):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    examples = data.get('examples', [])
    try:
        updated_beneficiary = ExpenseBeneficiary.update_user_def_beneficiary(
            user_id=user_id,
            name=name,
            description=description,
            examples=examples
        )
        return jsonify(
            {
                "status": "success",
                "message": "Expense beneficiary updated successfully",
                "data": updated_beneficiary.to_dict()
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error updating expense beneficiary by user: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_beneficiary_bp.route('/get/<uuid:beneficiary_id>', methods=['GET'])
def get_expense_beneficiary(beneficiary_id):
    try:
        beneficiary = ExpenseBeneficiary.get_beneficiary_by_id(beneficiary_id)
        return jsonify(
            {
                "status": "success",
                "data": beneficiary.to_dict(),
                "message": "Expense beneficiary retrieved successfully"
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error retrieving expense beneficiary: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_beneficiary_bp.route('/get_by_name/<string:name>', methods=['GET'])
def get_expense_beneficiary_by_name(name):
    try:
        beneficiary = ExpenseBeneficiary.get_beneficiary_by_name(name)
        return jsonify(
            {
                "status": "success",
                "data": beneficiary.to_dict(),
                "message": "Expense beneficiary retrieved successfully"
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error retrieving expense beneficiary by name: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_beneficiary_bp.route('/list/<uuid:user_id>', methods=['GET'])
def list_expense_beneficiaries(user_id):
    try:
        beneficiaries = ExpenseBeneficiary.get_all_beneficiaries(user_id=user_id)
        beneficiaries_data = [b.to_dict() for b in beneficiaries]
        return jsonify(
            {
                "status": "success",
                "data": beneficiaries_data,
                "message": "Expense beneficiaries retrieved successfully"
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error listing expense beneficiaries: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_beneficiary_bp.route('/bulk_create', methods=['POST'])
def bulk_create_expense_beneficiaries():
    data = request.get_json()
    beneficiaries = data.get('expense_beneficiaries', [])
    try:
        created_beneficiaries = ExpenseBeneficiary.bulk_create_beneficiaries(beneficiaries)
        return jsonify(
            {
                "status": "success",
                "message": "Expense beneficiaries created successfully",
                "data": [beneficiary.to_dict() for beneficiary in created_beneficiaries]
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error bulk creating expense beneficiaries: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400

@expense_beneficiary_bp.route('/delete_all', methods=['DELETE'])
def delete_all_expense_beneficiaries():
    try:
        ExpenseBeneficiary.delete_all_beneficiaries()
        return jsonify(
            {
                "status": "success",
                "message": "All expense beneficiaries deleted successfully"
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error deleting all expense beneficiaries: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400