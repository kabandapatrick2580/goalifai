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
    
