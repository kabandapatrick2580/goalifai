from flask import request, jsonify, Blueprint, current_app
from app.models.client.goal import Goal
from app.models.client.users_model import User
from app import db
from datetime import datetime
import traceback
from sqlalchemy.orm.exc import NoResultFound


goal_blueprint = Blueprint('goal_api', __name__, url_prefix='/api/v1/goals')
@goal_blueprint.route('/define_goal', methods=['POST'])
def create_goal():
    try:
        data = request.get_json()
        required_fields = ['user_id', 'title', 'target_amount','goal_category_id']

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"status":"error","message": f"'{field}' is required"}), 400
            
        # Check if user exists
        existing_user = User.get_user_by_id(data['user_id'])
        if existing_user is None:
            current_app.logger.info(f"User with id {data['user_id']} does not exist")
            return jsonify({"status":"error","message": "User does not exist"}), 400
        
        # Create goal
        goal = Goal.create_goal(
            user_id=data['user_id'],
            title=data['title'],
            target_amount=data['target_amount'],
            due_date=datetime.strptime(data['due_date'], "%Y-%m-%d") if 'due_date' in data else None,
            description=data.get('description', None),
            goal_category=data['goal_category_id'],
            priority_id=data.get('priority_id', None),
            goal_status_id=data.get('goal_status_id', None)

        )
        if goal is None:
            current_app.logger.error(f"An error occurred while creating the goal")
            return jsonify({"error": "An error occurred while creating the goal"}), 500
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return None
    
    # Log success
    current_app.logger.info(f"Goal {data['title']} created successfully")
    return jsonify({
        "message": "Goal created successfully",
    }), 201

"""Update goal"""
@goal_blueprint.route('/update/<uuid:goal_id>', methods=['PUT'])
def update_goal(goal_id):
    try:
        # Ensure request contains JSON data
        if not request.is_json:
            return jsonify({"status": "error", "message": "Request must be JSON"}), 400
        
        data = request.get_json()

        # Ensure there is data to update
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        # Find and update the goal
        updated_goal = Goal.update_goal(goal_id=goal_id, **data)

        if not updated_goal:
            return jsonify({"error": "Goal not found"}), 404

        return jsonify(updated_goal.to_dict()), 200

    except NoResultFound:
        return jsonify({"status": "error", "message": "Goal not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400

@goal_blueprint.route('/list/<uuid:goal_id>', methods=['GET'])
def get_goal(goal_id):
    try:
        goals = Goal.get_goal_by_id(goal_id)
        user_goals = []
        if goals is None:
            return jsonify({"status": "error", "message": "Goal not found"}), 404
        for goal in goals:
            user_goals.append(goal.to_dict())
        return jsonify(user_goals), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    
@goal_blueprint.route('/delete/<uuid:goal_id>', methods=['DELETE'])
def delete_goal(goal_id):
    try:
        response = Goal.delete_goal(goal_id)
        return jsonify(response), 200
    except NoResultFound:
        return jsonify({"status": "error", "message": "Goal not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 400
    

@goal_blueprint.route('/all_goals/<uuid:user_id>', methods=['GET'])
def get_all_goals(user_id):
    try:
        goals = Goal.get_all_goals(user_id)
        return jsonify({"status":"success", "message":"Goals fetched successfully", "data": goals})
    
    except Exception as e:
        current_app.logger.error(f"An error occured while fetching goals {e}")
        return jsonify({"status":"error", "message":"something went wrong, try again"}), 500
    
@goal_blueprint.route('/bulk_create', methods=['POST'])
def bulk_create_goals():
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({"status":"error","message": "Input data must be a list of goals"}), 400
        
        created_goals = []
        for goal_data in data:
            required_fields = ['user_id', 'title', 'target_amount','goal_category_id']
            for field in required_fields:
                if field not in goal_data:
                    return jsonify({"status":"error","message": f"'{field}' is required in each goal"}), 400
                
            existing_user = User.get_user_by_id(goal_data['user_id'])
            if existing_user is None:
                current_app.logger.info(f"User with id {goal_data['user_id']} does not exist")
                return jsonify({"status":"error","message": f"User with id {goal_data['user_id']} does not exist"}), 400
            
            goal = Goal.create_goal(
                user_id=goal_data['user_id'],
                title=goal_data['title'],
                target_amount=goal_data['target_amount'],
                due_date=datetime.strptime(goal_data['due_date'], "%Y-%m-%d") if 'due_date' in goal_data else None,
                description=goal_data.get('description', None),
                goal_category=goal_data['goal_category_id'],
                priority_id=goal_data.get('priority_id', None),
                goal_status_id=goal_data.get('goal_status_id', None)
            )
            if goal is None:
                current_app.logger.error(f"An error occurred while creating the goal {goal_data['title']}")
                return jsonify({"error": f"An error occurred while creating the goal {goal_data['title']}"}), 500
            created_goals.append(goal)
        
        current_app.logger.info(f"{len(created_goals)} goals created successfully")
        return jsonify({
            "status":"success",
            "message": f"{len(created_goals)} goals created successfully",
            "data": created_goals
        }), 201

    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status":"error","message": "An internal error occurred"}), 500
    
    


        