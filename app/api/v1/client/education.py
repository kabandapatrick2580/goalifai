from app.models.client.users_model import Education, User, Degree
from flask import Blueprint, request, jsonify, current_app
import traceback

education_blueprint = Blueprint('education', __name__)

@education_blueprint.route('/api/v1/education', methods=['POST'])
def create_education():
    try:
        data = request.get_json()
        required_fields = ['user_id', 'institution_name', 'degree_id', 'field_of_study', 'start_date']

        # Validate required fields
        for field in required_fields:
            if field not in data:
                return jsonify({"status":"error", "message": f"'{field}' is required"}), 400
        
        # Check if user exists
        existing_user = User.get_user_by_id(data['user_id']) 
        if existing_user is None:
            current_app.logger.info(f"User with id {data['user_id']} does not exist")
            return jsonify({"status": "error", "message": "User does not exist"}), 400
        
        # Check if degree exists
        existing_degree = Degree.get_degree_by_id(data['degree_id'])
        if existing_degree is None:
            current_app.logger.info(f"Degree with id {data['degree_id']} does not exist")
            return jsonify({
                "status": "error", 
                "message": "Degree does not exist"}
                ), 400
        # check if the education already exists
        existing_education = Education.get_education_by_user_and_degree(data['user_id'], data['degree_id'])
        if existing_education:
            current_app.logger.info(f"Education record for user {data['user_id']} and degree {data['degree_id']} already exists")
            return jsonify({
                "status": "error", 
                "message": "Education record already exists for this user and degree"
            }), 400
        # Create education record
        education = Education.create_education(
            user_id=data['user_id'],
            institution_name=data['institution_name'].strip(),
            degree_id=data['degree_id'],
            field_of_study=data['field_of_study'].strip(),
            start_date_str=data['start_date'],
            end_date_str=data.get('end_date','') 
        )
        if education is None:
            current_app.logger.error("An error occurred while creating the education record")
            return jsonify({"status": "error", "message": "An error occurred while creating the education record"}), 500        
        current_app.logger.info(f"Education record for user {data['user_id']} created successfully")
        return jsonify({
            "status": "success",
            "message": "Education record created successfully",
        }), 201
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "Something went wrong"}), 500
    
@education_blueprint.route('/api/v1/education/<uuid:education_id>', methods=['PUT'])
def update_education(education_id):
    try:
        # Ensure request contains JSON data
        if not request.is_json:
            return jsonify({"status": "error", "message": "Request must be JSON"}), 400
        
        data = request.get_json()

        # Ensure there is data to update
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400

        # Find and update the education record
        updated_education = Education.update_education(education_id=education_id, **data)

        if not updated_education:
            return jsonify({"status": "error", "message": "Education record not found"}), 404

        current_app.logger.info(f"Education record {education_id} updated successfully")
        return jsonify({
            "status": "success",
            "message": "Education record updated successfully",
            "data": updated_education.to_dict()
        }), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "Something went wrong"}), 500
    
@education_blueprint.route('/api/v1/education/<uuid:education_id>', methods=['DELETE'])
def delete_education(education_id):
    try:
        response = Education.delete_education(education_id)
        if response is None:
            return jsonify({"status": "error", "message": "Education record not found"}), 404
        current_app.logger.info(f"Education record {education_id} deleted successfully")
        return jsonify({
            "status": "success",
            "message": "Education record deleted successfully"
        }), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "Something went wrong"}), 500
    
@education_blueprint.route('/api/v1/education/user/<uuid:user_id>', methods=['GET'])
def get_education_by_user(user_id):
    try:
        educations = Education.get_education_by_user(user_id)
        if not educations:
            return jsonify({"status": "error", "message": "No education records found for this user"}), 404
        
        user_educations = [education.to_dict() for education in educations]
        current_app.logger.info(f"Retrieved {len(user_educations)} education records for user {user_id}")
        return jsonify({
            "status": "success",
            "data": user_educations
        }), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "Something went wrong"}), 500
    
@education_blueprint.route('/api/v1/educations', methods=['GET'])
def list_all_educations():
    try:
        educations = Education.get_all_educations()
        if not educations:
            return jsonify({"status": "error", "message": "No education records found"}), 404
        
        all_educations = [education.to_dict() for education in educations]
        current_app.logger.info(f"Retrieved {len(all_educations)} education records")
        return jsonify({
            "status": "success",
            "data": all_educations,
            "size": len(all_educations)
        }), 200
    except Exception as e:
        current_app.logger.error(f"An error occurred: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "Something went wrong"}), 500