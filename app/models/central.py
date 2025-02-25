from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from bcrypt import hashpw, gensalt, checkpw
import hashlib
from datetime import datetime, timezone
from dateutil.relativedelta import relativedelta  # To calculate months between dates
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
class Goal(db.Model):
    __tablename__ = 'goals'
    goal_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    target_amount = db.Column(db.Numeric(12, 2), nullable=False)  # Amount user wants to achieve
    current_amount = db.Column(db.Numeric(12, 2), nullable=True, default=0)  # Amount user has saved so far
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc), onupdate=datetime.now)

    # Relationships
    user = db.relationship("User", back_populates="goals")

    # Helper method to calculate goal progress
    def calculate_progress(self):
        return (self.current_amount / self.target_amount) * 100 if self.target_amount else 0

    def __repr__(self):
        return f"""
        goal_id: {self.goal_id}
        user_id: {self.user_id}
        title: {self.title}
        description: {self.description}
        target_amount: {self.target_amount}
        current_amount: {self.current_amount}
        due_date: {self.due_date}
        created_at: {self.created_at}
        updated_at: {self.updated_at}
        """

    def to_dict(self):
        return {
        'goal_id': {self.goal_id},
        'user_id': {self.user_id},
        'title': {self.title},
        'description': {self.description},
        'target_amount': {self.target_amount},
        'current_amount': {self.current_amount},
        'due_date': {self.due_date},
        'created_at': {self.created_at},
        'updated_at': {self.updated_at}
        }
    
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

"""
class Transaction(db.Model):
    __tablename__ = 'transactions'
    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    amount = db.Column(db.Numeric, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey('categories.category_id'))
    payment_method = db.Column(db.String(50))
    transaction_date = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    description = db.Column(db.Text)
    is_recurring = db.Column(db.Boolean, default=False)
    goal_id = db.Column(UUID(as_uuid=True), db.ForeignKey('goals.goal_id'), nullable=True)  # Link to a goal (optional)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="transactions")
    category = db.relationship("Category", back_populates="transactions")
    goal = db.relationship("Goal", back_populates="transactions", cascade="all, delete")

    
    def to_dict(self):
        return {
        'transaction_id': {self.transaction_id},
        'user_id': {self.user_id},
        'amount': {self.amount},
        'type': {self.type},
        'category_id': {self.category_id},
        'payment_method': {self.payment_method},
        'transaction_date': {self.transaction_date},
        'description': {self.description},
        'goal_id': {self.goal_id} 
        }

class TransactionProjection(db.Model):
    __tablename__ = 'transaction_projections'

    projection_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    category_id = db.Column(UUID(as_uuid=True), db.ForeignKey('categories.category_id'), nullable=True)
    goal_id = db.Column(UUID(as_uuid=True), db.ForeignKey('goals.goal_id'), nullable=True)  # Optional link to a goal
    amount = db.Column(db.Numeric, nullable=False)
    type = db.Column(db.String(10), nullable=False)  # 'income' or 'expense'
    projection_date = db.Column(db.DateTime, nullable=False)  # When is this projection happening
    description = db.Column(db.Text)
    is_recurring = db.Column(db.Boolean, default=False)  # Whether this projection is recurring
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))

    # Relationships
    user = db.relationship("User", back_populates="transaction_projections")
    category = db.relationship("Category", back_populates="transaction_projections")
    goal = db.relationship("Goal", back_populates="transaction_projections", cascade="all, delete")

    def to_dict(self):
        return {
            'projection_id': str(self.projection_id),
            'user_id': str(self.user_id),
            'category_id': str(self.category_id),
            'goal_id': str(self.goal_id) if self.goal_id else None,
            'amount': self.amount,
            'type': self.type,
            'projection_date': self.projection_date,
            'description': self.description,
            'is_recurring': self.is_recurring
        }
"""

"""
class Category(db.Model):
    __tablename__ = 'categories'
    category_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    name = db.Column(db.String(255), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    is_income = db.Column(db.Boolean, nullable=False, default=False)  # True for income, False for expenses
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))

    transactions = db.relationship("Transaction", back_populates="category")

    def __repr__(self):
        return f"Category(name={self.name}, is_income={self.is_income})"
    
    def to_dict(self):
        return {
            'category_id': {self.category_id},
            'name': {self.name},
            'description': {self.description},
            'is_income': {self.is_income},
            'created_at': {self.created_at}
        }
"""