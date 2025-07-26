from flask import Blueprint, current_app
from flask import request, jsonify
from app.models.central import GoalStatus

goal_status_bp = Blueprint('goal_status',__name__)

@goal_status_bp.route('/api/v1/goal_status', methods=['POST'])
def create_goal_status():
    data = request.get_json()
    name = data.get('name', '').strip().lower()
    if not data or 'name' not in data:
        return jsonify({"status": "error" , "message": "Missing required field: name"}), 400
    try: 
        GoalStatus.create_goal_status(name)
        return jsonify({"status": "success", "message": "Goal priority created successfully"})
    except Exception as e:
        current_app.logger.info(f"Error while adding priority: {str(e)}")
        return jsonify({"status": "error", "message": "Error while adding a goal status"}), 500
    

@goal_status_bp.route('/api/v1/goal_status/<uuid:status_id>', methods=['PUT'])
def update_goal_status(status_id):
    data = request.get_json()
    name = data.get('name', '').strip().lower()
    if not data or 'name' not in data:
        return jsonify({"status": "error", "message": "Missing required field: name"}), 400
    try:
        goal_status = GoalStatus.update_status(status_id, name)
        if not goal_status:
            return jsonify({"status": "error", "message": "Goal status not found"}), 404
        return jsonify({"status": "success", "message": "Goal status updated successfully"})
    except Exception as e:
        current_app.logger.info(f"Error while updating goal status: {str(e)}")
        return jsonify({"status": "error", "message": "Error while updating goal status"}), 500

@goal_status_bp.route('/api/v1/goal_statuses', methods=['GET'])
def get_all_goal_statuses():
    try:
        statuses = GoalStatus.get_all_statuses()
        if not statuses:
            return jsonify({"status": "error", "message": "No goal statuses found"}), 404
        return jsonify({
            "status": "success",
            "data": {
                "goal_statuses": [status.to_dict() for status in statuses]
            },
            "message": "Goal statuses retrieved successfully"
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching goal statuses: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@goal_status_bp.route('/api/v1/goal_status/<uuid:status_id>', methods=['DELETE'])
def delete_goal_status(status_id):
    try:
        result = GoalStatus.delete_status(status_id)
        if not result:
            return jsonify({"status": "error", "message": "Goal status not found"}), 404
        return jsonify({"status": "success", "message": "Goal status deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"Error while deleting goal status: {e}")
        return jsonify({"status": "error", "message": "Error while deleting goal status"}), 500