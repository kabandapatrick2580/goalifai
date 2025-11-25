from psycopg2 import IntegrityError
from app import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm.exc import NoResultFound
import uuid
from datetime import datetime
from datetime import datetime, timezone
from flask import current_app
from app import db
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from datetime import datetime
from flask import jsonify
from sqlalchemy import func
from sqlalchemy import extract
from decimal import Decimal



class CategoriesType(db.Model):
    """Represents a type of category, such as Income or Expense."""
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

        """Check for existing category type with the same name"""
        existing_category = CategoriesType.query.filter_by(name=name).first()
        if existing_category:
            raise ValueError(f"Category type with name '{name}' already exists")

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
    category_type = db.Column(db.String(255),db.ForeignKey("categories_type.name"), nullable=False, unique=False)  # Foreign key to CategoriesType.name
    description = db.Column(db.String(255), nullable=True)
    examples = db.Column(JSONB, nullable=True)  # New column to store examples as JSONB
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
            "type": self.category_type,
            "description": self.description,
            "created_at": self.created_at.isoformat(),
        }
    
    @staticmethod
    def create_category(**kwargs):
        """Create a new category with dynamic arguments passed as kwargs."""
        try:
            new_category = Categories(
                **kwargs
            )
            # Validate category type
            if 'category_type' in kwargs:
                category_type = kwargs['category_type'].strip()
                if not CategoriesType.query.filter_by(name=category_type).first():
                    raise ValueError(f"Category type '{category_type}' does not exist.")

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
        category = Categories.query.filter(
                db.func.lower(Categories.name) == db.func.lower(name.strip())
            ).first()
        return category.to_dict() if category else None

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
        return {"message": "Category deleted successfully", "status": "success"}

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
                category_type = category_data['category_type']
                print(category_type)
                print(type(category_type))
                if category_type not in [cat.name for cat in CategoriesType.get_all_category_types()]:
                    continue
                categories_data = Categories(
                    name=category_data['name'],
                    category_type=category_type,
                    description=category_data.get('description', '')
                )
                db.session.add(categories_data)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Error adding categories: {str(e)}")
        
    @staticmethod
    def get_categories_by_category_type(category_type_name):
        """Get categories by category type name."""
        # return an array of categories that match the category type name
        category_type_name = category_type_name.strip().lower()
        categories = Categories.query.filter(Categories.category_type.ilike(category_type_name)).all()
        if not categories:
            return []
        return [category.to_dict() for category in categories]

    @staticmethod
    def update_category_by_name(name, **kwargs):
        """Update a category by its name with dynamic arguments passed as kwargs."""
        category = Categories.query.filter(
                db.func.lower(Categories.name) == db.func.lower(name.strip())
            ).first()
        
        if not category:
            raise NoResultFound("Category not found")
        
        for key, value in kwargs.items():
            if isinstance(value, str):  # Remove leading/trailing whitespace for string inputs
                value = value.strip()

            if hasattr(category, key):  # Only update valid attributes
                setattr(category, key, value)
        db.session.commit()
        return category
    


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
    created_at = db.Column(db.DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = db.Column(db.DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=True)
    currency = db.Column(UUID(as_uuid=True), db.ForeignKey("currencies.id"), nullable=True)
    expected_transaction = db.Column(db.Boolean, default=True, nullable=False)  # True if expected, False if actual
    is_allocation_transaction = db.Column(db.Boolean, default=False, nullable=False)  # True if part of goal allocation
    expense_orientation_id = db.Column(UUID(as_uuid=True), db.ForeignKey("expense_orientations.id"), nullable=True)
    expense_beneficiary_id = db.Column(UUID(as_uuid=True), db.ForeignKey("expense_beneficiaries.id"), nullable=True)
    # Relationships
    user = db.relationship("User", back_populates="financial_records")
    category = db.relationship("Categories", back_populates="financial_records")
    currency_rel = db.relationship("Currency", backref="financial_records", lazy=True)
    expense_orientation = db.relationship("ExpenseOrientation", back_populates="transaction", lazy=True)
    expense_beneficiary = db.relationship("ExpenseBeneficiary", back_populates="financial_records", lazy=True)

    def __repr__(self):
        return f"<FinancialRecord(user_id={self.user_id}, record_type={self.record_type}, amount={self.amount}, expected={self.expected})>"

    def to_dict(self):
        return {
            "record_id": str(self.record_id),
            "user_id": str(self.user_id),
            "category_id": str(self.category_id),
            "category_name": self.category.name if self.category else None,
            "category_type": str(self.category.category_type) if self.category else None,
            "category_type_name": self.category.type.name if self.category and self.category.type else None,
            "amount": float(self.amount),
            "description": self.description,
            "recorded_at": self.recorded_at.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "currency": str(self.currency) if self.currency else None,
            "currency_code": self.currency_rel.code if self.currency_rel else None,
            "expected_transaction": self.expected_transaction,
            "is_allocation_transaction": self.is_allocation_transaction,
            "expense_orientation_name": self.expense_orientation.name if self.expense_orientation else None,
            "expense_beneficiary_name": self.expense_beneficiary.name if self.expense_beneficiary else None,
        }

    @staticmethod
    def create_record(user_id, category_id, amount, recorded_at, expected_transaction=False, description=None, currency_id=None, is_allocation_transaction=False, expense_orientation_id=None, expense_beneficiary_id=None):
        """Creates a new financial record (either expected or actual)."""
        try:
            new_record = FinancialRecord(
                user_id=user_id,
                category_id=category_id,
                amount=amount,
                expected_transaction=expected_transaction,
                currency=currency_id if currency_id else None,
                recorded_at=recorded_at,
                description=description.strip() if description else None,
                is_allocation_transaction=is_allocation_transaction,
                expense_orientation_id=expense_orientation_id,
                created_at=datetime.now(timezone.utc),
                expense_beneficiary_id=expense_beneficiary_id
            )
            db.session.add(new_record)
            db.session.commit()
            return new_record
        except IntegrityError as e:
            # Handle integrity errors, such as duplicate entries
            db.session.rollback()
            current_app.logger.error(f"Error creating financial record: {str(e)}")

            return jsonify({"error": "Failed to create financial record due to integrity error"}), 400
        
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
    
    @staticmethod
    def get_monthly_summary_list(user_id, year, month):
        """Get a summary of income and expenses for a given month."""
        from datetime import datetime

        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        # Query records within that month
        records = FinancialRecord.query.filter(
            FinancialRecord.user_id == user_id,
            FinancialRecord.recorded_at >= start_date,
            FinancialRecord.recorded_at < end_date
        ).order_by(FinancialRecord.recorded_at.asc()).all()
        if not records:
            return None
        return [record.to_dict() for record in records]

    @staticmethod
    def get_monthly_summary_totals(user_id, year, month):
        """
        Aggregates income and expenses for a given user and month.
        Returns totals for income, expense, and net balance.
        """
        try:
            income_sum = (
                db.session.query(func.coalesce(func.sum(FinancialRecord.amount), 0))
                .filter(
                    FinancialRecord.user_id == user_id,
                    extract('year', FinancialRecord.recorded_at) == year,
                    extract('month', FinancialRecord.recorded_at) == month,
                    FinancialRecord.category.has(Categories.category_type == 'Income'),
                    FinancialRecord.expected_transaction == False,
                    FinancialRecord.is_allocation_transaction == False
                )
                .scalar()
            )

            expense_sum = (
                db.session.query(func.coalesce(func.sum(FinancialRecord.amount), 0))
                .filter(
                    FinancialRecord.user_id == user_id,
                    extract('year', FinancialRecord.recorded_at) == year,
                    extract('month', FinancialRecord.recorded_at) == month,
                    FinancialRecord.category.has(Categories.category_type == 'Expense'),
                    FinancialRecord.expected_transaction == False,
                    FinancialRecord.is_allocation_transaction == False
                )
                .scalar()
            )

            return {
                "total_income": Decimal(income_sum),
                "total_expense": Decimal(expense_sum),
                "net_income": Decimal(income_sum) - Decimal(expense_sum)
            }
        except Exception as e:
            current_app.logger.error(f"Error calculating monthly summary totals: {str(e)}")
            return None
    @staticmethod
    def carry_over_surplus(user_id, surplus_amount, from_month):
        """
        Carry over surplus to the next month as income.
        """
        if surplus_amount <= 0:
            return None

        # Compute next month (e.g. from "2025-10" to "2025-11")
        year, month = map(int, from_month.split('-'))
        if month == 12:
            next_month = f"{year + 1}-01"
        else:
            next_month = f"{year}-{month + 1:02d}"

        carried_over_cat = Categories.get_category_by_name("Carried Over Surplus")

        new_record = FinancialRecord.create_record(
            user_id=user_id,
            amount=surplus_amount,
            category_id=carried_over_cat.get("category_id"),
            expected_transaction=False,
            description=f"Carried over surplus from {from_month}",
            recorded_at=datetime.now(timezone.utc),
        )

        current_app.logger.info(
            f"Carried over {surplus_amount} surplus from {from_month} to {next_month} for user {user_id}"
        )

        return new_record
    
    @staticmethod
    def get_income_records_by_user(user_id):
        """Fetch all income financial records for a user."""
        records = FinancialRecord.query.filter(
            FinancialRecord.user_id == user_id,
            FinancialRecord.category.has(Categories.category_type == 'Income')
        ).all()
        if not records:
            return None
        return records
    
    @staticmethod
    def get_expense_records_by_user(user_id):
        """Fetch all expense financial records for a user."""
        records = FinancialRecord.query.filter(
            FinancialRecord.user_id == user_id,
            FinancialRecord.category.has(Categories.category_type == 'Expense')
        ).all()
        if not records:
            return None
        return records

    @staticmethod
    def get_records_by_user_and_month(user_id, year, month):
        """Fetch all financial records for a user in a specific month."""
        records = FinancialRecord.query.filter(
            FinancialRecord.user_id == user_id,
            extract('year', FinancialRecord.recorded_at) == year,
            extract('month', FinancialRecord.recorded_at) == month,
            FinancialRecord.is_allocation_transaction == False
        ).all()
        if not records:
            return None
        return records