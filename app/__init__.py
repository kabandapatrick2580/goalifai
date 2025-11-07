from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import logging
from flask_migrate import Migrate
from flask_cors import CORS
from flask_jwt_extended import JWTManager

load_dotenv()

app = Flask(__name__)
CORS(
    app,
    supports_credentials=True,
    origins=os.getenv('CORS_ALLOWED_ORIGINS').split(',') if os.getenv('CORS_ALLOWED_ORIGINS') else []
)
     

# Load the database URI from environment variables
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')

# JWT Configuration
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['JWT_TOKEN_LOCATION'] = ['headers', 'cookies']
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 900))  # Default to 15 minutes
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = int(os.getenv('JWT_REFRESH_TOKEN_EXPIRES', 604800))  # Default to 7 days
app.config['JWT_COOKIE_SECURE'] = True if os.getenv('FLASK_ENV') == 'production' else False
app.config['JWT_COOKIE_CSRF_PROTECT'] = True
app.config['JWT_HTTPONLY'] = True


if not app.config['SQLALCHEMY_DATABASE_URI']:
    raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set")

# Initialize db with the app after configuration
db = SQLAlchemy(app)
jwt = JWTManager(app)
#initialize Flask-Migrate
migrate = Migrate(app, db)

# Other setup code if necessary

# Configure the Flask logger
handler = logging.FileHandler('app.log')
handler.setLevel(logging.INFO)  # Set the handler logging level

# Update formatter to include pathname, filename, and line number
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - [in %(pathname)s:%(lineno)d]')
handler.setFormatter(formatter)

app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

from app.api.v1.client.users import user_blueprint
from app.api.v1.goals.goals import goal_blueprint
from app.api.v1.client.fin_profile import fin_profile
from app.api.v1.hybrid.categories import categories_blueprint
from app.api.v1.central.category_types import cat_types_blueprint
from app.api.v1.client.degree import degree_blue_print
from app.api.v1.client.education import education_blueprint
from app.api.v1.client.financial_records import financial_records_blueprint
from app.api.v1.goals.goal_status import goal_status_bp
from app.api.v1.goals.goal_priorities import goal_priorities_blueprint
from app.api.v1.central.currencies import currency_bp
from app.api.v1.hybrid.user_access import user_access_bp
from app.api.v1.goals.goal_categories import goal_categories_blueprint
from app.api.v1.goals.goal_recalculation import allocations_blueprint

# Register blueprint
app.register_blueprint(user_blueprint)
app.register_blueprint(goal_blueprint)
app.register_blueprint(fin_profile)
app.register_blueprint(categories_blueprint)
app.register_blueprint(cat_types_blueprint)
app.register_blueprint(degree_blue_print)
app.register_blueprint(education_blueprint)
app.register_blueprint(financial_records_blueprint)
app.register_blueprint(goal_status_bp)
app.register_blueprint(goal_priorities_blueprint)
app.register_blueprint(currency_bp)
app.register_blueprint(user_access_bp)
app.register_blueprint(goal_categories_blueprint)
app.register_blueprint(allocations_blueprint)