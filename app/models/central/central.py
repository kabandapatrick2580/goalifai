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
from uuid import uuid4
from app.utils.errors import handle_db_errors

class EmploymentStatus(db.Model):
    """Model for employment statuses, eg. self-employed, full-time, part-time, student, unemployed."""
    __tablename__ = 'employment_statuses'
    
    status_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    status_name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)  # Optional description of the employment status
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users = db.relationship('User', back_populates='employment_statuses', cascade='all, delete')

    def __repr__(self):
        return f"<EmploymentStatus(status_id={self.status_id}, status_name={self.status_name})>"
    
    def to_dict(self):
        return {
            'status_id': str(self.status_id),
            'status_name': self.status_name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def create_status(status_name, description=None):
        """Create a new employment status."""
        try:
            status = EmploymentStatus(status_name=status_name, description=description)
            db.session.add(status)
            db.session.commit()
            return status
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating employment status: {str(e)}")
            return None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error creating employment status: {str(e)}")
            return None

    @staticmethod
    def get_status_by_id(status_id):
        """Get an employment status by its ID."""
        return EmploymentStatus.query.filter_by(status_id=status_id).first()
    
    @staticmethod
    def get_all_statuses():
        """Get all employment statuses."""
        return EmploymentStatus.query.all()

    @staticmethod
    def get_status_by_name(name):
        """Get an employment status by its name."""
        return EmploymentStatus.query.filter_by(status_name=name.strip().lower()).first()

    @staticmethod
    def update_status(status_id, status_name=None, description=None):
        """Update an existing employment status."""
        status = EmploymentStatus.get_status_by_id(status_id)
        if not status:
            return None

    @staticmethod
    def delete_status(status_id):
        """Delete an employment status by its ID."""
        status = EmploymentStatus.get_status_by_id(status_id)
        if not status:
            return None

        db.session.delete(status)
        db.session.commit()
        return status

class Degree(db.Model):
    """Degrees defined by the developer, e.g. 'Bachelor', 'Master', etc."""
    __tablename__ = 'degrees'
    degree_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)  # Optional description of the degree
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    educations = db.relationship('Education', back_populates='degree', cascade='all, delete')

    def __repr__(self):
        return f"<Degree(degree_id={self.degree_id}, name={self.name})>"
    
    def to_dict(self):
        return {
            'degree_id': str(self.degree_id),
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    @staticmethod
    def create_degree(name, description=None):
        """Create a new degree."""
        try:
            degree = Degree(name=name, description=description)
            db.session.add(degree)
            db.session.commit()
            return degree
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating degree: {str(e)}")
            return None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error creating degree: {str(e)}")
            return None

    @staticmethod
    def get_degree_by_id(degree_id):
        """Get a degree by its ID."""
        return Degree.query.filter_by(degree_id=degree_id).first()
    
    @staticmethod
    def get_all_degrees():
        """Get all degrees."""
        return Degree.query.all()

    @staticmethod
    def get_degree_by_name(name):
        """Get a degree by its name."""
        return Degree.query.filter_by(name=name.strip().lower()).first()

    @staticmethod
    def update_degree(degree_id, name=None, description=None):
        """Update an existing degree."""
        degree = Degree.get_degree_by_id(degree_id)
        if not degree:
            return None
        
        if name:
            degree.name = name
        if description:
            degree.description = description
        
        db.session.commit()
        return degree

    @staticmethod
    def delete_degree(degree_id):
        """Delete a degree by its ID."""
        degree = Degree.get_degree_by_id(degree_id)
        if not degree:
            return None
        
        db.session.delete(degree)
        db.session.commit()
        return degree

class GoalStatus(db.Model):
    """example: 'Active', 'Completed', 'Cancelled', 'In Progress'"""
    __tablename__ = 'goal_statuses'

    status_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, unique=True)

    def __repr__(self):
        return f"<GoalStatus(name='{self.name}')>"

    def to_dict(self):
        return {
            "status_id": str(self.status_id),
            "name": self.name
        }

    @staticmethod
    def create_goal_status(name):
        """Create goal statuses"""
        try:
            goal_status = GoalStatus(name=name)
            db.session.add(goal_status)
            db.session.commit()
            return goal_status.to_dict()
        except Exception as e:
            current_app.logger.info(f"Error while adding goal status {e}")
            return  None

    @staticmethod
    def get_all_statuses():
        """Fetch all goal statuses ex:ample: 'Active', 'Completed', 'Cancelled', 'In Progress'."""
        try:
            statuses = GoalStatus.query.all()
            return statuses
        except Exception as e:
            current_app.logger.error(f"Error fetching goal statuses: {e}")
            return None   
    @staticmethod
    def update_status(status_id, name):
        """Update a goal status."""
        try:
            status = GoalStatus.query.filter_by(status_id=status_id).first()
            if not status:
                current_app.logger.error(f"Goal status with ID {status_id} not found.")
                return None
            
            status.name = name
            db.session.commit()
            return status.to_dict()
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating goal status: {e}")
            return None
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Unexpected error updating goal status: {e}")
            return None
        
    @staticmethod
    def delete_status(status_id):
        """Delete a goal status."""
        try:
            status = GoalStatus.query.filter_by(status_id=status_id).first()
            if not status:
                current_app.logger.error(f"Goal status with ID {status_id} not found.")
                return None
            
            db.session.delete(status)
            db.session.commit()
            return status.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting goal status: {e}")
            return None


class Currency(db.Model):
    __tablename__ = 'currencies'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = db.Column(db.String(50), nullable=False, unique=True)
    symbol = db.Column(db.String(10), nullable=True)
    code = db.Column(db.String(5), nullable=False, unique=True)

    # relationships
    users = db.relationship('User', back_populates='currencies')
    def __repr__(self):
        return f"<Currency {self.name} ({self.code})>"

    def __init__(self, name, symbol, code):
        self.name = name
        self.symbol = symbol
        self.code = code

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "symbol": self.symbol,
            "code": self.code,
        }
    
    @staticmethod
    def create_currency(name, symbol, code):
        try:
            new_currency = Currency(
                name=name,
                symbol=symbol if symbol else "",
                code=code,
            )
            db.session.add(new_currency)
            db.session.commit()
            return new_currency
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating currency: {str(e)}")
            return None

    @staticmethod
    def get_currency_by_id(currency_id):
        try:
            return Currency.query.filter_by(id=currency_id).one()
        except NoResultFound:
            return None
        
    @staticmethod
    def get_all_currencies():
        try:
            return Currency.query.all()
        except Exception as e:
            return None
        
    @staticmethod
    def get_currency_by_code(code):
        try:
            return Currency.query.filter_by(code=code).one()
        except NoResultFound:
            return None
        
    @staticmethod
    def get_currency_by_name(name):
        try:
            return Currency.query.filter_by(name=name).one()
        except NoResultFound:
            return None
        
    @staticmethod
    def delete_currency(currency_id):
        try:
            currency = Currency.get_currency_by_id(currency_id)
            if not currency:
                return None
            db.session.delete(currency)
            db.session.commit()
            return currency
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting currency: {str(e)}")
            return None