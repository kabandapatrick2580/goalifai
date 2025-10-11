from flask import Blueprint, jsonify, request
from app import db
from datetime import datetime, timezone
from app.models.client.goal import Goal, MonthlyGoalAllocation as GoalAllocation, GoalPriority
from decimal import Decimal
import traceback
from flask import current_app
from app.models.client.financial import FinancialRecord, Categories as FC

allocations_blueprint = Blueprint('allocations_api', __name__, url_prefix='/api/v1/allocations')


@allocations_blueprint.route('/recalculate/<uuid:user_id>', methods=['POST'])
def recalculate_allocations(user_id):
    """
    Recalculate goal allocations for the user based on current income, expenses, and goal priorities.
    """

    try:
        if not user_id:
            return jsonify({"error": "user_id is required"}), 400

        data = FinancialRecord.get_monthly_summary_totals(user_id=user_id)
        total_income = Decimal(str(data.get("total_income", 0)))
        total_expense = Decimal(str(data.get("total_expense", 0)))
        net_income = total_income - total_expense

        current_app.logger.info(
            f"User {user_id}: Income={total_income}, Expense={total_expense}, Net={net_income}"
        )

        current_month = datetime.now().strftime("%Y-%m")

        # ---- Handle deficit ----
        if net_income <= 0:
            deficit_cat = FC.get_category_by_name("Deficit")
            FinancialRecord.create_record(
                user_id=user_id,
                amount=abs(net_income),
                category_id=deficit_cat.get("category_id"),
                expected_transaction=False,
                description="Monthly deficit - no allocations made",
                recorded_at=datetime.now(timezone.utc),
            )
            return jsonify({
                "status": "success",
                "message": f"Deficit recorded. No allocations made for user {user_id}.",
                "net_income": float(net_income)
            }), 200

        # ---- If surplus, try allocating ----
        goals = Goal.get_active_goals(user_id)
        if not goals:
            current_app.logger.info(f"No active goals found for user {user_id}.")
            return jsonify({"message": "No active goals found for user."}), 200

        total_priority = sum(
            float(g['priority']['percentage'])
            for g in goals if g.get('priority') and g['priority'].get('percentage')
        )

        if total_priority == 0:
            return jsonify({"message": "No valid goal priorities found for allocation."}), 400

        total_allocated = Decimal('0.00')
        allocations_summary = []

        for goal in goals:
            if not goal.get("priority") or not goal["priority"].get("percentage"):
                continue

            weight = float(goal["priority"]["percentage"]) / total_priority
            amt_to_allocate = net_income * Decimal(str(weight))
            remaining_need = goal["target_amount"] - goal["current_amount"]
            allocated_amount = min(amt_to_allocate, remaining_need) # Cap allocation to remaining need

            if allocated_amount <= 0:
                continue

            GoalAllocation.reallocate_funds(
                user_id=user_id,
                goal_id=goal["goal_id"],
                month=current_month,
                allocated_amount=allocated_amount
            )

            total_allocated += allocated_amount
            allocations_summary.append({
                "goal_id": str(goal["goal_id"]),
                "goal_title": goal["title"],
                "allocated_amount": float(allocated_amount)
            })

        # ---- Calculate remaining surplus (after allocations) ----
        remaining_surplus = net_income - total_allocated
        if remaining_surplus > 0:
            surplus_cat = FC.get_category_by_name("Surplus")
            FinancialRecord.create_record(
                user_id=user_id,
                amount=remaining_surplus,
                category_id=surplus_cat.get("category_id"),
                expected_transaction=False,
                description="Remaining funds after all goal allocations.",
                recorded_at=datetime.now(timezone.utc),
            )
            current_app.logger.info(
                f"Recorded {remaining_surplus} as surplus for user {user_id} after allocations."
            )
            # Autocarry surplus into next month's allocations could be implemented here
            FinancialRecord.carry_over_surplus(
                user_id,
                remaining_surplus,
                current_month
            )

        return jsonify({
            "status": "success",
            "message": "Allocations recalculated successfully.",
            "net_income": float(net_income),
            "allocated": float(total_allocated),
            "remaining_surplus": float(remaining_surplus),
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
