#!/usr/bin/env python3
from app import app, db
from app.models.client.goal import Goal
from app.models.client.users_model import User, UserFinancialProfile
from app.models.client.financial import Categories, CategoriesType
# Create all tables if they don't exist
with app.app_context():
    db.create_all()


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)