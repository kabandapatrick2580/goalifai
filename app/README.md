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
10. Auto carry over the surplus.
