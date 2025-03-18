from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import logging

load_dotenv()

app = Flask(__name__)

# Load the database URI from environment variables
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
if not app.config['SQLALCHEMY_DATABASE_URI']:
    raise RuntimeError("SQLALCHEMY_DATABASE_URI is not set")

# Initialize db with the app after configuration
db = SQLAlchemy(app)



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
# Register blueprint
app.register_blueprint(user_blueprint)
app.register_blueprint(goal_blueprint)