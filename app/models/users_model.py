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

class User(db.Model):
    __tablename__ = 'users'

    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(255), nullable=False)
    education_level = db.Column(db.String(255), nullable=True)  # e.g. 'Bachelor', 'Master', etc.
    date_of_birth = db.Column(Datetime, nullable=False)  # Store date of birth
    country_of_residence = db.Column(db.String(255), nullable=False)
    currency = db.Column(db.String(3), default="USD")  # Default currency is USD
    estimated_monthly_income = db.Column(db.Numeric, nullable=True)
    estimated_monthly_expenses = db.Column(db.Numeric, nullable=True)
    savings = db.Column(db.Numeric, default=0)  # Total savings of the user
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(datetime.timezone.utc))

    # Relationships
    goals = db.relationship('Goal', back_populates='user', cascade='all, delete')
    financial_profile = db.relationship('UserFinancialProfile', back_populates='user', uselist=False, cascade='all, delete')
    categories = db.relationship('Categories', back_populates='user', cascade='all, delete')

    def __repr__(self):
        return f"""
        user_id: {self.user_id}
        email: {self.email}
        first_name: {self.first_name}
        last_name: {self.last_name}
        education_level: {self.education_level}
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
            'education_level': self.education_level,
            'date_of_birth': self.date_of_birth,
            'country_of_residence': self.country_of_residence,
            'currency': self.currency,
            'estimated_monthly_income': {self.estimated_monthly_expenses},
            'estimated_monthly_expenses': {self.estimated_monthly_expenses},
            'savings': {self.savings},
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def hash_password(password):
        salt = gensalt()
        hashed_pwd = hashpw(password.encode('utf-8'), salt)
        return hashed_pwd.decode('utf-8')
    
    def verify_password(self, password):
        if not self.password:
            return False
        return checkpw(password.encode('utf-8'), self.password.encode('utf-8'))
    
    @staticmethod
    def get_user_by_email(email):
        return User.query.filter_by(email=email).first()
    

    @staticmethod
    def get_user_by_id(user_id):
        return User.query.filter_by(user_id=user_id).first()
    
    @staticmethod
    def create_user(email, password, first_name, last_name, education_level, date_of_birth, country_of_residence, currency):
        """Create a user authenticated via the app"""
        hashed_pwd = User.hash_password(password)
        try:
            user = User(
                email=email, 
                password=hashed_pwd,
                first_name=first_name,
                last_name=last_name,
                education_level=education_level,
                date_of_birth=date_of_birth,
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
                expected_monthly_savings=expected_monthly_income - expected_monthly_expenses
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
    

class Degree(db.Model):
    """Degrees defined by the developer, e.g. 'Bachelor', 'Master', etc."""
    __tablename__ = 'degrees'
    degree_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)  # Optional description of the degree
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

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


class Education(db.Model):
    __tablename__ = 'education'

    education_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    institution_name = db.Column(db.String(255), nullable=False)
    degree_id = db.Column(UUID(as_uuid=True), db.ForeignKey('degrees.degree_id'), nullable=False)
    field_of_study = db.Column(db.String(255), nullable=False)
    start_date = db.Column(Datetime, nullable=False)
    end_date = db.Column(Datetime, nullable=True)  # Nullable if still ongoing
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='education', cascade='all, delete')
    degree = db.relationship('Degree', backref='education', lazy=True)

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
            'institution_name': self.institution_name,
            'degree': self.degree,
            'field_of_study': self.field_of_study,
            'start_date': self.start_date.isoformat(),
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def create_education(user_id, institution_name, degree, field_of_study, start_date, end_date=None):
        """Create a new education record for a user."""
        try:
            education = Education(
                user_id=user_id,
                institution_name=institution_name,
                degree=degree,
                field_of_study=field_of_study,
                start_date=start_date,
                end_date=end_date
            )
            db.session.add(education)
            db.session.commit()
            return education
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating education record: {str(e)}")
            return None