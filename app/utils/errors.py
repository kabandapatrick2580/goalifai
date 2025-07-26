import traceback
from functools import wraps
from flask import current_app, jsonify, request
from sqlalchemy.exc import (
    IntegrityError, OperationalError, ProgrammingError,
    DataError, DatabaseError, InterfaceError, InvalidRequestError
)
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound

def handle_db_errors(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except NoResultFound as e:
            """Handle cases where no result is found when one is expected."""
            current_app.logger.error(f"No result found: {e}")
            return jsonify({"error": "No result found"}, 404)
        except MultipleResultsFound as e:
            """Handle cases where multiple results are found when only one is expected."""
            current_app.logger.error(f"Multiple results found: {e}")
            return jsonify({"error": "Multiple results found"}, 400)
        except IntegrityError as e:
            """Handle integrity errors, such as unique constraint violations."""
            current_app.logger.error(f"Integrity error: {e.orig}")
            return jsonify({"error": "Integrity error"}), 400
        except DataError as e:
            """Handle data errors, such as invalid input data."""
            current_app.logger.error(f"Data error: {e.orig}")
            return jsonify({"error": "Invalid data input"}), 400
        except OperationalError as e:
            """Handle operational errors, such as connection issues."""
            current_app.logger.error(f"Operational error: {e.orig}")
            return jsonify({"error": "Database operation failed"}), 500
        except ProgrammingError as e:
            """Handle programming errors, such as syntax errors in SQL."""
            current_app.logger.error(f"Programming error: {e.orig}")
            return jsonify({"error": "Database programming error"}), 500
        except InterfaceError as e:
            """Handle interface errors, such as connection issues."""
            current_app.logger.error(f"Database interface error: {e.orig}")
            return jsonify({"error": "Database interface connection failed"}), 500
        except InvalidRequestError as e:
            """Handle invalid request errors, such as malformed queries."""
            current_app.logger.error(f"Invalid databse request: {e.orig}")
            return jsonify({"error": "Invalid database request"}), 400
        except DatabaseError as e:
            """Handle general database errors."""
            current_app.logger.error(f"Database error: {e.orig}")
            return jsonify({"error": "Generic Database error occurred"}), 500
        except Exception as e:
            """Catch-all for any other exceptions."""
            current_app.logger.error(f"Unhandled error: {e}")
            current_app.logger.error(traceback.format_exc())
            return jsonify({"error": "An unexpected error occurred"}), 500
    return wrapper