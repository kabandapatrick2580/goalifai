from flask import Blueprint, request, jsonify
from app.models.users_model import Degree
from flask import current_app

degree_blue_print = Blueprint('degree', __name__)
@degree_blue_print.route('/api/v1/create_degree', methods=['POST'])
def create_degree():
    try:
        data = request.get_json()
        required_fields = ['name']
        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"'{field}' is required"}), 400
            
        # check if degree already exists
        existing_degree = Degree.get_degree_by_name(data['name'])
        if existing_degree:
            return jsonify({"error": "Degree already exists"}), 400
        # Create degree
        degree = Degree.create_degree(
            name=data['name'].strip().lower(),
            description=data.get('description', '').strip()
        )
        if degree is None:
            return jsonify({"error": "An error occurred while creating the degree"}), 500
        else:
            current_app.logger.info(f"Degree {data['name']} created successfully")
            return jsonify({
                "message": f"{data['name']} Degree created successfully",
            }), 201
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

        