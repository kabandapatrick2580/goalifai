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



class CategoriesType(db.Model):
    """Represents a type of category, such as Income or Expense.    """

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
    """Represents a transaction category for a user, which can be of either an income or expense category type.
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
    financial_records = db.relationship("FinancialRecord", back_populates="category")

    def __repr__(self):
        return f"<Category(name={self.name}, type={self.type}, user_id={self.user_id})>"

    def to_dict(self):
        return {
            "id": self.category_id,
            "user_id": str(self.user_id) if self.user_id else None,
            "name": self.name,
            "category_type": str(self.category_type) if self.category_type else None,
            "category_type_name": self.type.name if self.type else None,
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
        
        allowed_types = CategoriesType.get_all_category_types()
        allowed_types = [cat.type_id for cat in allowed_types]  # Extract type_ids

        
        if not category:
            raise NoResultFound("Category not found")
        

        for key, value in kwargs.items():
            if key == "category_type" and value not in allowed_types:
                raise ValueError(f"Invalid category type: {value}")
            
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
                category_type_id = uuid.UUID(category_data['category_type'])
                print(category_type_id)
                print(type(category_type_id))
                if category_type_id not in [cat.type_id for cat in CategoriesType.get_all_category_types()]:
                    continue
                categories_data = Categories(
                    name=category_data['name'],
                    category_type=category_type_id,
                    description=category_data.get('description', '')
                )
                db.session.add(categories_data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Error adding categories: {str(e)}")
        
    @staticmethod
    def get_categories_by_category_type(category_type_id):

        try: 
            category_type_id_uuid = uuid.UUID(str(category_type_id))
        except ValueError:
            current_app.logger.error(f"Invalid UUID for category_type_id: {category_type_id}")
            return []  # Return empty list for invalid UUID
        """Get categories by category type ID."""
        # return an array of categories that match the category type ID
        categories = Categories.query.filter_by(category_type=category_type_id_uuid).all()
        if not categories:
            current_app.logger.warning(f"No categories found for category type ID: {category_type_id}")
            return {"status": "error", "message": "No categories found for this category type"}
        return {"status": "success", "categories": [category.to_dict() for category in categories]}



class FinancialRecord(db.Model):
    """
    Represents a financial transaction, including income or expense details.
    
    Attributes:
        record_id (UUID): Unique identifier for the record.
        user_id (UUID): Foreign key referencing the associated user.
        category_id (UUID): Foreign key referencing the associated category.
        record_type (Enum): The type of record (Income or Expense).
        amount (Numeric): The monetary value of the transaction.
        expected (Boolean): Indicates if the record is an expected value (True) or an actual recorded value (False).
        description (String): Optional description of the record.
        recorded_at (DateTime): The timestamp when the transaction was made.
        created_at (DateTime): The timestamp when the record was created.
        updated_at (DateTime): The timestamp when the record was last updated.
    """

    __tablename__ = "financial_records"

    record_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey("users.user_id"), nullable=False)
    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey("transaction_categories.category_id"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    description = db.Column(db.String(255), nullable=True)
    recorded_at = db.Column(db.DateTime, nullable=False)  # The date the transaction happened
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="financial_records")
    category = db.relationship("Categories", back_populates="financial_records")

    def __repr__(self):
        return f"<FinancialRecord(user_id={self.user_id}, record_type={self.record_type}, amount={self.amount}, expected={self.expected})>"

    def to_dict(self):
        return {
            "record_id": str(self.record_id),
            "user_id": str(self.user_id),
            "category_id": str(self.category_id),
            "record_type": self.record_type,
            "amount": float(self.amount),
            "description": self.description,
            "recorded_at": self.recorded_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @staticmethod
    def create_record(user_id, category_id, record_type, amount, recorded_at, expected=False, description=None):
        """Creates a new financial record (either expected or actual)."""
        try:
            new_record = FinancialRecord(
                user_id=user_id,
                category_id=category_id,
                record_type=record_type,
                amount=amount,
                recorded_at=recorded_at,
                description=description.strip() if description else None,
            )
            db.session.add(new_record)
            db.session.commit()
            return new_record
        except IntegrityError as e:
            # Handle integrity errors, such as duplicate entries
            db.session.rollback()
            current_app.logger.error(f"Error creating financial record: {str(e)}")
            return None
        
        except Exception as e:
            # Handle other exceptions
            db.session.rollback()
            current_app.logger.error(f"Unexpected error creating financial record: {str(e)}")
            return None

    @staticmethod
    def get_records_by_user(user_id):
        """Fetch all financial records for a user, optionally filtering by expected status."""
        query = FinancialRecord.query.filter_by(user_id=user_id)
        if query is not None:
            return query.all()

    @staticmethod
    def update_record(record_id, **kwargs):
        """Updates an existing financial record."""
        record = FinancialRecord.query.filter_by(record_id=record_id).first()
        if not record:
            raise NoResultFound("Financial record not found")

        for key, value in kwargs.items():
            if key == "record_type" and value not in {"Income", "Expense"}:
                raise ValueError("Invalid record type. Must be 'Income' or 'Expense'.")

            if isinstance(value, str):
                value = value.strip()  # Remove unnecessary whitespace

            if hasattr(record, key):
                setattr(record, key, value)

        db.session.commit()
        return record

    @staticmethod
    def delete_record(record_id):
        """Deletes a financial record."""
        record = FinancialRecord.query.filter_by(record_id=record_id).first()
        if not record:
            raise NoResultFound("Financial record not found")

        db.session.delete(record)
        db.session.commit()
        return True

