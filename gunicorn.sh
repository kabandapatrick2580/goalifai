#!/usr/bin/env bash

# Activate virtual environment
if [ -f "./local-engine/bin/activate" ]; then
    echo "Activating virtual environment..."
    source ./local-engine/bin/activate
else
    echo "Virtual environment not found! Exiting."
    exit 1
fi

# Test if the app can start
echo "Checking for errors in the app..."
python -m py_compile app.py 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Syntax errors detected in app.py! Please fix them before starting Gunicorn."
    deactivate
    exit 1
fi

# Optionally, test if required modules are installed
python -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Required modules missing (e.g., Flask). Please install dependencies in your virtual environment."
    deactivate
    exit 1
fi

# Start Gunicorn if all checks pass
echo "Starting Gunicorn..."
nohup gunicorn -k gevent --worker-connections 1000 -w 2 -b 0.0.0.0:8000 app:app > gunicorn.log 2>&1 &

echo "Gunicorn started in background (check gunicorn.log for logs)"
