from flask import request, jsonify, Blueprint, current_app
from app.models.client.financial import CategoriesType
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from flask import json
from json.decoder import JSONDecodeError  # Import JSONDecodeError from json module
import os


cat_types_blueprint = Blueprint('category_types_api', __name__)
@cat_types_blueprint.route('/api/v1/category-types', methods=['GET'])
def get_category_types():
    """Fetch all category types."""
    try:
        category_types = CategoriesType.get_all_category_types()
        if not category_types:
            return jsonify({"status": "success", "data": [], "message": "No category types found"}), 200
        return jsonify(
            {
            "status": "success",
            "message": "Category types fetched successfully",
            "count": len(category_types),
            "data": [cat_type.to_dict() for cat_type in category_types]}
        ), 200
    except Exception as e:
        current_app.logger.error(f"Error fetching category types: {str(e)}")
        return jsonify({"error": "An error occurred while fetching category types"}), 500
    
@cat_types_blueprint.route('/api/v1/category-types', methods=['POST'])
def create_category_type():
    """Creates a new category type.
        JSON structure:
            {
                "name": "Income",
                "description": "Income category"
            }
    """
    try:
        data = request.get_json()
        if not data or 'name' not in data:
            return jsonify({"error": "Name is required"}), 400
        
        new_cat_type = CategoriesType.create_category_type(name=data['name'], description=data.get('description', None))
        if new_cat_type:
            current_app.logger.info(f"Category type {data['name']} created successfully")
            return jsonify(
                {
                    "status": "success",
                    "message": "Category type created successfully",
                    "data": new_cat_type.to_dict()
                }
            ), 201
        else:
            current_app.logger.error("An error occurred while creating the category type")
            return jsonify({"error": "An error occurred while creating the category type"}), 500
    except Exception as e:
        current_app.logger.error(f"Error creating category type: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "An error occurred while creating the category type",
            "error": str(e)}
            ), 500

@cat_types_blueprint.route('/api/v1/category-types/bulk', methods=['POST'])
def bulk_create_category_types():
    """send category types from file/category_types.json file"""
    try:
        file_path = 'app/files/category_types.json'
        
        # Check if file exists and is not empty
        if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
            return jsonify({"error": "The JSON file is either empty or does not exist"}), 400
        
        # Open and load the file
        with open(file_path, 'r') as file:
            data = json.load(file)

        # Debug log the data
        current_app.logger.debug(f"Loaded JSON data: {data}")
        
        if not data or not isinstance(data, list):
            return jsonify({"error": "A list of category types is required"}), 400
        
        created_types = []
        
        # Process the category types
        for item in data:
            if 'name' not in item:
                continue  # Skip invalid entries
            cat_type = CategoriesType.create_category_type_from_file(
                id=item.get('id', None),
                name=item['name'],
                description=item.get('description', None)
            )
            if cat_type:
                created_types.append(cat_type)
        
        current_app.logger.info(f"{len(created_types)} category types created successfully")
        return jsonify({
            "status": "success",
            "message": f"{len(created_types)} category types created successfully",
            "data": [ct.to_dict() for ct in created_types]
        }), 201

    except JSONDecodeError as e:
        current_app.logger.error(f"JSON decode error: {str(e)}")
        return jsonify({"error": "Invalid JSON format"}), 400
    except Exception as e:
        current_app.logger.error(f"Error in bulk creating category types: {str(e)}")
        return jsonify({"error": str(e)}), 500


@cat_types_blueprint.route('/api/v1/category-types/<uuid:cat_type_id>', methods=['PUT'])
def update_category_type(cat_type_id):
    """Updates an existing category type.

    Args:
        cat_type_id (UUID): The ID of the category type to update.

    Returns:
        JSON: The updated category type data or an error message.
    """
    try:
        # Get JSON data from request
        data = request.get_json()
        if not data:
            current_app.logger.warning(f"Update request for category type {cat_type_id} failed: No data provided")
            return jsonify({"error": "No data provided"}), 400

        # Update category type using the improved method
        result = CategoriesType.update_category_type(cat_type_id, **data)

        # Log success and return the updated category type
        current_app.logger.info(f"Category type {cat_type_id} updated successfully")
        # Fetch the updated category type to return its full data
        updated_cat_type = CategoriesType.query.get(cat_type_id)
        return jsonify(updated_cat_type.to_dict()), 200

    except NoResultFound:
        current_app.logger.error(f"Category type {cat_type_id} not found")
        return jsonify({"error": "Category type not found"}), 404
    except ValueError as e:
        current_app.logger.warning(f"Validation error updating category type {cat_type_id}: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except IntegrityError:
        current_app.logger.error(f"Database integrity error updating category type {cat_type_id}")
        return jsonify({"error": "Update failed due to duplicate name or other constraint violation"}), 400
    except Exception as e:
        current_app.logger.error(f"Unexpected error updating category type {cat_type_id}: {str(e)}")
        return jsonify({"error": "An unexpected error occurred"}), 500
    
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