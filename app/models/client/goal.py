from psycopg2 import IntegrityError
from app import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm.exc import NoResultFound
import uuid
from datetime import datetime
from bcrypt import hashpw, gensalt, checkpw
import hashlib
from datetime import datetime, timezone
from flask import current_app, jsonify
from sqlalchemy import DateTime as Datetime
from app import db
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
import traceback
from sqlalchemy.dialects.postgresql import UUID, NUMERIC
from uuid import uuid4


class Goal(db.Model):

    """Model for user-defined goals."""
    __tablename__ = 'goals'

    goal_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)

    # Goal details
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)  # e.g., Education, Finance, Travel

    # Financial details
    target_amount = db.Column(NUMERIC(12, 2), nullable=False)
    current_amount = db.Column(NUMERIC(12, 2), nullable=True, default=0)
    monthly_contribution = db.Column(NUMERIC(12, 2), nullable=True, default=0)

    # Priority & Deadline (via FK)
    priority_id = db.Column(UUID(as_uuid=True), db.ForeignKey('goal_priorities.priority_id'), nullable=True)
    due_date = db.Column(db.DateTime, nullable=True)
    expected_completion_date = db.Column(db.DateTime, nullable=True)

    # Feasibility Tracking
    funding_gap = db.Column(NUMERIC(12, 2), nullable=True, default=0)

    # Status (via FK)
    goal_status_id = db.Column(UUID(as_uuid=True), db.ForeignKey('goal_statuses.status_id'), nullable=True)

    # Control Flags
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)

    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Optional relationships (backrefs)
    priority = db.relationship("GoalPriority", backref="goals", lazy=True)
    status = db.relationship("GoalStatus", backref="goals", lazy=True)
    user = db.relationship("User", back_populates="goals")

    def __repr__(self):
        return f"<Goal(title='{self.title}', target={self.target_amount}, user_id={self.user_id})>"

    def to_dict(self):
        return {
            "goal_id": str(self.goal_id),
            "user_id": str(self.user_id),
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "target_amount": float(self.target_amount),
            "current_amount": float(self.current_amount),
            "monthly_contribution": float(self.monthly_contribution),
            "priority": self.priority.name if self.priority else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "expected_completion_date": self.expected_completion_date.isoformat() if self.expected_completion_date else None,
            "funding_gap": float(self.funding_gap) if self.funding_gap else 0,
            "status": self.status.name if self.status else None,
            "is_completed": self.is_completed,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @staticmethod
    def create_goal(user_id, **kwargs):
        """Create a new goal."""
        try:
            goal = Goal(user_id=user_id, **kwargs)
            db.session.add(goal)
            db.session.commit()
            return goal.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating goal: {e}")
            return e
    
    @staticmethod
    def calculate_funding_gap(target_amount, current_amount):
        """Calculate the funding gap for a goal."""
        if target_amount is None or current_amount is None:
            return None
        return max(0, target_amount - current_amount)

    @staticmethod
    def update_goal(self, **kwargs):
        for field, value in kwargs.items():
            setattr(self, field, value)
        try:
            self.updated_at = datetime.now(timezone.utc)
            self.funding_gap = self.calculate_funding_gap(self.target_amount, self.current_amount)
            db.session.commit()
            return self.to_dict()
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating goal: {e}")
            return e
    @staticmethod
    def get_goals_by_user(user_id):
        goals = Goal.query.filter_by(user_id=user_id).all()
        if not goals:
            return None
        return goals.to_dict()

    @staticmethod
    def get_goal_by_id(goal_id):
        goal = Goal.query.filter_by(goal_id=goal_id).first()
        if not goal:
            return None
        return goal.to_dict()
    
    @staticmethod
    def delete_goal(goal_id):
        goal = Goal.query.filter_by(goal_id=goal_id).first()
        if not goal:
            return None
        try:
            db.session.delete(goal)
            db.session.commit()
            return goal.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting goal: {e}")
            return EnvironmentError
        
    @staticmethod
    def get_active_goals(user_id):
        """Fetch all active goals for a user."""
        try:
            goals = Goal.query.filter_by(user_id=user_id, is_active=True).all()
            return goals.to_dict()
        except Exception as e:
            current_app.logger.error(f"Error fetching active goals: {e}")
            return e
        
    @staticmethod
    def get_completed_goals(user_id):
        """Fetch all completed goals for a user."""
        try:
            goals = Goal.query.filter_by(user_id=user_id, is_completed=True).all()
            return jsonify({
                "message": "Completed goals retrieved successfully",
                "status": "success",
                "goals": [goal.to_dict() for goal in goals]
            }), 200
        except Exception as e:
            current_app.logger.error(f"Error fetching completed goals: {e}")
            return jsonify({"error": str(e)}), 500
        


    