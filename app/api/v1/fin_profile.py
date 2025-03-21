from flask import request, jsonify, Blueprint, current_app
from app.models.central import UserFinancialProfile
from app import db 
from datetime import datetime
import traceback 
from sqlalchemy.orm.exc import NoResultFound

fin_profile = Blueprint('financial_profile', __name__)
@fin_profile.route('/api/v1/financial_profile', methods=['POST'])
def create_profile():
    
