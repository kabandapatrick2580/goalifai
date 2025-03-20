from flask import request, jsonify, Blueprint, current_app
from app.models.central import User, Goal
from app import db
from datetime import datetime
import traceback
from sqlalchemy.orm.exc import NoResultFound


goal_blueprint = Blueprint('goal_api', __name__)
@goal_blueprint.route('/api/v1/define_goal', methods=['POST'])
def create_goal():
    try:
        data = request.get_json()
        required_fields = ['user_id', 'title', 'target_amount', 'due_date']

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' is required"}), 400
            
        # Check if user exists
        existing_user = User.get_user_by_id(data['user_id'])
        if existing_user is None:
            current_app.logger.info(f"User with id {data['user_id']} does not exist")
            return jsonify({"error": "User does not exist"}), 400
        
        # Create goal
        goal = Goal.create_goal(
            user_id=data['user_id'],
            title=data['title'],
            target_amount=data['target_amount'],
            due_date=datetime.strptime(data['due_date'], "%Y-%m-%d")
        )
        if goal is None:
            current_app.logger.error(f"An error occurred while creating the goal")
            return jsonify({"error": "An error occurred while creating the goal"}), 500
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
    # Log success
    current_app.logger.info(f"Goal {data['title']} created successfully")
    return jsonify({
        "message": "Goal created successfully",
    }), 201

"""Update goal"""
@goal_blueprint.route('/api/v1/goals/update/<uuid:goal_id>', methods=['PUT'])
def update_goal(goal_id):
    try:
        # Ensure request contains JSON data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()

        # Ensure there is data to update
        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Find and update the goal
        updated_goal = Goal.update_goal(goal_id=goal_id, **data)

        if not updated_goal:
            return jsonify({"error": "Goal not found"}), 404

        return jsonify(updated_goal.to_dict()), 200

    except NoResultFound:
        return jsonify({"error": "Goal not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@goal_blueprint.route('/api/v1/goals/list/<uuid:goal_id>', methods=['GET'])
def get_goal(goal_id):
    try:
        goals = Goal.get_goal_by_id(goal_id)
        user_goals = []
        if goals is None:
            return jsonify({"error": "No goal found"}), 404
        for goal in goals:
            user_goals.append(goal.to_dict())
        return jsonify(user_goals), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    
@goal_blueprint.route('/api/v1/goals/delete/<uuid:goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    try:
        response = Goal.delete_goal(goal_id)
        return jsonify(response), 200
    except NoResultFound:
        return jsonify({"error": "Goal not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400    


@goal_blueprint.route('/api/v1/goals_list', methods=['GET'])
def list_all_goals():
    try:
        goals = Goal.get_all_goals()
        return jsonify(goals), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

    
    


        