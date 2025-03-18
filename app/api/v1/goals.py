from flask import request, jsonify, Blueprint, current_app
from app.models.central import User, Goal
from app import db
from datetime import datetime
import traceback

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

@goal_blueprint.route('/api/v1/goals_list', methods=['GET'])
def list_all_goals():
    try:
        goals = Goal.list_all_goals()
        goals_list = []
        for goal in goals:
            goals_list.append({
                "goal_id": str(goal.goal_id),
                "user_id": str(goal.user_id),
                "title": goal.title,
                "target_amount": goal.target_amount,
                "due_date": goal.due_date.strftime("%Y-%m-%d"),
                "created_at": goal.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                "updated_at": goal.updated_at.strftime("%Y-%m-%d %H:%M:%S")
            })
        return jsonify(goals_list), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
    
    


        