# Financial Goal Allocation System

## Overview
This system manages dynamic financial goal allocation based on user income, expenses, and configurable priorities. It handles real-time fund reallocation, deficit management, and protected goal balances throughout the monthly financial cycle using an incremental change detection approach.

## Core Logic Workflow

### 1. Financial Data Tracking
- **Income & Expense Monitoring**: Continuously tracks total income and total expenses from the `financial_records` table
- **User Context**: Processes data per `user_id` and `current_month`
- **Goal Priorities**: Uses goal priority percentages to calculate allocation weights
- **Snapshot Tracking**: Maintains `total_income_snapshot` and `total_expense_snapshot` in `financial_profile` to detect changes

### 2. Incremental Change Detection
The system uses **delta-based processing** to avoid duplicate allocations:
```
income_delta = current_total_income - last_income_snapshot
expense_delta = current_total_expense - last_expense_snapshot
net_change = income_delta - expense_delta
```

**Key Benefits:**
- Only processes actual changes since last calculation
- Prevents duplicate savings/deficit records
- Enables real-time responsiveness to new transactions
- Maintains accurate financial state across multiple recalculations

**Early Exit Condition:**
- If `net_change == 0`, skip processing (no new transactions)
- Return current balances without modification

### 3. Deficit Repayment Priority (Positive Net Change)
When `net_change > 0` and existing deficit exists:

#### Full Repayment
- If `available_funds >= existing_deficit`:
  - Repay full deficit amount
  - Reduce `available_funds` by deficit amount
  - Set `deficit_balance = 0`
  - Record repayment as expense transaction (category: "Deficit")

#### Partial Repayment
- If `available_funds < existing_deficit`:
  - Repay partial deficit with all available funds
  - Reduce `deficit_balance` by payment amount
  - Set `available_funds = 0`
  - Record partial repayment transaction
  - **Exit early** - no funds left for goal allocation
  - Update snapshots and commit

### 4. Expense Coverage Strategy (Negative Net Change)
When `net_change < 0`, calculate shortage and cover using **ethical 3-tier approach**:
```
shortage = abs(net_change)
```

#### Tier 1: Savings Balance (Priority Protection)
- Pull from `savings_balance` first (protects goal allocations)
- Amount pulled: `min(savings_balance, shortage)`
- Record withdrawal as expense transaction (category: "Saving")
- Reduce remaining shortage

#### Tier 2: Flexible Goal Allocations (Smart Pullback)
If savings insufficient, pull from non-protected goals:

**Goal Eligibility Rules:**
- ✅ Include: Goals with `protection_level = "flexible"`
- ❌ Skip: Goals with `protection_level = "protected"`
- ❌ Skip: Goals with `is_locked = true`
- ❌ Skip: Goals with `status = "completed"`

**Pull Priority Calculation** (lower score = pull first):
```python
pull_score = (
    (100 - priority_percentage) * 2 +      # Low priority = pull first
    (100 - completion_percentage) +         # Far from completion = pull first
    (0 if is_essential else 50)            # Non-essential = pull first
)
```

**Pullback Process:**
1. Sort eligible goals by `pull_score` (ascending)
2. For each goal until `shortage = 0`:
   - Calculate: `pullback = min(allocated_amount, remaining_shortage)`
   - Update `goal_allocations.allocated_amount` (reduce by pullback)
   - Update `goals.current_amount` (reduce by pullback)
   - Track reduction in response for user visibility
   - Reduce remaining shortage

**Protected Goals Tracking:**
- Log all skipped protected goals with:
  - Goal ID and title
  - Current allocation amount
  - Protection reason (if provided)

#### Tier 3: Deficit Recording (Last Resort)
- If `shortage > 0` after all pullbacks:
  - Add to `deficit_balance`
  - Record as expense transaction (category: "Deficit")
  - Include in response with clear messaging

**Response Data:**
```json
{
  "status": "expense_processed",
  "net_change": -5000.00,
  "funds_used": {
    "from_savings": 2000.00,
    "from_goals": 2500.00
  },
  "goal_reductions": [
    {
      "goal_id": "uuid",
      "goal_title": "Emergency Fund",
      "reduced_by": 1500.00,
      "new_allocation": 3500.00,
      "priority": 60.0
    }
  ],
  "protected_goals": [
    {
      "goal_id": "uuid",
      "goal_title": "House Down Payment",
      "amount": 5000.00,
      "reason": "User-protected"
    }
  ],
  "deficit_created": 500.00,
  "savings_balance": 0.00,
  "deficit_balance": 500.00
}
```

### 5. Goal Allocation (Positive Net Change with Available Funds)
After deficit repayment, if `available_funds > 0`:

#### Eligibility Filtering
- Exclude goals with `status = "completed"`
- Exclude goals with `is_locked = true`
- Calculate gap for each goal: `gap = target_amount - current_amount`
- Only allocate to goals with `gap > 0`

#### No Active Goals Scenario
- If no eligible goals exist:
  - All `available_funds` → `savings_balance`
  - Record as income transaction (category: "Saving")
  - Update snapshots and exit

#### Priority-Based Allocation
Calculate allocation for each eligible goal:
```python
# Calculate each goal's proportional share
share = goal_priority_percentage / total_priority_percentage
proposed_allocation = available_funds * share

# Cap at goal's remaining gap
final_allocation = min(proposed_allocation, goal_gap)
```

**Allocation Process:**
1. Create/update `goal_allocations` record for current month
2. Increment `goals.current_amount` by allocation
3. Track total allocated amount
4. Check for goal completion: `new_current >= target_amount`
5. Log newly completed goals

**Example:**
- Available funds: $1000
- Goal A: Priority 60%, Gap $800 → Allocates $600 (capped at gap)
- Goal B: Priority 40%, Gap $500 → Allocates $400
- Total allocated: $1000

#### Savings Remainder
- Calculate: `remaining = available_funds - total_allocated`
- If `remaining > 0`:
  - Add to `savings_balance`
  - Record as income transaction (category: "Saving")

### 6. Snapshot Updates (Critical for Change Detection)
After **every** allocation process (success or failure):
```python
profile.total_income_snapshot = current_total_income
profile.total_expense_snapshot = current_total_expense
profile.last_calculated_at = current_timestamp
```

**Why This Matters:**
- Ensures next calculation only processes new changes
- Prevents reprocessing of already-allocated transactions
- Maintains accurate delta calculations across sessions

### 7. Financial Profile State Management
The `financial_profile` table maintains:

| Field | Type | Purpose |
|-------|------|---------|
| `savings_balance` | Decimal | Accumulated unallocated surplus |
| `deficit_balance` | Decimal | Outstanding shortage requiring repayment |
| `total_income_snapshot` | Decimal | Last processed income total (for delta) |
| `total_expense_snapshot` | Decimal | Last processed expense total (for delta) |
| `last_calculated_at` | Timestamp | Last allocation calculation time |
| `include_savings_in_alloc` | Boolean | Whether to include existing savings in allocation pool |

### 8. Month-End Finalization
When current month closes (separate process):

1. **Lock Allocations**: Mark all `goal_allocations` for the month as finalized
2. **Finalization Check**: Prevent further modifications to finalized months
3. **Historical Integrity**: Past allocations become immutable
4. **Rollover Balances**: 
   - `savings_balance` carries forward to next month
   - `deficit_balance` carries forward for repayment
5. **Reset Workspace**: Clear temporary allocation state for new month

**Finalization Safety:**
- API checks if month is finalized before allowing recalculation
- Returns error if attempting to modify finalized period
- Ensures historical data integrity

### 9. Goal Protection Mechanisms
Users can protect goals from automatic pullback:

| Protection Level | Can Pull Back? | Use Case |
|------------------|----------------|----------|
| `flexible` (default) | ✅ Yes | Standard goals, can be adjusted |
| `protected` | ❌ No | Critical goals (e.g., emergency fund) |
| `is_locked = true` | ❌ No | User manually locked |
| `status = completed` | ❌ No | Already reached target |

**Protection Reason Field:**
- Optional user-provided explanation for why goal is protected
- Displayed in pullback skip notifications

### 10. Real-Time Transaction Processing
The system is designed to run **after each financial transaction**:

#### Transaction Flow
1. User records income/expense in `financial_records`
2. Transaction saved to database
3. Trigger: `POST /api/allocations/recalculate/<user_id>`
4. System calculates delta since last run
5. Processes incremental change only
6. Updates balances and allocations
7. Returns detailed summary to user

#### Performance Characteristics
- ✅ **Fast**: Only processes new changes (not entire month)
- ✅ **Accurate**: Snapshots prevent double-counting
- ✅ **Transparent**: Detailed response shows all actions taken
- ✅ **Idempotent**: Safe to call multiple times (early exit if no change)

### 11. Fund Categorization & Visibility
At any point, funds are categorized as:

| Category | Description | Source |
|----------|-------------|--------|
| **Allocated Goal Funds** | Committed to specific goals (current month) | `goal_allocations.allocated_amount` |
| **Goal Balances** | Cumulative funds in goals | `goals.current_amount` |
| **Savings Balance** | Available surplus (liquid) | `financial_profile.savings_balance` |
| **Deficit Balance** | Outstanding shortage | `financial_profile.deficit_balance` |
| **Protected Funds** | Goal allocations immune to pullback | Goals with `protection_level = "protected"` |

### 12. Transaction Logging
All allocation actions create `financial_records` entries with:
- `is_allocation_transaction = true` (distinguishes from user transactions)
- Appropriate category: "Saving" or "Deficit"
- Descriptive messages explaining the action
- Accurate timestamps for audit trail

**Example Categories:**
- **Saving (Income)**: Surplus saved, goal over-allocation saved, unallocated funds
- **Deficit (Expense)**: Shortage recorded after using all sources
- **Deficit (Income)**: Deficit repayment made

### 13. Edge Cases Handled

#### All Funds Used for Deficit Repayment
- If `available_funds <= 0` after repayment:
  - Update snapshots
  - Return success with balances
  - No goal allocation attempted

#### Goals Already Fully Funded
- If `total_gap <= 0` or no eligible goals:
  - All available funds → savings
  - Record savings transaction
  - Return "Goals already funded" status

#### Partial Deficit Repayment
- If only partial repayment possible:
  - Use all available funds for deficit
  - Update deficit balance
  - **Early exit** (no goal allocation)
  - Update snapshots

#### No Active Goals
- If no goals exist or all completed/locked:
  - All available funds → savings
  - Record savings transaction
  - Return "No active goals" status

## API Endpoint

### `POST /api/allocations/recalculate/<user_id>`

**Purpose**: Recalculate allocations based on latest financial data

**When to Call**:
- After recording any income/expense transaction
- Can be called multiple times (safe - checks for changes)

**Response Scenarios**:

#### 1. No Change Detected
```json
{
  "status": "success",
  "message": "No new transactions to process.",
  "savings_balance": 5000.00,
  "deficit_balance": 0.00
}
```

#### 2. Successful Allocation
```json
{
  "status": "success",
  "message": "Allocations processed successfully. 2 goal(s) completed!",
  "net_change": 10000.00,
  "allocations": [
    {
      "goal_id": "uuid",
      "goal_title": "Emergency Fund",
      "allocated_amount": 6000.00,
      "priority_percentage": 60.0,
      "new_total": 15000.00
    }
  ],
  "total_allocated": 8000.00,
  "remaining_savings_balance": 2000.00,
  "deficit_balance": 0.00,
  "newly_completed_goals": [
    {
      "goal_id": "uuid",
      "goal_title": "Vacation Fund",
      "final_amount": 5000.00
    }
  ]
}
```

#### 3. Expense Covered (With Pullback)
```json
{
  "status": "expense_processed",
  "message": "Expense processed using available funds. No deficit created.",
  "net_change": -3000.00,
  "funds_used": {
    "from_savings": 1000.00,
    "from_goals": 2000.00
  },
  "goal_reductions": [
    {
      "goal_id": "uuid",
      "goal_title": "Car Fund",
      "reduced_by": 2000.00,
      "new_allocation": 3000.00,
      "priority": 40.0
    }
  ],
  "protected_goals": [
    {
      "goal_id": "uuid",
      "goal_title": "Emergency Fund",
      "amount": 5000.00,
      "reason": "Critical emergency reserve"
    }
  ],
  "savings_balance": 0.00,
  "deficit_balance": 0.00
}
```

#### 4. Deficit Created
```json
{
  "status": "expense_processed",
  "message": "Expense processed using available funds. Deficit of 500.00 recorded.",
  "net_change": -5000.00,
  "funds_used": {
    "from_savings": 2000.00,
    "from_goals": 2500.00
  },
  "goal_reductions": [...],
  "protected_goals": [...],
  "deficit_created": 500.00,
  "savings_balance": 0.00,
  "deficit_balance": 500.00
}
```

#### 5. Partial Deficit Repayment
```json
{
  "status": "deficit_partial",
  "message": "Partial deficit repayment made. No allocations available.",
  "remaining_deficit": 2000.00
}
```

#### 6. Month Already Finalized
```json
{
  "status": "error",
  "message": "Month 2025-10 is already finalized. Cannot modify allocations.",
  "finalized_at": "2025-11-01T00:00:00Z"
}
```

## Key Features
- ✅ **Incremental Processing**: Only processes new transactions (delta-based)
- ✅ **Duplicate Prevention**: Snapshot system prevents reprocessing
- ✅ **Ethical Pullback**: Savings → Flexible Goals → Deficit (in order)
- ✅ **Goal Protection**: Multi-level protection system with user control
- ✅ **Smart Priority**: Pull from lowest-priority, least-complete goals first
- ✅ **Deficit Management**: Automatic repayment when funds available
- ✅ **Real-Time Updates**: Responds immediately to transactions
- ✅ **Transparent Actions**: Detailed response shows all changes made
- ✅ **Historical Integrity**: Finalized months are immutable
- ✅ **Audit Trail**: All actions logged as transactions

## Database Tables

### `financial_records`
- Stores all income/expense transactions
- `is_allocation_transaction` flag distinguishes system vs user entries
- Used to calculate monthly totals

### `financial_profile`
- `savings_balance`: Liquid surplus funds
- `deficit_balance`: Outstanding shortage
- `total_income_snapshot`: Last processed income (for delta)
- `total_expense_snapshot`: Last processed expense (for delta)
- `last_calculated_at`: Timestamp of last calculation
- `include_savings_in_alloc`: Config option

### `goals`
- `current_amount`: Cumulative funds allocated to goal
- `target_amount`: Goal target
- `status`: active/completed/paused
- `is_locked`: User lock flag
- `protection_level`: flexible/protected
- `protection_reason`: Optional explanation
- `is_essential`: Priority calculation factor

### `goal_allocations`
- `user_id`, `goal_id`, `month`: Composite key
- `allocated_amount`: Funds allocated this month
- `is_finalized`: Month closure flag
- `finalized_at`: Timestamp of finalization

### `goal_priorities`
- `goal_id`, `percentage`: Priority weight for allocation

## Technical Implementation Notes

### Decimal Precision
- All monetary calculations use `Decimal` type
- `quantize()` function ensures consistent precision
- Prevents floating-point arithmetic errors

### Transaction Safety
- Database transactions wrap all allocation logic
- Rollback on any error
- Ensures atomic updates across tables

### Logging
- Comprehensive logging at INFO level
- Tracks all decisions and calculations
- Essential for debugging and auditing

### Error Handling
- Try-catch wraps entire endpoint
- Rollback on exception
- Returns 500 with error message
- Logs full traceback for debugging

## Usage Example
```python
# After user records a transaction
response = requests.post(
    f"/api/allocations/recalculate/{user_id}"
)

if response.json()["status"] == "success":
    # Show allocations to user
    allocations = response.json()["allocations"]
    
elif response.json()["status"] == "expense_processed":
    # Show which goals were reduced
    reductions = response.json()["goal_reductions"]
    protected = response.json()["protected_goals"]
```

## Up Next
For the purpose of AI Finance Insights and how we spend
on ourselves, communities, Families

## Future Enhancements
- Scheduled month-end finalization automation
- Goal allocation forecasting
- What-if scenario modeling
- Allocation rule customization
- Multi-currency support
- Goal dependency chains (fund X before Y)