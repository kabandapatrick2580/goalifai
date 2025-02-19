from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from bcrypt import hashpw, gensalt, checkpw
import hashlib


class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=True)
    auth_method = db.Column(db.String(255), nullable=False)
    google_id = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(datetime.timezone.utc))

    def __repr__(self):
        """Return a representation of a user instance."""
        return f"""
        user_id: {self.user_id}
        email: {self.email}
        auth_method: {self.auth_method}
        google_id: {self.google_id}
        created_at: {self.created_at}
        updated_at: {self.updated_at}
        """
    
    def to_dict(self):
        """Return a dictionary representation of a user instance."""
        return {
            'user_id': str(self.user_id),
            'email': self.email,
            'auth_method': self.auth_method,
            'google_id': self.google_id,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def hash_password(password):
        """Hash the password"""
        # Generate a random salt
        salt = gensalt()

        # Hash the password using bcrypt
        hashed_pwd = hashpw(password.encode('utf-8'), salt)
        return hashed_pwd.decode('utf-8')  # Return as a string for storage
    
    def verify_password(self, password):
        """Verify the user's password"""
        if not self.password:
            return False  # No password set (e.g., Google OAuth user)
        return checkpw(password.encode('utf-8'), self.password.encode('utf-8'))
    
    @staticmethod
    def get_user_by_email(email):
        """Fetch a user by their email"""
        return User.query.filter_by(email=email).first()
    
    @staticmethod
    def create_google_user(email, google_id):
        """Create a user authenticated via Google OAuth"""
        user = User(
            email=email,
            auth_method='google',
            google_id=google_id
        )
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def create_app_user(email, password):
        """Create a user authenticated via the app"""
        hashed_password = User.hash_password(password)
        user = User(
            email=email,
            password=hashed_password,
            auth_method='app'
        )
        db.session.add(user)
        db.session.commit()
        return user

class Goals(db.Model):
    __tablename__ = 'goals'
    goal_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    due_date = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default= lambda: datetime.now(datetime.timezone.utc))