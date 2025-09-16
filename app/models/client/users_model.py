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
from app.models.central.central import Degree
from uuid import uuid4
from werkzeug.security import generate_password_hash, check_password_hash



class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    date_of_birth = db.Column(Datetime, nullable=True)  # Store date of birth
    country_of_residence = db.Column(db.String(255), nullable=False)
    currency = db.Column(db.String(10), db.ForeignKey('currencies.code'), nullable=False)
    estimated_monthly_income = db.Column(db.Numeric, nullable=True)
    estimated_monthly_expenses = db.Column(db.Numeric, nullable=True)
    savings = db.Column(db.Numeric, default=0)  # Total savings of the user
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(datetime.timezone.utc))
    is_employed = db.Column(db.Boolean, default=True, nullable=True)
    employment_status = db.Column(UUID(as_uuid=True), db.ForeignKey('employment_statuses.status_id'), nullable=True)

     # Auth-related extras
    is_active = db.Column(db.Boolean, default=True)       # can be used to disable login
    is_admin = db.Column(db.Boolean, default=False)       # optional role control
    last_login = db.Column(db.DateTime, nullable=True)   # track last login time

    # Relationships
    goals = db.relationship('Goal', back_populates='user', cascade='all, delete')
    financial_profile = db.relationship('UserFinancialProfile', back_populates='user', uselist=False, cascade='all, delete')
    categories = db.relationship('Categories', back_populates='user', cascade='all, delete')
    educations = db.relationship('Education', back_populates='user', cascade='all, delete')
    financial_records = db.relationship('FinancialRecord', back_populates='user', cascade='all, delete')
    employment_statuses = db.relationship('EmploymentStatus', back_populates='users', cascade='all, delete')
    currencies = db.relationship('Currency', back_populates='users')

    def __repr__(self):
        return f"""
        user_id: {self.user_id}
        email: {self.email}
        first_name: {self.first_name}
        last_name: {self.last_name}
        date_of_birth: {self.date_of_birth}
        country_of_residence: {self.country_of_residence}
        currency: {self.currency}
        estimated_monthly_income: {self.estimated_monthly_expenses}
        estimated_monthly_expenses: {self.estimated_monthly_expenses}
        savings: {self.savings}
        created_at: {self.created_at}
        updated_at: {self.updated_at}
        """
    
    def to_dict(self):
        return {
            'user_id': str(self.user_id),
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'date_of_birth': self.date_of_birth,
            'country_of_residence': self.country_of_residence,
            'employment_status': self.employment_status,
            'is_employed': self.is_employed,
            'currency': self.currency,
            'estimated_monthly_income': {self.estimated_monthly_income},
            'estimated_monthly_expenses': {self.estimated_monthly_expenses},
            'savings': {self.savings},
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    # Password helpers
    @staticmethod
    def set_password(self, user_password: str):
        """Hashes the password and stores it."""
        self.password = generate_password_hash(user_password)
    @staticmethod
    def check_password(self, user_password: str) -> bool:
        """Verifies the given password against the stored hash."""
        return check_password_hash(self.password, user_password)

    @staticmethod
    def get_user_by_email(email):
        return User.query.filter_by(email=email).first()
    

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.filter_by(user_id=user_id).first()
    
    @staticmethod
    def create_user(email, password, first_name, last_name, country_of_residence, currency):
        """Create a user authenticated via the app"""
        hashed_pwd = User.hash_password(password)
        try:
            user = User(
                email=email, 
                password=hashed_pwd,
                first_name=first_name,
                last_name=last_name,
                country_of_residence=country_of_residence,
                currency=currency
                )
            db.session.add(user)
            db.session.commit()
            return user
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating user:{str(e)}")
            current_app.logger.error(traceback.format_exc())
            return None
    
    @staticmethod
    def get_all_users():
        return User.query.all()


class UserFinancialProfile(db.Model):
    """
    Represents a user's financial profile, including expected and actual financial data.
    If actual values are missing, expected values will be used for goal projections.
    """
    
    __tablename__ = 'user_financial_profiles'

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    
    # Expected financial values (User's planned budget)
    expected_monthly_income = db.Column(db.Numeric(12, 2), nullable=False, default=0)
    expected_monthly_expenses = db.Column(db.Numeric(12, 2), nullable=False, default=0)

    # Actual financial values (Recorded real data)
    actual_monthly_income = db.Column(db.Numeric(12, 2), nullable=True)  # Nullable, as user might not enter yet
    actual_monthly_expenses = db.Column(db.Numeric(12, 2), nullable=True)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship("User", back_populates="financial_profile")
    
    @property
    def monthly_income(self):
        """Return actual income if available, otherwise fallback to expected."""
        return self.actual_monthly_income if self.actual_monthly_income is not None else self.expected_monthly_income

    @property
    def monthly_expenses(self):
        """Return actual expenses if available, otherwise fallback to expected."""
        return self.actual_monthly_expenses if self.actual_monthly_expenses is not None else self.expected_monthly_expenses

    @property
    def monthly_savings(self):
        """Calculate savings dynamically as income minus expenses."""
        return self.monthly_income - self.monthly_expenses

    def to_dict(self):
        """Convert financial profile to dictionary format."""
        return {
            'id': str(self.id),
            'user_id': str(self.user_id),
            'expected_monthly_income': float(self.expected_monthly_income),
            'expected_monthly_expenses': float(self.expected_monthly_expenses),
            'actual_monthly_income': float(self.actual_monthly_income) if self.actual_monthly_income is not None else None,
            'actual_monthly_expenses': float(self.actual_monthly_expenses) if self.actual_monthly_expenses is not None else None,
            'monthly_income': float(self.monthly_income),  # Fallback applied here
            'monthly_expenses': float(self.monthly_expenses),  # Fallback applied here
            'monthly_savings': float(self.monthly_savings),  # Auto-calculated
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f"""<UserFinancialProfile(
            id={self.id}, 
            user_id={self.user_id}, 
            expected_monthly_income={self.expected_monthly_income}, 
            expected_monthly_expenses={self.expected_monthly_expenses}, 
            actual_monthly_income={self.actual_monthly_income}, 
            actual_monthly_expenses={self.actual_monthly_expenses}, 
            created_at={self.created_at}, 
            updated_at={self.updated_at}
        )>"""
    
    @staticmethod
    def update_financial_profile(profile_id, **kwargs):
        """
        Update the user's financial profile while maintaining fallback logic.
        Only valid attributes will be updated.
        """
        profile = UserFinancialProfile.query.filter_by(id=profile_id).first()

        if not profile:
            raise NoResultFound("Financial profile not found")

        # Update attributes dynamically
        allowed_fields = {'expected_monthly_income', 'expected_monthly_expenses', 'actual_monthly_income', 'actual_monthly_expenses'}
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(profile, key, value)

        db.session.commit()
        return profile
    
    @classmethod
    def create_financial_profile(cls, user_id, expected_monthly_income, expected_monthly_expenses):
        """Create a user's financial profile."""
        try:
            financial_profile = cls(
                user_id=user_id,
                expected_monthly_income=expected_monthly_income,
                expected_monthly_expenses=expected_monthly_expenses,
            )
            db.session.add(financial_profile)
            db.session.commit()
            return financial_profile
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating financial profile:{str(e)}")
            current_app.logger.error(traceback.format_exc())
            return None
        
    @classmethod
    def get_financial_profile_by_id(cls, profile_id):
        return cls.query.filter_by(id=profile_id).first()
    
    @classmethod
    def get_financial_profile_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).first()
    

class Education(db.Model):
    __tablename__ = 'education'

    education_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    institution_name = db.Column(db.String(255), nullable=False)
    degree_id = db.Column(UUID(as_uuid=True), db.ForeignKey('degrees.degree_id'), nullable=False)
    field_of_study = db.Column(db.String(255), nullable=False)
    start_date = db.Column(db.String(10), nullable=False)  # Format: YYYY-MM-DD
    end_date = db.Column(db.String(10), nullable=True)  # Format: YYYY-MM-DD, can be None if ongoing
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='educations')
    degree = db.relationship('Degree', back_populates='educations')
    def __repr__(self):
        return f"""
        education_id: {self.education_id}
        user_id: {self.user_id}
        institution_name: {self.institution_name}
        degree: {self.degree}
        field_of_study: {self.field_of_study}
        start_date: {self.start_date}
        end_date: {self.end_date}
        created_at: {self.created_at}
        updated_at: {self.updated_at}
        """
    
    def to_dict(self):
        return {
            'education_id': str(self.education_id),
            'user_id': str(self.user_id),
            'user_name': self.user.first_name + ' ' + self.user.last_name if self.user else None,
            'degree_id': str(self.degree_id) if self.degree else None,
            'institution_name': self.institution_name,
            'degree_name': self.degree.name if self.degree else None,
            'field_of_study': self.field_of_study,
            'start_date': self.start_date,
            'end_date': self.end_date if self.end_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def create_education(user_id, institution_name, degree_id, field_of_study, start_date_str, end_date_str):
        """Create a new education record for a user."""
        try:
            # Convert dates
            start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date() if end_date_str else None
            education = Education(
                user_id=User.query.get(user_id).user_id,
                institution_name=institution_name,
                degree_id=Degree.query.get(degree_id).degree_id,
                field_of_study=field_of_study,
                start_date=start_date,
                end_date=end_date or None 
            )
            db.session.add(education)
            db.session.commit()
            return education
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating education record: {str(e)}")
            return None
        
    @staticmethod
    def get_education_by_id(education_id):
        """Get an education record by its ID."""
        return Education.query.filter_by(education_id=education_id).first()
    
    @staticmethod
    def get_educations_by_user_id(user_id):
        """Get all education records for a user."""
        return Education.query.filter_by(user_id=user_id).all()
    
    @staticmethod
    def get_education_by_user_and_degree(user_id, degree_id):
        """Get an education record by user ID and degree ID."""
        return Education.query.filter_by(user_id=user_id, degree_id=degree_id).first()
    
    @staticmethod
    def update_education(education_id, **kwargs):
        """Update an existing education record."""
        education = Education.get_education_by_id(education_id)
        if not education:
            return None
        
        # Update attributes dynamically
        allowed_fields = {'institution_name', 'degree_id', 'field_of_study', 'start_date', 'end_date'}
        for key, value in kwargs.items():
            if key in allowed_fields and value is not None:
                setattr(education, key, value)

        db.session.commit()
        return education
    
    @staticmethod
    def delete_education(education_id):
        """Delete an education record by its ID."""
        education = Education.get_education_by_id(education_id)
        if not education:
            return None
        
        db.session.delete(education)
        db.session.commit()
        return education
    
    @staticmethod
    def get_all_educations():
        """Get all education records."""
        return Education.query.all()
    
    @staticmethod
    def get_education_by_user(user_id):
        """Get all education records for a user."""
        return Education.query.filter_by(user_id=user_id).all()
    

class GoalPriority(db.Model):
    """Model for goal priorities.
        - It defines the priority levels for goals, such as 'High', 'Medium', 'Low'.
        - Initial priorities are created by the system upon user registration with default values.
        - later on can be updated by the user or admin.
        
    """
    __tablename__ = 'goal_priorities'

    priority_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, unique=True)

    def __repr__(self):
        return f"<GoalPriority(name='{self.name}')>"

    def to_dict(self):
        return {
            "priority_id": str(self.priority_id),
            "name": self.name
        }

    @staticmethod
    def create_priority(name):
        """Create a new goal priority."""
        try:
            priority = GoalPriority(name=name)
            db.session.add(priority)
            db.session.commit()
            return priority.to_dict()
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Integrity error creating priority: {e.orig}")
            return {"error": "Priority already exists"}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating priority: {e}")
            return {"error": "An unexpected error occurred"}, 500
        
    @staticmethod
    def update_priority(priority_id):
        """Update an existing goal priority."""
        priority = GoalPriority.query.filter_by(priority_id=priority_id).first()
        if not priority:
            return {"error": "Priority not found"}, 404
        
        try:
            db.session.commit()
            return priority.to_dict()
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Integrity error updating priority: {e.orig}")
            return {"error": "Priority already exists"}, 400
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating priority: {e}")
            return {"error": "An unexpected error occurred"}, 500


