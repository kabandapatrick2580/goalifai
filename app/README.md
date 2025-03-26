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
```

next:
implementation of financial records
    1. User profile has to be one per user
implementation of categories