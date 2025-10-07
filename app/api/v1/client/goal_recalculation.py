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
            remaining_need = goal["target_amount"] - goal["current_amount"]
            if amt_to_allocate > 0:
                allocated_amount = amt_to_allocate if amt_to_allocate < remaining_need else remaining_need
            else:
                allocated_amount = Decimal('0.00')
            
            
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
    
@allocations_blueprint.route('/finalize/<string:month>', methods=['POST'])
def finalize_allocations(month):
    """
    - Finalize goal allocations for a specific month.
    - Transfers allocated funds to the corresponding goals.
    - Locks the allocation records to prevent further changes.

    Args:
        month: str (format: YYYY-MM) e.g. "2024-09"
    """
    month = month.strip()
    monthly_allocations = GoalAllocation.get_allocations_by_month(month)
    if not monthly_allocations:
        return jsonify({"status": "error", "message": f"No allocations found for month {month}"}), 404

    current_app.logger.info(f"Finalizing allocations for month {month}: {monthly_allocations}")

    try:
        for goal_id, goal_data in monthly_allocations.items():
            goal = Goal.query.get(goal_id)
            if not goal:
                current_app.logger.error(f"Goal {goal_id} not found. Skipping allocations.")
                continue
            total_allocated_for_goal = 0
            for allocation_info in goal_data["allocations"]:
                allocation = GoalAllocation.query.get(allocation_info["allocation_id"])
                if not allocation:
                    current_app.logger.error(f"Allocation {allocation_info['allocation_id']} not found. Skipping.")
                    continue
                if allocation.is_finalized:
                    current_app.logger.info(f"Allocation {allocation.allocation_id} already finalized. Skipping.")
                    continue

                # Update goal's current amount
                total_allocated_for_goal += (allocation.allocated_amount or 0)
                allocation.is_finalized = True
                db.session.add(allocation)

            # Update goal's current amount once per goal
            goal.current_amount += total_allocated_for_goal
            if goal.current_amount >= goal.target_amount:
                goal.is_completed = True
            db.session.add(goal)

        db.session.commit()
        return jsonify({"status": "success", "message": f"Allocations for month {month} finalized successfully."}), 200

    except Exception as e:
        current_app.logger.error(f"Error finalizing allocations for month {month}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        db.session.rollback()
        return jsonify({"status": "error", "message": "Internal server error"}), 500
