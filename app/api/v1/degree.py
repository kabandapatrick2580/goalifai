from flask import Blueprint, request, jsonify
from app.models.users_model import Degree
from flask import current_app
import traceback

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
                "status": "success",
                "message": f"{data['name']} Degree created successfully",
            }), 201
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"success": False, "message": str(e)}), 500
    
@degree_blue_print.route('/api/v1/degrees', methods=['GET'])
def get_degrees():
    try:
        degrees = Degree.get_all_degrees()
        if not degrees:
            return jsonify({"message": "No degrees found"}), 404
        
        return jsonify({
            "status": "success",
            "data": {
                "degrees": [degree.to_dict() for degree in degrees]
            },
            "message": "Degrees retrieved successfully"
        }), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500
    
@degree_blue_print.route('/api/v1/degrees/<uuid:degree_id>', methods=['PUT'])
def update_degree(degree_id):
    try:
        data = request.get_json()
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
        
        updated_degree = Degree.update_degree(degree_id=degree_id, **data)
        if not updated_degree:
            return jsonify({
                "status": "error",
                "message": "Degree not found"
            }), 404
        
        return jsonify(updated_degree.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500

@degree_blue_print.route('/api/v1/degrees/<uuid:degree_id>', methods=['DELETE'])
def delete_degree(degree_id):
    try:
        degree = Degree.get_degree_by_id(degree_id)
        if not degree:
            return jsonify({
                "status": "error",
                "message": "Degree not found"
            }), 404
        
        Degree.delete_degree(degree_id)
        current_app.logger.info(f"Degree {degree.name} deleted successfully")
        return jsonify({"message": f"Degree {degree.name} deleted successfully"}), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({
            "status": "error",
            "message": "Something went wrong try again later"
        }), 500
    

@degree_blue_print.route('/api/v1/degrees/<uuid:degree_id>', methods=['GET'])
def get_degree(degree_id):
    try:
        degree = Degree.get_degree_by_id(degree_id)
        if not degree:
            return jsonify({"error": "Degree not found"}), 404
        
        return jsonify(degree.to_dict()), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({
            "status": "error",
            "message": "Something went wrong try again later"
        }), 500

@degree_blue_print.route('/api/v1/degrees/search', methods=['GET'])
def search_degrees():
    try:
        query = request.args.get('query', '').strip().lower()
        if not query:
            return jsonify({"error": "Query parameter is required"}), 400
        
        degrees = Degree.search_degrees(query)
        if not degrees:
            return jsonify({"message": "No degrees found"}), 404
        
        return jsonify({
            "status": "success",
            "data": {
                "degrees": [degree.to_dict() for degree in degrees]
            },
            "message": "Degrees retrieved successfully"
        }), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        return jsonify({"error": str(e)}), 500


        