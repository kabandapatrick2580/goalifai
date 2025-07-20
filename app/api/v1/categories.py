from flask import request, jsonify, Blueprint, current_app
from app.models.financial import Categories
from app import db
from datetime import datetime
import traceback
from sqlalchemy.orm.exc import NoResultFound
import json

categories_blueprint = Blueprint('categories_api', __name__)
@categories_blueprint.route('/api/v1/categories/create', methods=['POST'])
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
            return jsonify({"message": "Category created successfully"}), 201
        if new_category is None:
            current_app.logger.error(f"An error occurred while creating the category")
            return jsonify({"error": "An error occurred while creating the category"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@categories_blueprint.route('/api/v1/categories/update/<uuid:category_id>', methods=['PUT'])
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
            return jsonify({"message": "Category updated successfully"}), 200
        if updated_category is None:
            current_app.logger.error(f"An error occurred while updating the category")
            return jsonify({"error": "An error occurred while updating the category"}), 500
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@categories_blueprint.route('/api/v1/categories/list', methods=['GET'])
def get_categories():
    try:
        
        categories = Categories.get_all_categories()
        if not categories:
            return jsonify({"message": "No categories found"}), 404
        return jsonify([category.to_dict() for category in categories]), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def load_cattegories_from_file(file_path):
    # Load categories data from the specified JSON file
    try:
        with open(file_path, 'r') as file:
            categories_data = json.load(file)
            return categories_data
    except Exception as e:
        current_app.logger.error(f"An error occurred while loading categories from file: {str(e)}")
        return []
    

@categories_blueprint.route('/api/v1/categories/load', methods=['POST'])
def load_categories():
    try:
        data = request.get_json()
        # Example of how data should look:
        # {
        #     "file_path": "/path/to/categories.json"
        # }
        if 'file_path' not in data:
            return jsonify({"error": "file_path is required"}), 400
        
        categories_data = load_cattegories_from_file(data['file_path'])
        if not categories_data:
            return jsonify({"error": "No data found in file"}), 400
        
        # Load categories
        Categories.batch_add_categories(categories_data)
        return jsonify({"message": "Categories loaded successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500