## Installation of Flask migrate
### steps:
1. pip install Flask-Migrate
2. Added the following code in the app/__init__.py file
```
from flask_migrate import Migrate
migrate = Migrate(app, db)
```
3. Run the following command to create the migration repository
```
export FLASK_APP=app
flask db init
```

4. Run the following command to create the migration script
```
flask db migrate
# undoing the last migration
flask db migrate --rev-id <revision_id> # to undo the last migration where <revision_id> is the id of the last migration

```

next:
implementation of financial records
    1. User profile has to be one per user
implementation of categories


implementation of financial recording
1. Fetch the currencies to populate the dropdown
2. fetch the categories to populate the dropdown

Goal funds reallocation
1. Track the total income and total expense from the financial records table or financial profile

2. the user_id and the current month as well as the goal priorities to calculate the goal weights and funds
3. When the income is super high, regulate to avoid allocating more funds than what are required
4. and also when the income is lower than the expense
5. THe structure of funds after the financial month closes to secure the allocated funds
6. The monthly allocated funds are added to the goals' current amount
7. making sure that the allocated goal funds are sealed not changeable at the next reallocation
8. The expense and income have to reflect to monthly funds allocation and being able to handle the funds allocated earlier in other months
9. the solution is to record the surplus as income or deficit as an expense at the end of the month which will be based on the next month, before goal funds allocation.
10. update the user financial profile to record savings balance and deficit balance.
11. Updated the user financial profile to record the funds allocation rate in order to allocate only the portion of the available funds and the remaining are saved in savings(surplus). and if the calculations happens and the expense happen to exceed the income, record a deficit balance instead of a savings balance.

12. Update the goal current amount
13. Reallocate funds on recalculation, update the financial record where expense called deficit was recorded, and income where savings were recorded.
14. fund recalculation and goal allocation is expected to run frequently and let's say we've got a surplus income which will be distribute to cover the deficits or get saved as a saving at first time, but if it runs for the second time, becaue the income and expenses nothing changed, it may save a saving or a deficit without taking into account that no changes made in income and expenses.
    - Solution: to record the total income and total expenses at the first time of allocation, and when run for another time before updating the deficit or savings balances, compare the current income and expenses balances with those during the first time

15. within that same month if expenses happen to exceed the income, the goal allocations shall reduce as well
