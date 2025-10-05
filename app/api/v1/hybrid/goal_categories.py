from flask import request, jsonify, Blueprint, current_app
from app import db
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
import traceback
import uuid
from app.models.client.goal import GoalCategories

goal_categories_blueprint = Blueprint('goal_categories_api', __name__, url_prefix='/api/v1/goal_categories')


# ------------------- CREATE ---------------------------
@goal_categories_blueprint.route('/create', methods=['POST'])
def create_category():
    try:
        data = request.get_json()
        name = data.get("name")
        description = data.get("description")
        user_id = data.get("user_id")  # optional (system category if null)

        if not name:
            return jsonify({"error": "Category name is required"}), 400

        category = GoalCategories.create_category(
            user_id=user_id if user_id else None,
            name=name.strip().lower(),
            description=description
        )

        return jsonify({"message": "Category created successfully", "data": category.to_dict()}), 201

    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error creating category: {e}")
        return jsonify({"error": "Category already exists"}), 409

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error creating category: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


# ------------------- GET ALL -------------------
@goal_categories_blueprint.route('/', methods=['GET'])
def get_all_categories():
    try:
        user_id = request.args.get("user_id")  # optional
        categories = GoalCategories.get_all_categories(user_id)
        return jsonify({"data": categories}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching categories: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


# ------------------- GET ONE -------------------
@goal_categories_blueprint.route('/<uuid:category_id>', methods=['GET'])
def get_category(category_id):
    try:
        category = GoalCategories.get_category_by_id(category_id)
        if not category:
            return jsonify({"error": "Category not found"}), 404
        return jsonify({"data": category}), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching category: {traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


# ------------------- UPDATE -------------------
@goal_categories_blueprint.route('/<uuid:category_id>', methods=['PUT'])
def update_category(category_id):
    try:
        data = request.get_json()
        category = GoalCategories.query.filter_by(category_id=category_id).first()

        if not category:
            return jsonify({"status": "error", "message": "Category not found"}), 404

        # allow only user-defined categories to be updated
        if category.user_id is None:
            return jsonify({"status": "error", "message": "System categories cannot be updated"}), 403

        if "name" in data:
            category.name = data["name"].strip().lower()
        if "description" in data:
            category.description = data["description"]

        db.session.commit()
        return jsonify({"status": "success", "message": "Category updated successfully", "data": category.to_dict()}), 200

    except IntegrityError:
        db.session.rollback()
        return jsonify({"status": "error", "message": "Category with this name already exists"}), 409

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error updating category: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": "something went wrong, try again"}), 500


# ------------------- DELETE -------------------
@goal_categories_blueprint.route('/<uuid:category_id>', methods=['DELETE'])
def delete_category(category_id):
    try:
        category = GoalCategories.query.filter_by(category_id=category_id).first()

        if not category:
            return jsonify({"status": "error", "message": "Category not found"}), 404

        # prevent deletion of system-wide categories
        if category.user_id is None:
            return jsonify({ "status": "error", "message": "System categories cannot be deleted" }), 403

        db.session.delete(category)
        db.session.commit()
        return jsonify({"status":"success","message": "Category deleted successfully"}), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting category: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500

@goal_categories_blueprint.route('/bulk_create', methods=['POST'])
def bulk_create_categories():
    try:
        data = request.get_json()
        categories = data.get("categories", [])
        user_id = data.get("user_id")  # optional (system categories if null)

        if not categories or not isinstance(categories, list):
            return jsonify({"status": "error", "message": "'categories' must be a non-empty list"}), 400
        created_categories = []
        for cat in categories:
            
            name = cat.get("name")
            description = cat.get("description")
            existing_cat = GoalCategories.get_goal_category_by_name(name)
            if existing_cat:
                continue  # skip duplicates
            if not name:
                return jsonify({"status": "error", "message": "Each category must have a 'name'"}), 400
            category = GoalCategories.create_category(
                user_id=user_id if user_id else None,
                name=name.strip().lower(),
                description=description
            )
            
            created_categories.append(category)
        return jsonify({"status": "success", "message": f"{len(created_categories)} categories created successfully", "data": created_categories}), 201
    except IntegrityError as e:
        db.session.rollback()
        current_app.logger.error(f"Integrity error in bulk create: {e}")
        return jsonify({"status": "error", "message": "One or more categories already exist"}), 409
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk create: {traceback.format_exc()}")
        return jsonify({"status": "error", "message": str(e)}), 500
