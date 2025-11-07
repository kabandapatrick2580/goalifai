from flask import request, jsonify, Blueprint, current_app
from app.models.client.goal import GoalPriority
from app import db

from sqlalchemy.exc import IntegrityError
goal_priorities_blueprint = Blueprint('goal_priorities_api', __name__, url_prefix='/api/v1/goal_priorities')
@goal_priorities_blueprint.route('/create', methods=['POST'])
def create_goal_priority():
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'percentage']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' is required", "status": "fail"}), 400

        # Create a new goal priority
        new_goal_priority = GoalPriority.create_priority(
            name=data['name'],
            percentage=data['percentage'],
            user_id=data.get('user_id', None)
            )
        if not new_goal_priority:
            current_app.logger.error("An error occurred while creating the goal priority")
            return jsonify({"status": "error", "message": "An error occurred while creating the goal priority"}), 500

        return jsonify({"message": "Goal priority created successfully", "status": "success"}), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Goal priority with this name already exists", "status": "fail"}), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating goal priority: {str(e)}")
        return jsonify({"error": "Internal server error", "status": "fail"}), 500
    

@goal_priorities_blueprint.route('/bulk_create', methods=['POST'])
def bulk_create_goal_priorities():
    try:
        data = request.get_json()
        priorities = data.get('priorities', [])
        
        if not priorities or not isinstance(priorities, list):
            return jsonify({"status": "error", "message": "Invalid or missing 'priorities' list"}), 400

        for priority in priorities:
            if 'name' not in priority or 'percentage' not in priority:
                return jsonify({"status": "error", "message": "Each priority must have 'name' and 'percentage' fields"}), 400

        created_priorities = []
        for priority in priorities:
            new_priority = GoalPriority.create_priority(
                name=priority['name'],
                percentage=priority['percentage'],
                user_id=priority.get('user_id', None)
            )
            if not new_priority:
                current_app.logger.error("An error occurred while creating a goal priority")
                return jsonify({"status": "error", "message": "An error occurred while creating a goal priority"}), 500
            created_priorities.append(new_priority)

        return jsonify({"status": "success", "message": "Goal priorities created successfully", "data": created_priorities}), 201

    except Exception as e:
        current_app.logger.error(f"Error creating goal priorities: {str(e)}")
        return jsonify({"status": "error", "message": "Internal server error"}), 500