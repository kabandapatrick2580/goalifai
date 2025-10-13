from flask import Blueprint, jsonify, request
from app import db
from datetime import datetime, timezone
from app.models.client.goal import Goal, MonthlyGoalAllocation as GoalAllocation, GoalPriority
from decimal import Decimal
import traceback
from flask import current_app
from app.models.client.financial import FinancialRecord, Categories as FC
from app.models.client.users_model import UserFinancialProfile as FinancialProfile
from app.helpers.financials import quantize, ensure_profile_balances

allocations_blueprint = Blueprint('allocations_api', __name__, url_prefix='/api/v1/allocations')

@allocations_blueprint.route('/recalculate/<uuid:user_id>', methods=['POST'])
def recalculate_allocations(user_id):
    """
    Recalculate allocations for the given user's financial profile:
    - Handles repayment or recording of deficits
    - Allocates available funds to active goals by priority
    - Records any remaining funds as saving
    """
    try:
        # 1. Get financial profile
        profile = FinancialProfile.get_financial_profile_by_user_id(user_id)
        if not profile:
            return jsonify({"status": "error", "message": "Financial profile not found"}), 404

        ensure_profile_balances(profile)

        # 2. Fetch monthly totals
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month

        totals = FinancialRecord.get_monthly_summary_totals(user_id=user_id, year=year, month=month)
        current_app.logger.info(f"Monthly totals for user {user_id} for {year}-{month}: {totals}")
        if not totals:
            current_app.logger.info(f"This user has no financial records for {year}-{month}. Nothing to allocate.")
            expected_totals = FinancialProfile.get_expected_totals(user_id)
            if expected_totals:
                totals = {
                    "total_income": Decimal(str(expected_totals.get("expected_monthly_income", 0))),
                    "total_expense": Decimal(str(expected_totals.get("expected_monthly_expenses", 0)))
                }
            else:
                totals = {"total_income": Decimal('0.00'), "total_expense": Decimal('0.00')}

        total_income = quantize(Decimal(str(totals.get("total_income", 0))))
        total_expense = quantize(Decimal(str(totals.get("total_expense", 0))))
        raw_net = quantize(total_income - total_expense)

        current_app.logger.info(
            f"[alloc] user={user_id} income={total_income} expense={total_expense} net={raw_net}"
        )

        # 3. Calculate available funds
        base_rate = Decimal(str(profile.base_allocation_rate or 0.10))
        base_allocation_amount = quantize(raw_net * base_rate if raw_net > 0 else Decimal('0.00'))

        include_savings_in_alloc = getattr(profile, "include_savings_in_alloc", False)
        pre_existing_savings = quantize(profile.savings_balance or Decimal('0.00')) if include_savings_in_alloc else Decimal('0.00')

        available_funds = raw_net + pre_existing_savings

        current_app.logger.info(
            f"[alloc] profile={profile.id} available_funds={available_funds} base_allocation={base_allocation_amount}"
        )

        # 4. Handle deficit repayment first
        if profile.deficit_balance > 0:
            if available_funds >= profile.deficit_balance:
                paid = profile.deficit_balance
                available_funds -= paid
                profile.deficit_balance = Decimal('0.00')

                # Record repayment
                def_cat = FC.get_category_by_name("Deficit")
                if def_cat:
                    FinancialRecord.create_record(
                        user_id=user_id,
                        amount=paid,
                        category_id=def_cat["id"],
                        expected_transaction=False,
                        description="Deficit repayment from current funds",
                        recorded_at=datetime.now(timezone.utc),
                    )
            else:
                # Partial repayment only
                paid = available_funds
                profile.deficit_balance -= paid
                available_funds = Decimal('0.00')
                db.session.commit()
                return jsonify({
                    "status": "deficit_partial",
                    "message": "Partial deficit repayment made; no allocations available.",
                    "remaining_deficit": float(profile.deficit_balance)
                }), 200

        # 5. If deficit after repayment still negative (spent more than earned)
        if raw_net < 0 and available_funds == 0:
            new_deficit = abs(raw_net)
            current_app.logger.info(f"Recording new deficit of {new_deficit} for user {user_id}")
            profile.deficit_balance += new_deficit
            db.session.add(profile)
            def_cat = FC.get_category_by_name("Deficit")
            if def_cat:
                FinancialRecord.create_record(
                    user_id=user_id,
                    amount=new_deficit,
                    category_id=def_cat["id"],
                    expected_transaction=False,
                    description="Recorded monthly deficit (expenses exceeded income)",
                    recorded_at=datetime.now(timezone.utc),
                )

            # Update all goals to have zero allocation for this month
            goals = Goal.get_active_goals(user_id)
            for g in goals:
                GoalAllocation.reallocate_funds(
                    user_id=user_id,
                    goal_id=g.get("goal_id"),
                    month=now.strftime("%Y-%m"),
                    allocated_amount=Decimal('0.00')
                )

            db.session.commit()
            return jsonify({
                "status": "deficit_recorded",
                "message": "No available funds, deficit recorded and carried forward.",
                "deficit_balance": float(profile.deficit_balance)
            }), 200

        # 6. Fetch active goals
        goals = Goal.get_active_goals(user_id)
        if not goals:
            # No active goals, treat all available funds as savings
            if available_funds > 0:
                profile.savings_balance += available_funds
                save_cat = FC.get_category_by_name("Saving")
                if save_cat:
                    FinancialRecord.create_record(
                        user_id=user_id,
                        amount=available_funds,
                        category_id=save_cat["category_id"],
                        expected_transaction=False,
                        description="No active goals — funds saved.",
                        recorded_at=datetime.now(timezone.utc),
                    )
            db.session.commit()
            return jsonify({
                "status": "saved",
                "message": "No active goals. Funds saved.",
                "savings_balance": float(profile.savings_balance)
            }), 200

        # 7. Compute goal gaps and priorities for the purpose of allocation
        total_gap = Decimal('0.00')
        total_priority = Decimal('0.00')

        for g in goals:
            gap = Decimal(str(g.get("target_amount", 0))) - Decimal(str(g.get("current_amount", 0)))
            if gap > 0:
                total_gap += gap
            total_priority += Decimal(str(g.get("priority", {}).get("percentage", 0)))

        if total_gap <= 0 or total_priority <= 0:
            # Nothing to allocate
            #profile.savings_balance += available_funds
            #db.session.commit()
            return jsonify({
                "status": "saved",
                "message": "All goals fully funded or invalid priority; funds saved.",
                "savings_balance": float(profile.savings_balance)
            }), 200

        # 8. Allocate funds proportionally by priority
        allocatable_pool = min(available_funds, total_gap)
        total_allocated = Decimal('0.00')
        allocations_summary = []

        for g in goals:
            pct = Decimal(str(g.get("priority", {}).get("percentage", 0)))
            if pct <= 0:
                continue

            share = (pct / total_priority)
            proposed = quantize(allocatable_pool * share)
            gap = Decimal(str(g.get("target_amount", 0))) - Decimal(str(g.get("current_amount", 0)))
            allocate_amt = min(proposed, gap)

            if allocate_amt <= 0:
                continue

            alloc = GoalAllocation.reallocate_funds(
                user_id=user_id,
                goal_id=g.get("goal_id"),
                month=now.strftime("%Y-%m"),
                allocated_amount=allocate_amt
            )

            if alloc:
                total_allocated += allocate_amt
                allocations_summary.append({
                    "goal_id": str(g["goal_id"]),
                    "goal_title": g.get("title"),
                    "allocated_amount": float(allocate_amt)
                })

                update_g = Goal.update_goal(goal_id=g.get("goal_id"), current_amount=allocate_amt)
                if not update_g:
                    current_app.logger.error(f"Failed to update goal {g.get('goal_id')} after allocation.")

            else:
                current_app.logger.error(f"Failed to create/update allocation for goal {g.get('goal_id')}")

        # 9. Save remaining funds (if any)
        remaining_balance = quantize(available_funds - total_allocated)
        if remaining_balance > 0:
            profile.savings_balance += remaining_balance
            save_cat = FC.get_category_by_name("Saving")
            if save_cat:
                FinancialRecord.create_record(
                    user_id=user_id,
                    amount=remaining_balance,
                    category_id=save_cat["id"],
                    expected_transaction=False,
                    description="Remaining funds after allocations saved.",
                    recorded_at=datetime.now(timezone.utc),
                )

        db.session.add(profile)
        db.session.commit()

        return jsonify({
            "status": "success",
            "message": "Allocations recalculated successfully.",
            "allocations": allocations_summary,
            "total_allocated": float(total_allocated),
            "remaining_savings_balance": float(profile.savings_balance),
            "deficit_balance": float(profile.deficit_balance)
        }), 200

    except Exception as exc:
        db.session.rollback()
        current_app.logger.error(f"Error recalculating allocations: {exc}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@allocations_blueprint.route('/user/<uuid:user_id>', methods=['GET'])
def get_user_allocations(user_id):
    """
    Get all goal allocations for a specific user, grouped by month.
    """
    try:
        allocations = GoalAllocation.get_allocations_by_user(user_id)
        if not allocations:
            return jsonify({"status": "error", "message": "No allocations found for this user."}), 404

        return jsonify({
            "status": "success",
            "user_id": str(user_id),
            "allocations": allocations
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error fetching allocations for user {user_id}: {str(e)}")
        current_app.logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": "Internal server error"}), 500


@allocations_blueprint.route('/all', methods=['GET'])
def get_all_allocations():
    """
    Get all goal allocations for a specific month across all users.
    """
    try:
        allocations = GoalAllocation.get_all_allocations()
        print(f"Allocations: {allocations}")
        if allocations:
            return jsonify({
                "status": "success",
                "allocations": allocations
            }), 200
        else:
            return jsonify({"status": "error", "message": "No allocations found."}), 404
            

    except Exception as e:
        current_app.logger.error(f"Error fetching allocations for month: {str(e)}")
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
