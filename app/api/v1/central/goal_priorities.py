from flask import request, jsonify, Blueprint, current_app
from app.models.client.goal import GoalPriority
from app import db

from sqlalchemy.exc import IntegrityError
goal_priorities_blueprint = Blueprint('goal_priorities_api', __name__)
@goal_priorities_blueprint.route('/api/v1/goal_priorities/create', methods=['POST'])
def create_goal_priority():
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' is required", "status": "fail"}), 400

        # Create a new goal priority
        new_goal_priority = GoalPriority(name=data['name'])
        db.session.add(new_goal_priority)
        db.session.commit()

        return jsonify({"message": "Goal priority created successfully", "status": "success"}), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({"error": "Goal priority with this name already exists", "status": "fail"}), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating goal priority: {str(e)}")
        return jsonify({"error": "Internal server error", "status": "fail"}), 500