from flask import Blueprint, current_app
from flask import request, jsonify
from app.models.central import GoalStatus

goal_status_bp = Blueprint('goal_status',__name__)

@goal_status_bp.route('/api/v1/create_goal_status', methods=['POST'])
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