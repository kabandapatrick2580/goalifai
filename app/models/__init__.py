from flask_sqlalchemy import SQLAlchemy
import os
from flask import Flask

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')

db = SQLAlchemy(app)