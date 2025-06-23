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

    record_type = db.Column(db.Enum("Income", "Expense"), nullable=False)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    description = db.Column(db.String(255), nullable=True)

    recorded_at = db.Column(db.DateTime, nullable=False)  # The date the transaction happened
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship("User", back_populates="financial_records")
    category = db.relationship("Category", back_populates="financial_records")

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
