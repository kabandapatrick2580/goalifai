from flask import request, jsonify, Blueprint, current_app
from app.models.central import CategoriesType
import json


cat_types_blueprint = Blueprint('category_types_api', __name__)
@cat_types_blueprint.route('/api/v1/category-types', methods=['GET'])
def get_category_types():
    """Fetch all category types."""
    try:
        category_types = CategoriesType.get_all_category_types()
        return jsonify([cat_type.to_dict() for cat_type in category_types]), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching category types: {str(e)}")
        return jsonify({"error": "An error occurred while fetching category types"}), 500
    
@cat_types_blueprint.route('/api/v1/category-types', methods=['POST'])
def create_category_type():
    """Creates a new category type."""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "Name is required"}), 400
        
        new_cat_type = CategoriesType.create_category_type(name=data['name'], description=data.get('description', None))
        if new_cat_type:
            current_app.logger.info(f"Category type {data['name']} created successfully")
            return jsonify(new_cat_type.to_dict()), 201
        else:
            current_app.logger.error("An error occurred while creating the category type")
            return jsonify({"error": "An error occurred while creating the category type"}), 500
    except Exception as e:
        current_app.logger.error(f"Error creating category type: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@cat_types_blueprint.route('/api/v1/category-types/<uuid:cat_type_id>', methods=['PUT'])
def update_category_type(cat_type_id):
    """Updates an existing category type."""
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "Name is required"}), 400
        
        updated_cat_type = CategoriesType.update_category_type(cat_type_id, name=data['name'], description=data.get('description', None))
        if updated_cat_type:
            current_app.logger.info(f"Category type {cat_type_id} updated successfully")
            return jsonify(updated_cat_type.to_dict()), 200
        else:
            current_app.logger.error("An error occurred while updating the category type")
            return jsonify({"error": "An error occurred while updating the category type"}), 500
    except Exception as e:
        current_app.logger.error(f"Error updating category type: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@cat_types_blueprint.route('/api/v1/category-types/<uuid:cat_type_id>', methods=['DELETE'])
def delete_category_type(cat_type_id):
    """Deletes a category type."""
    try:
        deleted = CategoriesType.delete_category_type(cat_type_id)
        if deleted:
            current_app.logger.info(f"Category type {cat_type_id} deleted successfully")
            return jsonify({"message": "Category type deleted successfully"}), 200
        else:
            current_app.logger.error("An error occurred while deleting the category type")
            return jsonify({"error": "An error occurred while deleting the category type"}), 500
    except Exception as e:
        current_app.logger.error(f"Error deleting category type: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@cat_types_blueprint.route('/api/v1/category-types/<uuid:cat_type_id>', methods=['GET'])
def get_category_type(cat_type_id):
    """Fetch a specific category type by ID."""
    try:
        cat_type = CategoriesType.get_category_type_by_id(cat_type_id)
        if cat_type:
            return jsonify(cat_type.to_dict()), 200
        else:
            return jsonify({"error": "Category type not found"}), 404
    except Exception as e:
        current_app.logger.error(f"Error fetching category type: {str(e)}")
        return jsonify({"error": str(e)}), 500