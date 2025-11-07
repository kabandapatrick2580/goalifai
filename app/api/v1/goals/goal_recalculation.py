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
    Recalculate allocations for the given user's financial profile.
    Designed to run after each income/expense transaction is recorded.
    
    Uses ethical allocation strategy:
      - Non-finalized goal allocations are FLEXIBLE (available for current month expenses)
      - User can mark goals as PROTECTED to prevent pullback
      - Finalized months are IMMUTABLE (historical integrity)
      - Savings → Flexible Goals → Deficit (in that order)
    
    This process:
      1. Retrieves latest monthly totals (including the just-recorded transaction).
      2. Calculates the NET CHANGE since last recalculation.
      3. Only processes the incremental change (not the entire month's balance).
      4. Repays existing deficits if funds allow.
      5. Allocates remaining funds to active goals based on priority and gap.
      6. Records any unallocated funds as savings.
      7. Updates snapshots to track what's been processed.
    """

    try:
        # 1. Retrieve financial profile
        profile = FinancialProfile.get_financial_profile_by_user_id(user_id)
        if not profile:
            return jsonify({"status": "error", "message": "Financial profile not found"}), 404

        ensure_profile_balances(profile)

        # 2. Determine current period
        now = datetime.now(timezone.utc)
        year, month = now.year, now.month
        current_month = now.strftime("%Y-%m")

        # 3. Check if current month is already finalized (shouldn't happen, but safety check)
        month_finalization = GoalAllocation.check_if_monthly_allocation_finalized(user_id=user_id, month=current_month)
        
        if month_finalization:
            return jsonify({
                "status": "error",
                "message": f"Month {current_month} is already finalized. Cannot modify allocations.",
                "finalized_at": month_finalization.finalized_at.isoformat()
            }), 400

        # 4. Fetch income and expense totals for the period
        totals = FinancialRecord.get_monthly_summary_totals(user_id=user_id, year=year, month=month)
        current_app.logger.info(f"Monthly totals for user {user_id}: {totals}")

        if not totals:
            # Fall back to expected income/expense if user has no actual records
            expected = FinancialProfile.get_expected_totals(user_id)
            totals = {
                "total_income": Decimal(str(expected.get("expected_monthly_income", 0))) if expected else Decimal('0.00'),
                "total_expense": Decimal(str(expected.get("expected_monthly_expenses", 0))) if expected else Decimal('0.00')
            }

        total_income = quantize(Decimal(str(totals.get("total_income", 0))))
        total_expense = quantize(Decimal(str(totals.get("total_expense", 0))))

        current_app.logger.info(
            f"[alloc] user={user_id} income={total_income} expense={total_expense}"
        )

        # 5. Calculate INCREMENTAL CHANGE since last recalculation
        prev_income = profile.total_income_snapshot or Decimal('0.00')
        prev_expense = profile.total_expense_snapshot or Decimal('0.00')
        
        income_delta = quantize(total_income - prev_income)
        expense_delta = quantize(total_expense - prev_expense)
        net_change = quantize(income_delta - expense_delta)

        current_app.logger.info(
            f"[alloc] Incremental change - income_delta={income_delta}, "
            f"expense_delta={expense_delta}, net_change={net_change}"
        )

        # 6. If no change, nothing to process
        if net_change == 0:
            current_app.logger.info(f"[alloc] No incremental change detected — skipping.")
            return jsonify({
                "status": "success",
                "message": "No new transactions to process.",
                "savings_balance": float(profile.savings_balance),
                "deficit_balance": float(profile.deficit_balance)
            }), 200

        # 7. Preserve existing balances
        existing_savings = quantize(profile.savings_balance or Decimal('0.00'))
        existing_deficit = quantize(profile.deficit_balance or Decimal('0.00'))

        current_app.logger.info(
            f"[alloc] Starting balances - savings={existing_savings}, deficit={existing_deficit}"
        )

        # 8. Calculate available funds from this incremental change
        available_funds = net_change
        
        # Optionally include existing savings in allocation pool (for positive changes)
        include_savings_in_alloc = getattr(profile, "include_savings_in_alloc", False)
        if include_savings_in_alloc and existing_savings > 0 and net_change > 0:
            available_funds += existing_savings
            profile.savings_balance = Decimal('0.00')
        
        current_app.logger.info(
            f"[alloc] Available funds from change: {available_funds}"
        )

        # 9. Handle deficit scenarios first
        
        # Case A: Repay existing deficit if we have positive funds
        if existing_deficit > 0 and available_funds > 0:
            if available_funds >= existing_deficit:
                # Full repayment
                paid = existing_deficit
                available_funds -= paid
                profile.deficit_balance = Decimal('0.00')

                current_app.logger.info(f"[alloc] Full deficit repayment: {paid}")

                def_cat = FC.get_category_by_name("Deficit")
                if def_cat:
                    FinancialRecord.create_record(
                        user_id=user_id,
                        amount=paid,
                        category_id=def_cat["id"],
                        expected_transaction=False,
                        description="Deficit fully repaid using current funds.",
                        recorded_at=datetime.now(timezone.utc),
                        is_allocation_transaction=True
                    )
            else:
                # Partial repayment
                paid = available_funds
                profile.deficit_balance = quantize(existing_deficit - paid)
                available_funds = Decimal('0.00')

                current_app.logger.info(
                    f"[alloc] Partial deficit repayment: {paid}, remaining={profile.deficit_balance}"
                )

                def_cat = FC.get_category_by_name("Deficit")
                if def_cat:
                    FinancialRecord.create_record(
                        user_id=user_id,
                        amount=paid,
                        category_id=def_cat["id"],
                        expected_transaction=False,
                        description="Partial deficit repayment made.",
                        recorded_at=datetime.now(timezone.utc),
                        is_allocation_transaction=True
                    )

                # Update snapshots and commit
                profile.total_income_snapshot = total_income
                profile.total_expense_snapshot = total_expense
                profile.last_calculated_at = now
                db.session.add(profile)
                db.session.commit()

                return jsonify({
                    "status": "deficit_partial",
                    "message": "Partial deficit repayment made. No allocations available.",
                    "remaining_deficit": float(profile.deficit_balance)
                }), 200
        
        # Case B: Negative net change (expenses > income this period)
        # ETHICAL APPROACH: Pull from savings first, then flexible goals, then deficit
        if net_change < 0:
            shortage = abs(net_change)
            current_app.logger.info(f"[alloc] Negative net_change: {net_change}, shortage: {shortage}")
            
            pullback_from_savings = Decimal('0.00')
            recovered_from_goals = Decimal('0.00')
            goal_reductions = []
            protected_goals_skipped = []
            
            # Step 1: Pull from savings balance FIRST (protects goal allocations)
            if shortage > 0 and profile.savings_balance > 0:
                pullback_from_savings = min(profile.savings_balance, shortage)
                profile.savings_balance = quantize(profile.savings_balance - pullback_from_savings)
                shortage -= pullback_from_savings
                
                current_app.logger.info(
                    f"[alloc] Pulled {pullback_from_savings} from savings, "
                    f"remaining_savings={profile.savings_balance}, remaining_shortage={shortage}"
                )
                
                # Record the savings withdrawal
                save_cat = FC.get_category_by_name("Saving")
                if save_cat:
                    FinancialRecord.create_record(
                        user_id=user_id,
                        amount=pullback_from_savings,
                        category_id=save_cat["id"],
                        expected_transaction=False,
                        description="Withdrawn from savings to cover expenses.",
                        recorded_at=datetime.now(timezone.utc),
                        is_allocation_transaction=True
                    )
            
            # Step 2: Pull from FLEXIBLE goal allocations (respecting protection levels)
            if shortage > 0:
                goals = Goal.get_active_goals(user_id)
                
                if goals:
                    current_app.logger.info(
                        f"[alloc] Savings insufficient. Checking flexible goals to cover remaining {shortage}"
                    )
                    
                    # Get pullable goals in smart order (lowest priority first)
                    pullable_goals = []
                    
                    for g in goals:
                        goal_id = g.get("goal_id")
                        
                        # Get current month's allocation
                        current_allocation = GoalAllocation.get_total_allocated_for_goal(
                            goal_id=goal_id,
                            month=current_month
                        )
                        current_app.logger.info(f"[alloc] Goal {goal_id} allocation for {current_month}: {current_allocation}")
                        if not current_allocation or current_allocation <= 0:
                            continue
                        
                        # Check protection level
                        protection_level = g.get("protection_level", "flexible")
                        is_locked = g.get("is_locked", False)
                        is_completed = g.get("status") == "completed"
                        
                        # Skip protected, locked, or completed goals
                        if protection_level == "protected" or is_locked or is_completed:
                            protected_goals_skipped.append({
                                "goal_id": str(goal_id),
                                "goal_title": g.get("title"),
                                "amount": float(current_allocation.get("allocated_amount")),
                                "reason": g.get("protection_reason") or "User-protected"
                            })
                            current_app.logger.info(
                                f"[alloc] Skipping protected/locked goal {goal_id} ({g.get('title')})"
                            )
                            continue
                        
                        # Calculate pull priority (lower score = pull first)
                        priority_pct = Decimal(str(g.get("priority", {}).get("percentage", 50)))
                        current_amt = Decimal(str(g.get("current_amount", 0)))
                        target_amt = Decimal(str(g.get("target_amount", 1)))
                        completion_pct = (current_amt / target_amt * 100) if target_amt > 0 else 0
                        is_essential = g.get("is_essential", False)
                        
                        pull_score = (
                            (100 - float(priority_pct)) * 2 +  # Low priority = pull first
                            (100 - float(completion_pct)) +    # Far from done = pull first
                            (0 if is_essential else 50)        # Non-essential = pull first
                        )
                        
                        pullable_goals.append({
                            "goal": g,
                            "allocation": current_allocation,
                            "pull_score": pull_score
                        })
                        current_app.logger.info(
                            f"[alloc] Goal {goal_id} eligible for pullback: "
                            f"priority={priority_pct}, completion={completion_pct}, "
                            f"is_essential={is_essential}, pull_score={pull_score}"
                        )
                    
                    # Sort by pull_score (pull from lowest priority first)
                    pullable_goals.sort(key=lambda x: x["pull_score"])
                    current_app.logger.info(
                        f"[alloc] Pullable goals sorted for pullback: {pullable_goals}"
                    )
                    # Pull from goals in order
                    for item in pullable_goals:
                        if shortage <= 0:
                            break
                        
                        goal = item["goal"]
                        allocation = item["allocation"]
                        goal_id = goal.get("goal_id")
                        allocated_amt = Decimal(str(allocation))
                        
                        # Calculate how much to pull back
                        pullback = min(allocated_amt, shortage)
                        
                        # Reduce the allocation
                        new_allocation = quantize(allocated_amt - pullback)
                        GoalAllocation.reallocate_funds(
                            user_id=user_id,
                            goal_id=goal_id,
                            month=current_month,
                            allocated_amount=new_allocation
                        )
                        
                        # Reduce the goal's current_amount
                        Goal.update_goal(goal_id=goal_id, current_amount=-pullback)
                        
                        recovered_from_goals += pullback
                        shortage -= pullback
                        
                        goal_reductions.append({
                            "goal_id": str(goal_id),
                            "goal_title": goal.get("title"),
                            "reduced_by": float(pullback),
                            "new_allocation": float(new_allocation),
                            "priority": float(goal.get("priority", {}).get("percentage", 50))
                        })
                        
                        current_app.logger.info(
                            f"[alloc] Pulled {pullback} from goal {goal_id} ({goal.get('title')}), "
                            f"new_allocation={new_allocation}, remaining_shortage={shortage}"
                        )
            
            # Step 3: Only record deficit if we still have a shortage after pulling from all sources
            if shortage > 0:
                profile.deficit_balance = quantize(profile.deficit_balance + shortage)
                
                current_app.logger.info(
                    f"[alloc] Recording deficit: {shortage}, total_deficit={profile.deficit_balance}"
                )

                def_cat = FC.get_category_by_name("Deficit")
                if def_cat:
                    FinancialRecord.create_record(
                        user_id=user_id,
                        amount=shortage,
                        category_id=def_cat["id"],
                        expected_transaction=False,
                        description="Recorded deficit after using available funds.",
                        recorded_at=datetime.now(timezone.utc),
                        is_allocation_transaction=True
                    )

            # Update snapshots and commit
            profile.total_income_snapshot = total_income
            profile.total_expense_snapshot = total_expense
            profile.last_calculated_at = now
            db.session.add(profile)
            db.session.commit()

            response_data = {
                "status": "expense_processed",
                "message": "Expense processed using available funds.",
                "net_change": float(net_change),
                "funds_used": {
                    "from_savings": float(pullback_from_savings),
                    "from_goals": float(recovered_from_goals)
                },
                "goal_reductions": goal_reductions,
                "protected_goals": protected_goals_skipped,
                "savings_balance": float(profile.savings_balance),
                "deficit_balance": float(profile.deficit_balance)
            }
            
            if shortage > 0:
                response_data["deficit_created"] = float(shortage)
                response_data["message"] += f" Deficit of {float(shortage)} recorded."
            else:
                response_data["message"] += " No deficit created."
            
            return jsonify(response_data), 200

        # 10. At this point, available_funds >= 0 (positive income or surplus)
        if available_funds <= 0:
            # Edge case: all funds used for deficit repayment
            profile.total_income_snapshot = total_income
            profile.total_expense_snapshot = total_expense
            profile.last_calculated_at = now
            db.session.add(profile)
            db.session.commit()

            return jsonify({
                "status": "success",
                "message": "All funds used for deficit repayment.",
                "savings_balance": float(profile.savings_balance),
                "deficit_balance": float(profile.deficit_balance)
            }), 200

        # 11. Retrieve active goals for positive allocation
        goals = Goal.get_active_goals(user_id)
        
        if not goals:
            # If no goals, all available funds become savings
            profile.savings_balance = quantize(profile.savings_balance + available_funds)
            
            current_app.logger.info(
                f"[alloc] No active goals, saving {available_funds}, total_savings={profile.savings_balance}"
            )
            
            save_cat = FC.get_category_by_name("Saving")
            if save_cat:
                FinancialRecord.create_record(
                    user_id=user_id,
                    amount=available_funds,
                    category_id=save_cat["id"],
                    expected_transaction=False,
                    description="No active goals — funds moved to savings.",
                    recorded_at=datetime.now(timezone.utc),
                    is_allocation_transaction=True
                )

            # Update snapshots and commit
            profile.total_income_snapshot = total_income
            profile.total_expense_snapshot = total_expense
            profile.last_calculated_at = now
            db.session.add(profile)
            db.session.commit()

            return jsonify({
                "status": "saved",
                "message": "No active goals. Funds saved.",
                "savings_balance": float(profile.savings_balance)
            }), 200

        # 12. Compute total goal gaps and priorities (only for non-completed goals)
        total_gap = Decimal('0.00')
        total_priority = Decimal('0.00')
        goals_with_gap = []

        for g in goals:
            # Skip completed or locked goals from new allocations
            if g.get("status") == "completed" or g.get("is_locked", False):
                continue
                
            target = Decimal(str(g.get("target_amount", 0)))
            current = Decimal(str(g.get("current_amount", 0)))
            gap = quantize(target - current)
            
            if gap > 0:
                total_gap += gap
                goals_with_gap.append({**g, "gap": gap})
            
            priority_pct = Decimal(str(g.get("priority", {}).get("percentage", 0)))
            total_priority += priority_pct

        current_app.logger.info(
            f"[alloc] Goals analysis - total_gap={total_gap}, total_priority={total_priority}, "
            f"goals_with_gap={len(goals_with_gap)}"
        )

        if total_gap <= 0 or total_priority <= 0 or not goals_with_gap:
            # Nothing to allocate, save all available funds
            profile.savings_balance = quantize(profile.savings_balance + available_funds)
            
            save_cat = FC.get_category_by_name("Saving")
            if save_cat:
                FinancialRecord.create_record(
                    user_id=user_id,
                    amount=available_funds,
                    category_id=save_cat["id"],
                    expected_transaction=False,
                    description="Goals already funded — funds saved.",
                    recorded_at=datetime.now(timezone.utc),
                    is_allocation_transaction=True
                )

            # Update snapshots and commit
            profile.total_income_snapshot = total_income
            profile.total_expense_snapshot = total_expense
            profile.last_calculated_at = now
            db.session.add(profile)
            db.session.commit()

            return jsonify({
                "status": "saved",
                "message": "Goals already funded — funds saved.",
                "savings_balance": float(profile.savings_balance)
            }), 200

        # 13. Allocate funds proportionally based on goal priority
        allocatable_pool = min(available_funds, total_gap)
        total_allocated = Decimal('0.00')
        allocations_summary = []
        newly_completed_goals = []

        current_app.logger.info(
            f"[alloc] Allocating {allocatable_pool} from net_change={net_change} "
            f"across {len(goals_with_gap)} goals"
        )

        for g in goals_with_gap:
            priority_pct = Decimal(str(g.get("priority", {}).get("percentage", 0)))
            
            if priority_pct <= 0:
                continue

            # Calculate this goal's share based on priority
            share = quantize(priority_pct / total_priority)
            proposed = quantize(allocatable_pool * share)
            
            # Don't allocate more than the goal's remaining gap
            gap = g["gap"]
            allocate_amt = min(proposed, gap)

            if allocate_amt <= 0:
                continue

            # Create or update allocation record for this month
            alloc = GoalAllocation.reallocate_funds(
                user_id=user_id,
                goal_id=g.get("goal_id"),
                month=current_month,
                allocated_amount=allocate_amt
            )

            if alloc:
                total_allocated = quantize(total_allocated + allocate_amt)
                
                # Update goal progress (increment current_amount)
                Goal.update_goal(goal_id=g.get("goal_id"), current_amount=allocate_amt)
                
                # Check if goal just completed
                new_current = Decimal(str(g.get("current_amount", 0))) + allocate_amt
                target = Decimal(str(g.get("target_amount", 0)))
                
                if new_current >= target and g.get("status") != "completed":
                    newly_completed_goals.append({
                        "goal_id": str(g["goal_id"]),
                        "goal_title": g.get("title"),
                        "final_amount": float(new_current)
                    })
                
                allocations_summary.append({
                    "goal_id": str(g["goal_id"]),
                    "goal_title": g.get("title"),
                    "allocated_amount": float(allocate_amt),
                    "priority_percentage": float(priority_pct),
                    "new_total": float(new_current)
                })
                
                current_app.logger.info(
                    f"[alloc] Allocated {allocate_amt} to goal {g.get('goal_id')} ({g.get('title')})"
                )
            else:
                current_app.logger.error(f"[alloc] Failed to allocate to goal {g.get('goal_id')}")

        # 14. Save any remaining unallocated funds
        remaining_balance = quantize(available_funds - total_allocated)
        
        if remaining_balance > 0:
            profile.savings_balance = quantize(profile.savings_balance + remaining_balance)
            
            current_app.logger.info(
                f"[alloc] Saving remaining {remaining_balance}, total_savings={profile.savings_balance}"
            )
            
            save_cat = FC.get_category_by_name("Saving")
            if save_cat:
                FinancialRecord.create_record(
                    user_id=user_id,
                    amount=remaining_balance,
                    category_id=save_cat["id"],
                    expected_transaction=False,
                    description="Unallocated funds moved to savings.",
                    recorded_at=datetime.now(timezone.utc),
                    is_allocation_transaction=True
                )

        # 15. Update snapshots to reflect what we've now processed
        profile.total_income_snapshot = total_income
        profile.total_expense_snapshot = total_expense
        profile.last_calculated_at = now
        db.session.add(profile)
        db.session.commit()

        current_app.logger.info(
            f"[alloc] Recalculation complete - net_change={net_change}, allocated={total_allocated}, "
            f"savings={profile.savings_balance}, deficit={profile.deficit_balance}"
        )

        response = {
            "status": "success",
            "message": "Allocations processed successfully.",
            "net_change": float(net_change),
            "allocations": allocations_summary,
            "total_allocated": float(total_allocated),
            "remaining_savings_balance": float(profile.savings_balance),
            "deficit_balance": float(profile.deficit_balance)
        }
        
        if newly_completed_goals:
            response["newly_completed_goals"] = newly_completed_goals
            response["message"] += f" {len(newly_completed_goals)} goal(s) completed!"

        return jsonify(response), 200

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
