from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import logging
from flask_migrate import Migrate

load_dotenv()

app = Flask(__name__)

# Load the database URI from environment variables
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
if not app.config['SQLALCHEMY_DATABASE_URI']:
    raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set")

# Initialize db with the app after configuration
db = SQLAlchemy(app)

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

from app.api.v1.users import user_blueprint
from app.api.v1.goals import goal_blueprint
from app.api.v1.fin_profile import fin_profile
from app.api.v1.categories import categories_blueprint
from app.api.v1.category_types import cat_types_blueprint
from app.api.v1.degree import degree_blue_print
from app.api.v1.education import education_blueprint
from app.api.v1.financial_records import financial_records_blueprint
# Register blueprint
app.register_blueprint(user_blueprint)
app.register_blueprint(goal_blueprint)
app.register_blueprint(fin_profile)
app.register_blueprint(categories_blueprint)
app.register_blueprint(cat_types_blueprint)
app.register_blueprint(degree_blue_print)
app.register_blueprint(education_blueprint)
app.register_blueprint(financial_records_blueprint)