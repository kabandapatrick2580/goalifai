from flask import request, jsonify, Blueprint, current_app
from app.models.client.financial import Categories
from app import db
from datetime import datetime
import traceback
from sqlalchemy.orm.exc import NoResultFound
import json

categories_blueprint = Blueprint('categories_api', __name__, url_prefix='/api/v1/categories')
@categories_blueprint.route('/create', methods=['POST'])
def create_category():
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['name', 'category_type']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' is required"}), 400
            
        # check if category already exists
        # Check if category already exists (case-insensitive)
        existing_category = Categories.query.filter(
            db.func.lower(Categories.name) == data['name'].lower()
        ).first()
        if existing_category:
            message = f"Category {data['name']} already exists"
            current_app.logger.info(f"Category {data['name']} already exists")
            return jsonify({f"error": message}), 400
        
        # Create category
        new_category = Categories.create_category(
            user_id=data.get('user_id', None),
            name=data['name'],
            category_type=data['category_type'],
            description=data.get('description', None)
        )
        if new_category:
            current_app.logger.info(f"Category {data['name']} created successfully")
            return jsonify({
                "message": "Category created successfully",
                "status": "success",
                "category": new_category.to_dict()
                }), 201
        if new_category is None:
            current_app.logger.error(f"An error occurred while creating the category")
            return jsonify({"error": "An error occurred while creating the category"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@categories_blueprint.route('/update/<uuid:category_id>', methods=['PUT'])
def update_category(category_id):
    try:
        # Ensure request contains JSON data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()

        # Ensure there is data to update
        if not data:
            return jsonify({"error": "No data provided"}), 400
        
        # Check if category exists
        existing_category = Categories.get_category_by_id(category_id)
        if existing_category is None:
            return jsonify({"error": "Category does not exist"}), 404
        
        # Update category
        updated_category = Categories.update_category(
            category_id=category_id,
            name=data.get('name', existing_category.name),
            category_type=data.get('category_type', existing_category.category_type),
            description=data.get('description', existing_category.description)
        )
        if updated_category:
            current_app.logger.info(f"Category {existing_category.name} updated successfully")
            return jsonify({f"message": f"Category {existing_category.name} updated successfully", "status": "success"}), 200
        if updated_category is None:
            current_app.logger.error(f"An error occurred while updating the category")
            return jsonify({"error": "An error occurred while updating the category", "status": "error"}), 500
    except Exception as e:
        return jsonify({"error": str(e), "status": "error"}), 500

@categories_blueprint.route('/list', methods=['GET'])
def get_categories():
    try:
        categories = Categories.get_all_categories()
        if not categories:
            return jsonify({"data": {"categories": []}, "message": "No categories found"}), 200
        return jsonify({"data": {"categories": [category.to_dict() for category in categories]}, 
                        "message": "Categories retrieved successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500



    

@categories_blueprint.route('/load', methods=['POST'])
def load_categories():
    """Load categories from a JSON file."""
    def load_categories_from_file(file_path):
    # Load categories data from the specified JSON file
        try:
            with open(file_path, 'r') as file:
                categories_data = json.load(file)
                return categories_data
        except Exception as e:
            current_app.logger.error(f"An error occurred while loading categories from file: {str(e)}")
            return []
        
    try:
        data = request.get_json()
        # Example of how request data should look:
        # {
        #     "file_path": "/home/patrick/goalifai/app/files/default_categories.json"
        # }
        current_app.logger.info(f"Request data: {data}")
        if 'file_path' not in data:
            return jsonify({"error": "file_path is required"}), 400
        
        categories_data = load_categories_from_file(data['file_path'])
        if not categories_data:
            return jsonify({"error": "No data found in file"}), 400
        
        # Load categories
        Categories.batch_add_categories(categories_data)
        return jsonify({"message": "Categories loaded successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@categories_blueprint.route('/category_type/<category_type_name>', methods=['GET'])
def get_categories_by_category_type(category_type_name):
    """Fetch a category by its ID."""
    try:
        category = Categories.get_categories_by_category_type(category_type_name)
        if not category:
            return jsonify({"error": "Category not found"}), 404
        
        return jsonify({"data": {"categories": category}, "message": "Categories retrieved successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@categories_blueprint.route('/<uuid:category_id>', methods=['GET'])
def get_category_by_id(category_id):
    """Fetch a category by its ID."""
    try:
        category = Categories.get_category_by_id(category_id)
        if not category:
            return jsonify({"error": "Category not found"}), 404
        
        return jsonify(category.to_dict()), 200
    except NoResultFound:
        return jsonify({"error": "Category not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@categories_blueprint.route('/delete/<uuid:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """Delete a category by its ID."""
    try:
        # Check if category exists
        existing_category = Categories.get_category_by_id(category_id)
        if not existing_category:
            return jsonify({"error": "Category not found"}), 404
        
        # Delete category
        Categories.delete_category(category_id)
        current_app.logger.info(f"Category {existing_category.name} deleted successfully")
        return jsonify({"message": f"Category {existing_category.name} deleted successfully", "status": "success"}), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred while deleting the category: {str(e)}")
        return jsonify({"error": str(e), "status": "error"}), 500
@categories_blueprint.route('/update/<uuid:category_id>', methods=['PUT'])
def update_category_record(category_id):
    """Update the status of a category."""
    try:
        # Ensure request contains JSON data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()

        if not data or 'category_id' not in data:
            return jsonify({"error": "No data provided or 'category_id' is missing"}), 400
        
        # Check if category exists
        existing_category = Categories.get_category_by_id(category_id)
        if existing_category is None:
            return jsonify({"error": "Category does not exist"}), 404
        
        # Update category status
        updated_category = Categories.update_category(
            category_id=category_id,
            name=data.get('name', existing_category.name),
            category_type=data.get('category_type', existing_category.category_type),
            description=data.get('description', existing_category.description),
            user_id=data.get('user_id', existing_category.user_id)
        )
        if updated_category:
            current_app.logger.info(f"Category {existing_category.name} status updated successfully")
            return jsonify({"message": "Category status updated successfully", "status":"success"}), 200
        if updated_category is None:
            current_app.logger.error(f"An error occurred while updating the category status")
            return jsonify({"error": "An error occurred while updating the category status", "status":"error"}), 500

    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred: {str(e)}")
        return jsonify({"error": "An unexpected error occurred", "status":"error"}), 500

@categories_blueprint.route('/all_categories', methods=['GET'])
def get_all_categories():
    """Fetch all categories."""
    try:
        categories = Categories.get_all_categories()
        if not categories:
            return jsonify({"data": {"categories": []}, "message": "No categories found", "status":"success"}), 200
        return jsonify({"data": {"categories": [category.to_dict() for category in categories]}, 
                        "message": "Categories retrieved successfully", "status":"success"}), 200
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred: {str(e)}")
        return jsonify({"error": "An unexpected error occurred", "status":"error"}), 500

@categories_blueprint.route('/bulk_create', methods=['POST'])
def bulk_create_categories():
    """Bulk create categories."""
    try:
        data = request.get_json()
        if not data or 'transaction_categories' not in data:
            return jsonify({
                "status":"error",
                "message": "No categories data provided"}), 400

        categories_data = data['transaction_categories']
        if not isinstance(categories_data, list) or not categories_data:
            return jsonify({
                "status":"error",
                "message": "Categories data must be a non-empty list"}), 400
        
        skipped_categories = []
        created_categories = []
        # Validate each category entry
        for category in categories_data:
            if 'name' not in category or 'category_type' not in category:
                current_app.logger.info(f"Skipping invalid category entry: {category}")
                skipped_categories.append(category)
                continue
            # Check if category already exists (case-insensitive)
            existing_category = Categories.get_category_by_name(category['name'])
            if existing_category:
                current_app.logger.info(f"Category {category['name']} already exists. Skipping.")
                skipped_categories.append(category)
                continue
            # Create new category
            new_category = Categories.create_category(**category)
            if new_category:
                created_categories.append(new_category)
        return jsonify({"message": "Bulk category creation completed", 
                        "created_categories": [cat.to_dict() for cat in created_categories],
                        "skipped_categories": len(skipped_categories),
                        "status":"success"}), 201
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred: {str(e)}")
        return jsonify({"error": "An unexpected error occurred", "status":"error"}), 500


@categories_blueprint.route('/update_by_name', methods=['PUT'])
def update_category_by_name():
    """Update a category by its name."""
    try:
        # Ensure request contains JSON data
        if not request.is_json:
            return jsonify({"error": "Request must be JSON"}), 400
        
        data = request.get_json()

        if not data or 'name' not in data:
            return jsonify({"error": "No data provided or 'name' is missing"}), 400
        
        # Check if category exists
        existing_category = Categories.get_category_by_name(data.get('name'))
        current_app.logger.info(f"Existing category: {existing_category}")
        if existing_category is None:
            return jsonify({"error": "Category does not exist"}), 404
        
        # Update category
        updated_category = Categories.update_category_by_name(
            name=data['name'],
            category_type=data.get('category_type' if 'category_type' in data else None, existing_category.get('category_type')),
            description=data.get('description' if 'description' in data else None, existing_category.get('description')),
            user_id=data.get('user_id' if 'user_id' in data else None, existing_category.get('user_id')),
            examples=data.get('examples' if 'examples' in data else None, existing_category.get('examples'))
        )
        if updated_category:
            current_app.logger.info(f"Category {existing_category.name} updated successfully")
            return jsonify({"message": "Category updated successfully", "status":"success"}), 200
        if updated_category is None:
            current_app.logger.error(f"An error occurred while updating the category")
            return jsonify({"error": "An error occurred while updating the category", "status":"error"}), 500
        
    except Exception as e:
        current_app.logger.error(f"An unexpected error occurred: {str(e)}")
        return jsonify({"error": "An unexpected error occurred", "status":"error"}), 500