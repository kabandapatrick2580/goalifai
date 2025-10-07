from flask import Blueprint, jsonify, request
from app import db
from datetime import datetime, timezone
from app.models.client.goal import Goal, MonthlyGoalAllocation as GoalAllocation, GoalPriority
from decimal import Decimal
import traceback
from flask import current_app

allocations_blueprint = Blueprint('allocations_api', __name__, url_prefix='/api/v1/allocations')


@allocations_blueprint.route('/recalculate', methods=['POST'])
def recalculate_allocations():
    """
    Recalculate goal allocations for the user based on current income, expenses, and goal priorities.
    Expected JSON:
    {
        "user_id": "<uuid>",
        "total_income": 2000,
        "total_expense": 1200
    }
    """
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        total_income = Decimal(str(data.get("total_income", 0)))
        total_expense = Decimal(str(data.get("total_expense", 0)))

        if not user_id:
            current_app.logger.error("user_id is required for recalculation")
            return jsonify({"error": "user_id is required"}), 400

        net_income = total_income - total_expense
        current_month = datetime.now().strftime("%Y-%m")

        # Fetch user's active goals with priority
        goals = Goal.get_active_goals(user_id)
        current_app.logger.info(f"All goals for user {user_id}: {goals}")
        if not goals:
            current_app.logger.info(f"No active goals found for user {user_id}")
            return jsonify({"message": "No active goals found for user."}), 200

        # Sum all priority percentages (to normalize if needed)
        total_priority = sum(float(g['priority']['percentage']) for g in goals if g['priority'] and g['priority']['percentage'])

        allocations_summary = []

        for goal in goals:                
            if not goal["priority"] or not goal["priority"]["percentage"]:
                continue
            # Calculate proportional allocation
            weight = float(goal["priority"]["percentage"]) / total_priority
            amt_to_allocate = net_income * Decimal(str(weight))
            allocated_amount = amt_to_allocate if amt_to_allocate > 0 else Decimal('0.00') # No negative allocations

            # Record allocation
            try:
                allocation = GoalAllocation.reallocate_funds(
                    user_id=user_id,
                    goal_id=goal["goal_id"],
                    month=current_month,
                    allocated_amount=allocated_amount
                )
                if allocation:
                    allocations_summary.append({
                        "goal_id": str(goal["goal_id"]),
                        "goal_title": goal["title"],
                        "allocated_amount": float(allocated_amount)
                    })
                    current_app.logger.info(f"Allocated {allocated_amount} to goal {goal['title']} for user {user_id}")
                else:
                    current_app.logger.error(f"Failed to allocate funds to goal {goal['title']} for user {user_id}")
                    return jsonify({"status": "error", "message": f"Failed to allocate funds to goal {goal['title']}"}), 500
            except Exception as e:
                current_app.logger.error(f"Error allocating funds to goal {goal['title']}: {str(e)}")
                current_app.logger.error(traceback.format_exc())
                return jsonify({"status": "error", "message": "Internal server error"}), 500
        current_app.logger.info(f"Allocation summary for user {user_id}: {allocations_summary}")
        return jsonify({
            "status": "success",
            "message": "Allocations recalculated successfully",
            "net_income": float(net_income),
            "allocations": allocations_summary
        }), 200
    except Exception as e:
        current_app.logger.error(f"Error during allocation recalculation: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "Internal server error"}), 500