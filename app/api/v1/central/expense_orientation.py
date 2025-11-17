from flask import Blueprint, request, jsonify, current_app
from app.models.central.central import ExpenseOrientation

expense_orientation_bp = Blueprint('expense_orientation', __name__, url_prefix='/api/v1/expense_orientation')

@expense_orientation_bp.route('/create', methods=['POST'])
def create_expense_orientation():
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    examples = data.get('examples', [])
    try:
        new_orientation = ExpenseOrientation.create_orientation(
            name=name,
            description=description,
            examples=examples
        )
        return jsonify(
            {
                "status": "success",
                "message": "Expense orientation created successfully",
                "data": new_orientation.to_dict()
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error creating expense orientation: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400

@expense_orientation_bp.route('/list', methods=['GET'])
def list_expense_orientations():
    try:
        orientations = ExpenseOrientation.get_all_orientations()
        return jsonify(
            {
                "status": "success",
                "data": [orientation.to_dict() for orientation in orientations]
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error listing expense orientations: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_orientation_bp.route('/delete/<int:orientation_id>', methods=['DELETE'])
def delete_expense_orientation(orientation_id):
    try:
        ExpenseOrientation.delete_orientation(orientation_id)
        return jsonify(
            {
                "status": "success",
                "message": "Expense orientation deleted successfully"
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error deleting expense orientation: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_orientation_bp.route('/update/<int:orientation_id>', methods=['PUT'])
def update_expense_orientation(orientation_id):
    data = request.get_json()
    name = data.get('name')
    description = data.get('description')
    try:
        updated_orientation = ExpenseOrientation.update_orientation(
            orientation_id,
            name=name,
            description=description
        )
        return jsonify(
            {
                "status": "success",
                "message": "Expense orientation updated successfully",
                "data": updated_orientation.to_dict()
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error updating expense orientation: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_orientation_bp.route('/get/<int:orientation_id>', methods=['GET'])
def get_expense_orientation(orientation_id):
    try:
        orientation = ExpenseOrientation.get_orientation_by_id(orientation_id)
        return jsonify(
            {
                "status": "success",
                "data": orientation.to_dict()
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error retrieving expense orientation: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    
@expense_orientation_bp.route('/get_by_name/<string:name>', methods=['GET'])
def get_expense_orientation_by_name(name):
    try:
        orientation = ExpenseOrientation.get_orientation_by_name(name)
        return jsonify(
            {
                "status": "success",
                "data": orientation.to_dict()
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error retrieving expense orientation by name: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400
    

@expense_orientation_bp.route('/bulk_create', methods=['POST'])
def bulk_create_expense_orientations():
    data = request.get_json()
    orientations = data.get('expense_orientations', [])
    try:
        created_orientations = ExpenseOrientation.bulk_create_orientations(orientations)
        return jsonify(
            {
                "status": "success",
                "message": "Expense orientations created successfully",
                "data": [orientation.to_dict() for orientation in created_orientations]
            }
        )
    except Exception as e:
        current_app.logger.error(f"Error bulk creating expense orientations: {str(e)}")
        return jsonify(
            {
                "status": "error",
                "message": str(e)
            }
        ), 400