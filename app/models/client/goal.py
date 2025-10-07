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
    goal_category = db.Column(UUID(as_uuid=True), db.ForeignKey('goal_categories.category_id'), nullable=True)

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
    priority = db.relationship("GoalPriority", back_populates="goals", lazy=True)
    status = db.relationship("GoalStatus", back_populates="goals", lazy=True)
    user = db.relationship("User", back_populates="goals")

    def __repr__(self):
        return f"<Goal(title='{self.title}', target={self.target_amount}, user_id={self.user_id})>"

    def to_dict(self):
        return {
            "goal_id": str(self.goal_id),
            "user_id": str(self.user_id),
            "title": self.title,
            "description": self.description,
            "category_id": self.goal_category,
            "target_amount": float(self.target_amount),
            "current_amount": float(self.current_amount),
            "monthly_contribution": float(self.monthly_contribution),
            "priority": {
                "priority_id": str(self.priority.priority_id) if self.priority else None,
                "name": self.priority.name if self.priority else None,
                "percentage": float(self.priority.percentage) if self.priority and self.priority.percentage else 0
            },
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "expected_completion_date": self.expected_completion_date.isoformat() if self.expected_completion_date else None,
            "funding_gap": float(self.funding_gap) if self.funding_gap else 0,
            "status": self.status.name if self.status else None,
            "is_completed": self.is_completed,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
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
            return [goal.to_dict() for goal in goals]
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

    @staticmethod
    def get_incomplete_goals(user_id):
        """Fetch all incomplete goals for a user."""
        try:
            goals = Goal.query.filter_by(user_id=user_id, is_completed=False).all()
            return jsonify({
                "message": "Incomplete goals retrieved successfully",
                "status": "success",
                "goals": [goal.to_dict() for goal in goals]
            }), 200
        except Exception as e:
            current_app.logger.error(f"Error fetching incomplete goals: {e}")
            return jsonify({"error": str(e)}), 500
        
    @staticmethod
    def get_all_goals(user_id):
        """Fetch all goals, optionally filtered by user."""
        try:
            goals = Goal.query.filter_by(user_id=user_id).all()
            if not goals:
                return None
            return [goal.to_dict() for goal in goals]
        except Exception as e:
            current_app.logger.error(f"Error fetching goals: {e}")
            return e

    
class GoalCategories(db.Model):
    """Model for goal categories."""
    __tablename__ = 'goal_categories'

    category_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False, unique=True)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)  # Nullable for system-wide categories
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # relationships
    user = db.relationship("User", back_populates="goal_categories")
    goals = db.relationship("Goal", backref="category_ref", lazy=True)

    def __repr__(self):
        return f"<GoalCategory(name='{self.name}')>"
    
    def to_dict(self):
        return {
            "category_id": str(self.category_id),
            "name": self.name,
            "description": self.description,
            "user_id": str(self.user_id) if self.user_id else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @staticmethod
    def create_category(name, user_id=None, description=None):
        """Create a new goal category."""
        try:
            category = GoalCategories(name=name, user_id=user_id, description=description)
            db.session.add(category)
            db.session.commit()
            return category.to_dict()
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating goal category: {e}")
            return e
        
    @staticmethod
    def get_category_by_id(category_id):
        category = GoalCategories.query.filter_by(category_id=category_id).first()
        if not category:
            return None
        return category.to_dict()

    @staticmethod
    def get_categories_by_user(user_id):
        """Fetch all categories for a specific user."""
        try:
            categories = GoalCategories.query.filter_by(user_id=user_id).all()
            return [category.to_dict() for category in categories]
        except Exception as e:
            current_app.logger.error(f"Error fetching categories for user {user_id}: {e}")
            return e
        
    @staticmethod
    def get_goal_category_by_name(name, user_id=None):
        """Fetch a goal category by name, optionally filtered by user."""
        try:
            if user_id:
                category = GoalCategories.query.filter_by(name=name, user_id=user_id).first()
            else:
                category = GoalCategories.query.filter_by(name=name, user_id=None).first()
            if not category:
                return None
            return category.to_dict()
        except Exception as e:
            current_app.logger.error(f"Error fetching goal category by name: {e}")
            return e

    @staticmethod
    def get_all_categories(user_id=None):
        """Fetch all goal categories, optionally filtered by user."""
        try:
            if user_id:
                categories = GoalCategories.query.filter((GoalCategories.user_id == user_id) | (GoalCategories.user_id.is_(None))).all()
            else:
                categories = GoalCategories.query.all()
            return [category.to_dict() for category in categories]
        except Exception as e:
            current_app.logger.error(f"Error fetching goal categories: {e}")
            return e
    
    @staticmethod
    def update_category(category_id, user_id=None, is_admin=False, **kwargs):
        """
        Update an existing goal category.
        - Admins can update system categories (user_id=None).
        - Users can only update their own categories.
        """
        try:
            category = GoalCategories.query.filter_by(category_id=category_id).first()
            if not category:
                return None

            # Check permissions
            if category.user_id is None and not is_admin:
                return {"error": "You are not allowed to update system categories."}
            if category.user_id is not None and category.user_id != user_id and not is_admin:
                return {"error": "You can only update your own categories."}

            # Apply updates
            for key, value in kwargs.items():
                if hasattr(category, key) and value is not None:
                    setattr(category, key, value)

            db.session.commit()
            return category.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating goal category: {e}")
            return {"error": str(e)}
        
    @staticmethod
    def delete_category(category_id, user_id=None, is_admin=False):
        """
        Delete a goal category.
        - Admins can delete system-wide categories (user_id=None).
        - Users can only delete their own categories.
        - If a category has linked goals, you may want to prevent deletion or cascade.
        """
        try:
            category = GoalCategories.query.filter_by(category_id=category_id).first()
            if not category:
                return {"error": "Category not found."}

            # Permission check
            if category.user_id is None and not is_admin:
                return {"error": "You are not allowed to delete system categories."}
            if category.user_id is not None and category.user_id != user_id and not is_admin:
                return {"error": "You can only delete your own categories."}

            # Optional: check if goals exist under this category
            if category.goals and not is_admin:
                return {"error": "This category has existing goals. Remove them first."}

            db.session.delete(category)
            db.session.commit()
            return {"message": f"Category '{category.name}' deleted successfully."}
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting goal category: {e}")
            return {"error": str(e)}

class GoalPriority(db.Model):
    """Model for goal priorities.
        - It defines the priority levels for goals, such as 'High', 'Medium', 'Low'.
        - Initial priorities are created by the system upon user registration with default values.
        - later on can be updated by the user or admin.
        
    """
    __tablename__ = 'goal_priorities'

    priority_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=True)  # Nullable for system-wide priorities
    name = db.Column(db.String(50), nullable=False, unique=True)
    percentage = db.Column(db.Integer, nullable=True)  # Optional percentage field
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    # relationships
    goals = db.relationship("Goal", back_populates="priority", lazy=True)
    users = db.relationship("User", back_populates="goal_priorities")

    
    def __repr__(self):
        return f"<GoalPriority(name='{self.name}', user_id='{self.user_id}')>"
    
    def to_dict(self):
        return {
            "priority_id": str(self.priority_id),
            "user_id": str(self.user_id) if self.user_id else None,
            "name": self.name,
            "percentage": self.percentage,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }
    
    @staticmethod
    def create_priority(name, user_id=None, percentage=None):
        """Create a new goal priority."""
        try:
            priority = GoalPriority(name=name, user_id=user_id, percentage=percentage)
            db.session.add(priority)
            db.session.commit()
            return priority.to_dict()
        except IntegrityError as e:
            db.session.rollback()
            current_app.logger.error(f"Error creating goal priority: {e}")
            return e
        
    @staticmethod
    def get_priority_by_id(priority_id):
        priority = GoalPriority.query.filter_by(priority_id=priority_id).first()
        if not priority:
            return None
        return priority.to_dict()
    
    @staticmethod
    def get_priorities_by_user(user_id):
        """Fetch all default priorities and user-defined priorities for a specific user."""
        try:
            priorities = GoalPriority.query.filter((GoalPriority.user_id == user_id) & (GoalPriority.user_id.is_(None))).all()
            return [priority.to_dict() for priority in priorities]
        except Exception as e: 
            current_app.logger.error(f"Error fetching priorities for user {user_id}: {e}")
            return e
        
    @staticmethod
    def delete_user_defined_priority(priority_id, user_id):
        """Delete a user-defined priority. System-wide priorities cannot be deleted."""
        try:
            priority = GoalPriority.query.filter_by(priority_id=priority_id, user_id=user_id).first()
            if not priority:
                return None
            db.session.delete(priority)
            db.session.commit()
            return priority.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error deleting goal priority: {e}")
            return e
        
    @staticmethod
    def update_priority(priority_id, user_id=None, is_admin=False, **kwargs):
        """
        Update an existing goal priority.
        - Admins can update system priorities (user_id=None).
        - Users can only update their own priorities.
        """
        try:
            priority = GoalPriority.query.filter_by(priority_id=priority_id).first()
            if not priority:
                return None

            # Check permissions
            if priority.user_id is None and not is_admin:
                return {"error": "You are not allowed to update system priorities."}
            if priority.user_id is not None and priority.user_id != user_id and not is_admin:
                return {"error": "You can only update your own priorities."}

            # Apply updates
            for key, value in kwargs.items():
                if hasattr(priority, key) and value is not None:
                    setattr(priority, key, value)

            db.session.commit()
            return priority.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating goal priority: {e}")
            return {"error": str(e)}
        


class GoalStatus(db.Model):
    """example: 'Active', 'Completed', 'Cancelled', 'In Progress'"""
    __tablename__ = 'goal_statuses'

    status_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False)
    name = db.Column(db.String(50), nullable=False, unique=True)

    # relationships
    goals = db.relationship("Goal", back_populates="status", lazy=True)

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
        
    @staticmethod
    def get_status_by_name(name):
        """Fetch a goal status by name."""
        try:
            status = GoalStatus.query.filter_by(name=name).first()
            if not status:
                current_app.logger.error(f"Goal status with name '{name}' not found.")
                return None
            return status.to_dict()
        except Exception as e:
            current_app.logger.error(f"Error fetching goal status by name: {e}")
            return None

class MonthlyGoalAllocation(db.Model):
    """Tracks monthly allocation of funds to each goal for each user as per net income."""
    __tablename__ = "monthly_goal_allocations"

    allocation_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid4, unique=True, nullable=False)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('users.user_id'), nullable=False)
    goal_id = db.Column(UUID(as_uuid=True), db.ForeignKey('goals.goal_id'), nullable=False)

    # Financial tracking
    month = db.Column(db.String(7), nullable=False)  # Format: YYYY-MM
    allocated_amount = db.Column(NUMERIC(12, 2), nullable=False, default=0)
    # Metadata
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    is_finalized = db.Column(db.Boolean, default=False)
    is_deficit = db.Column(db.Boolean, default=False)
    # Relationships
    goal = db.relationship("Goal", backref=db.backref("allocations", lazy=True))
    user = db.relationship("User", backref=db.backref("goal_allocations", lazy=True))

    def __repr__(self):
        return f"<MonthlyGoalAllocation(goal_id='{self.goal_id}', month='{self.month}', allocated='{self.allocated_amount}')>"

    def to_dict(self):
        return {
            "allocation_id": str(self.allocation_id),
            "user_id": str(self.user_id),
            "goal_id": str(self.goal_id),
            "month": self.month,
            "allocated_amount": float(self.allocated_amount or 0),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
    
    @staticmethod
    def reallocate_funds(user_id, goal_id, month, allocated_amount):
        """Create or update a monthly goal allocation."""
        try:
            allocation = MonthlyGoalAllocation.query.filter_by(user_id=user_id, goal_id=goal_id, month=month).first()
            if allocation:
                allocation.allocated_amount = allocated_amount
            else:
                allocation = MonthlyGoalAllocation(
                    user_id=(user_id),
                    goal_id=(goal_id),
                    month=month,
                    allocated_amount=allocated_amount
                )
                db.session.add(allocation)
            db.session.commit()
            return allocation.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error reallocating funds: {e}")
            return None
        
    @staticmethod
    def record_deficit(user_id, month):
        """Record a deficit month where no allocations are made."""
        try:
            # Check if a deficit record already exists
            existing_deficit = MonthlyGoalAllocation.query.filter_by(user_id=user_id, goal_id=None, month=month).first()
            if existing_deficit:
                return existing_deficit.to_dict()

            deficit_record = MonthlyGoalAllocation(
                user_id=user_id,
                goal_id=None,  # No specific goal for deficit
                month=month,
                allocated_amount=0
            )
            db.session.add(deficit_record)
            db.session.commit()
            return deficit_record.to_dict()
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error recording deficit: {e}")
            return None
        
    @staticmethod
    def finalize_monthly_allocations(month):
        allocations = MonthlyGoalAllocation.query.filter_by(month=month, is_finalized=False).all()
        if not allocations:
            return None
        try:
            for allocation in allocations:
                goal = Goal.query.get(allocation.goal_id)
                if goal:
                    goal.current_amount += allocation.allocated_amount
                    goal.funding_gap = Goal.calculate_funding_gap(goal.target_amount, goal.current_amount)
                    if goal.funding_gap == 0:
                        goal.is_completed = True
                        goal.is_active = False
                    db.session.add(goal)
                allocation.is_finalized = True
                db.session.add(allocation)
            db.session.commit()
            return [allocation.to_dict() for allocation in allocations]
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error finalizing monthly allocations: {e}")
            return None
        
    @staticmethod
    def get_allocations_by_month(month):
        allocations = MonthlyGoalAllocation.query.filter_by(month=month).all()
        if not allocations:
            return None

        result = {}
        for allocation in allocations:
            goal_id = str(allocation.goal_id)
            if goal_id not in result:
                result[goal_id] = {
                    "goal_name": allocation.goal.title if allocation.goal else None,
                    "total_allocated": 0,
                    "allocations": []
                }

            result[goal_id]["allocations"].append({
                "allocation_id": str(allocation.allocation_id),
                "user_id": str(allocation.user_id),
                "month": allocation.month,
                "allocated_amount": float(allocation.allocated_amount or 0),
                "created_at": allocation.created_at.isoformat(),
                "updated_at": allocation.updated_at.isoformat(),
                "is_finalized": allocation.is_finalized,
                "is_deficit": allocation.is_deficit,
            })

            result[goal_id]["total_allocated"] += float(allocation.allocated_amount or 0)

        return result
