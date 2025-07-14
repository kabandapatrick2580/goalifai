from psycopg2 import IntegrityError
from app import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm.exc import NoResultFound
import uuid
from datetime import datetime
from bcrypt import hashpw, gensalt, checkpw
import hashlib
from datetime import datetime, timezone
from flask import current_app
from sqlalchemy import DateTime as Datetime
from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import traceback



class Goal(db.Model):
    __tablename__ = 'goals'

    goal_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)

    # Goal details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)  # e.g., Education, Finance, Travel
    
    # Financial details
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)  # Total amount required
    current_amount = db.Column(db.Numeric(12, 2), nullable=False, default=0)  # Amount saved so far
    monthly_contribution = db.Column(db.Numeric(12, 2), nullable=False, default=0)  # User-planned savings per month
    
    # Priority & Deadline
    priority = db.Column(db.Enum('High', 'Medium', 'Low', name='priority'), nullable=False, default='Medium')
    due_date = db.Column(db.DateTime, nullable=False)  # When the user wants to achieve the goal
    expected_completion_date = db.Column(db.DateTime, nullable=True)  # Realistic completion date based on funds
    
    # Feasibility Tracking
    funding_gap = db.Column(db.Numeric(12, 2), nullable=True, default=0)  # Shortfall in savings
    status = db.Column(db.Enum('Active', 'Completed', 'On Hold', 'Adjusted', name='goal_status'), nullable=False, default='Active')

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


    # Relationships
    user = db.relationship("User", back_populates="goals")

    # Helper method to calculate goal progress
    def calculate_progress(self):
        return (self.current_amount / self.target_amount) * 100 if self.target_amount else 0

    def __repr__(self):
        return f"""<Goal(
            goal_id={self.goal_id}, 
            user_id={self.user_id}, 
            title="{self.title}", 
            description="{self.description}", 
            category="{self.category}", 
            priority="{self.priority}", 
            target_amount={self.target_amount}, 
            current_amount={self.current_amount}, 
            monthly_contribution={self.monthly_contribution}, 
            due_date={self.due_date}, 
            expected_completion_date={self.expected_completion_date}, 
            funding_gap={self.funding_gap}, 
            status="{self.status}", 
            created_at={self.created_at}, 
            updated_at={self.updated_at}
        )>"""

    def to_dict(self):
        return {
            'goal_id': str(self.goal_id),
            'user_id': str(self.user_id),
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'target_amount': float(self.target_amount),
            'current_amount': float(self.current_amount),
            'monthly_contribution': float(self.monthly_contribution),
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'expected_completion_date': self.expected_completion_date.isoformat() if self.expected_completion_date else None,
            'funding_gap': float(self.funding_gap) if self.funding_gap is not None else None,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    @staticmethod
    def create_goal(user_id, title, target_amount, due_date, description=None):
        try:
            goal = Goal(
                user_id=user_id,
                title=title,
                target_amount=target_amount,
                due_date=due_date,
                description=description
            )
            db.session.add(goal)
            db.session.commit()
            return goal
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating goal:{str(e)}")
            current_app.logger.error(traceback.format_exc())
            return None
        
    @staticmethod
    def list_goals(user_id):
        return Goal.query.filter_by(user_id=user_id).all()
    
    @staticmethod
    def get_goal_by_id(goal_id):
        return Goal.query.filter_by(goal_id=goal_id).first()
    
    @staticmethod
    def get_all_goals():
        goals = Goal.query.all()
        goals_dict = []
        for goal in goals:
            goals_dict.append(goal.to_dict())
        return goals_dict

    @staticmethod
    def update_goal(goal_id, **kwargs):
        goal = Goal.query.filter_by(goal_id=goal_id).first()

        if not goal:
            raise NoResultFound("Goal not found")

        for key, value in kwargs.items():
            if hasattr(goal, key):  # Only update valid attributes
                setattr(goal, key, value)

        db.session.commit()
        return goal
    # List goals for a user
    @staticmethod
    def get_goal_by_id(user_id):
        return Goal.query.filter_by(user_id=user_id).all()

    # delete a goal
    @staticmethod
    def delete_goal(goal_id):
        goal = Goal.query.filter_by(goal_id=goal_id).first()
        if not goal:
            raise NoResultFound("Goal not found")
        db.session.delete(goal)
        db.session.commit()
        return {"message": "Goal deleted successfully"}
    @classmethod
    def calculate_monthly_goal_savings(cls, user_id):
        """Calculates the required monthly savings for all goals of a user based on due dates."""
        today = datetime.now()

        user_goals = cls.query.filter_by(user_id=user_id).all()

        goal_savings_plan = []
        total_required_savings = 0

        for goal in user_goals:
            remaining_amount = max(goal.target_amount - goal.current_amount, 0)
            months_left = max((goal.due_date - today).days // 30, 1)  # At least 1 month
            
            required_monthly_savings = remaining_amount / months_left if months_left else remaining_amount
            total_required_savings += required_monthly_savings

            goal_savings_plan.append({
                "goal_id": str(goal.goal_id),
                "goal_title": goal.title,
                "target_amount": float(goal.target_amount),
                "current_amount": float(goal.current_amount),
                "due_date": goal.due_date.strftime("%Y-%m-%d"),
                "months_left": months_left,
                "required_monthly_savings": round(required_monthly_savings, 2)
            })

        return {
            "monthly_goal_savings": goal_savings_plan,
            "total_required_savings": round(total_required_savings, 2)
        }
    
class CategoriesType(db.Model):
    __tablename__ = "categories_type"
    type_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=True)  # e.g., 'Income', 'Expense'
    description = db.Column(db.String(255), nullable=True)
    def __repr__(self):
        return f"<CategoriesType(type_id={self.type_id}, name='{self.name}', description='{self.description}')>"
    
    def to_dict(self):
        return {
            "id": self.type_id,
            "name": self.name,
            "description": self.description,
        }
    @staticmethod
    def get_all_category_types():
        """Get all category types."""
        return CategoriesType.query.all()
    
    @staticmethod
    def create_category_type(name, description=None):
        """Create a new category type."""
        try:
            new_type = CategoriesType(name=name, description=description)
            db.session.add(new_type)
            db.session.commit()
            return new_type
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating category type: {str(e)}")
            raise Exception(f"Error creating category type: {str(e)}")

    @staticmethod
    def update_category_type(type_id, **kwargs):
        """Update an existing category type.

        Args:
            type_id (int): The ID of the category type to update.
            **kwargs: Key-value pairs of fields to update (e.g., name).

        Returns:
            dict: Success message with the updated category type.

        Raises:
            NoResultFound: If the category type with the given type_id is not found.
            ValueError: If the input validation fails (e.g., duplicate name).
            IntegrityError: If a database integrity constraint is violated.
        """
        category_type = CategoriesType.query.filter_by(type_id=type_id).first()
        
        if not category_type:
            raise NoResultFound("Category type not found")

        # Validate inputs
        if "name" in kwargs:
            new_name = kwargs["name"].strip() if isinstance(kwargs["name"], str) else kwargs["name"]
            if not new_name:
                raise ValueError("Name cannot be empty")
            if len(new_name) > 100:  # Adjust based on schema
                raise ValueError("Name cannot exceed 100 characters")
            
            # Check for duplicate name (excluding the current record)
            existing_category = CategoriesType.query.filter(
                CategoriesType.name == new_name,
                CategoriesType.type_id != type_id
            ).first()
            if existing_category:
                raise ValueError(f"Category type with name '{new_name}' already exists")

        try:
            for key, value in kwargs.items():
                if hasattr(category_type, key):
                    if isinstance(value, str):
                        value = value.strip()  # Remove unnecessary whitespace
                    setattr(category_type, key, value)
            db.session.commit()
            return {"message": f"Category type '{category_type.name}' updated successfully"}
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Database integrity error updating category type {type_id}: {str(e)}")
            raise ValueError("Update failed due to duplicate name or other constraint violation")
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error updating category type {type_id}: {str(e)}")
            raise
    
    @staticmethod
    def delete_category_type(type_id):
        """Delete a category type by type_id."""
        category_type = CategoriesType.query.filter_by(type_id=type_id).first()
        if not category_type:
            raise NoResultFound("Category type not found")
        db.session.delete(category_type)
        db.session.commit()
        return {"message": "Category type deleted successfully"}

    @staticmethod
    def get_category_type_by_id(type_id):
        """Get a category type by its ID."""
        return CategoriesType.query.filter_by(type_id=type_id).first()
    

class Categories(db.Model):
    """Represents a transaction category for a user, which can be either an income or expense category.
        Example categories: 'Salary', 'Groceries', 'Utilities', etc.
        Each category is associated with a user and has a type (Income or Expense).
    """
    __tablename__ = "transaction_categories"
    category_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.user_id"), nullable=True)  
    name = db.Column(db.String(100), nullable=False)
    category_type = db.Column(db.ForeignKey("categories_type.type_id"), nullable=False)  # Foreign key to CategoriesType
    description = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # Relationship (User can have multiple categories)
    user = db.relationship("User", back_populates="categories")
    type = db.relationship("CategoriesType", backref="categories", lazy=True)  #

    def __repr__(self):
        return f"<Category(name={self.name}, type={self.type}, user_id={self.user_id})>"

    def to_dict(self):
        return {
            "id": self.category_id,
            "user_id": str(self.user_id) if self.user_id else None,
            "name": self.name,
            "type": self.category_type,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }
    
    @staticmethod
    def create_category(**kwargs):
        """Create a new category with dynamic arguments passed as kwargs."""
        try:
            name = kwargs.get("name")
            category_type = kwargs.get("category_type")
            description = kwargs.get("description", None)
            user_id = kwargs.get("user_id", None)
            new_category = Categories(
                name=name,
                category_type=category_type,
                description=description,
                user_id=user_id
            )

            db.session.add(new_category)
            db.session.commit()
            return new_category
        except Exception as e:
           db.session.rollback()
           raise Exception(f"Error creating category: {str(e)}")
        
    @staticmethod
    def get_category_by_id(category_id):
        """get category by category_id"""
        return Categories.query.filter_by(category_id=category_id).first()
    
    @staticmethod
    def get_category_by_name(name):
        """get category by name"""
        return Categories.query.filter_by(name=name).first()
    
    @staticmethod
    def get_all_categories():
        """Get all categories"""
        return Categories.query.all()
    
    @staticmethod
    def update_category(category_id, **kwargs):
        """Update a category with dynamic arguments passed as kwargs."""
        category = Categories.query.filter_by(category_id=category_id).first()
        
        allowed_types = {"Income", "Expense"}

        
        if not category:
            raise NoResultFound("Category not found")
        

        for key, value in kwargs.items():
            if key == "category_type" and value not in allowed_types:
                raise ValueError(f"Invalid category type: {value}. Must be one of {allowed_types}")
            
            if isinstance(value, str):  # Remove leading/trailing whitespace for string inputs
                value = value.strip()

            if hasattr(category, key):  # Only update valid attributes
                setattr(category, key, value)
        db.session.commit()
        return category
    
    @staticmethod
    def delete_category(category_id):
        """Delete a category by category_id."""
        category = Categories.query.filter_by(category_id=category_id).first()
        if not category:
            raise NoResultFound("Category not found")
        db.session.delete(category)
        db.session.commit()
        return {"message": "Category deleted successfully"}
    
    @staticmethod
    def batch_add_categories(categories_data):
        """Batch insert categories into the database."""
        try:
            for category_data in categories_data:
                # filter out existing categories
                existing_category = Categories.get_category_by_name(category_data['name'])
                if existing_category:
                    continue
                # if not Income or expense skip
                if category_data['type'] not in ['Income', 'Expense']:
                    continue
                categories_data = Categories(
                    name=category_data['name'],
                    category_type=category_data['type'],
                    description=category_data.get('description', '')
                )
                db.session.add(categories_data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Error adding categories: {str(e)}")
        