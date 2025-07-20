#!/usr/bin/env python3
from app import app, db
from app.models.goal import Goal
from app.models.users_model import User, UserFinancialProfile
from app.models.financial import Categories, CategoriesType
# Create all tables if they don't exist
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)