#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting setup..."

# Function to prompt user before a step
prompt_continue() {
    read -p "$1 [y/n]: " choice
    case "$choice" in
        y|Y ) echo "Proceeding...";;
        * ) echo "Skipping this step."; return 1;;
    esac
}

# Check for Python3 version
PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:3])))')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

echo "Detected Python version: $PYTHON_VERSION"

if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 13 ]; then
    echo "Warning: Python 3.13 or above detected. Some packages may not have relevant updates yet."
fi

# 1. Install pip
if prompt_continue "Do you want to install pip for Python3?"; then
    echo "Installing pip..."
    sudo apt update
    sudo apt install -y python3-pip
    pip3 --version
fi

# 2. Install python3.12-venv
if prompt_continue "Do you want to install python3.12-venv?"; then
    echo "Installing python3.12-venv..."
    sudo apt install -y python3.12-venv
fi


# --- 1. Check Python Version ---
REQUIRED_PYTHON="3.8"

# Get current Python version
if command -v python3 &>/dev/null; then
    PY_VERSION=$(python3 -V 2>&1 | awk '{print $2}')
else
    echo "❌ Python3 is not installed. Please install Python ${REQUIRED_PYTHON} or higher."
    exit 1
fi

# Compare versions
if [ "$(printf '%s\n' "$REQUIRED_PYTHON" "$PY_VERSION" | sort -V | head -n1)" != "$REQUIRED_PYTHON" ]; then
    echo "❌ Python version $PY_VERSION is lower than required $REQUIRED_PYTHON"
    exit 1
fi

echo "✅ Python version check passed: $PY_VERSION"

# --- 2. Check and create local virtual environment ---
if [ -d "local-env" ]; then
    echo "Virtual environment 'local-env' already exists."
    if prompt_continue "Do you want to use the existing virtual environment?"; then
        echo "Using existing virtual environment."
    else
        echo "Removing existing 'local-env'..."
        rm -rf local-env
        prompt_continue "Do you want to create a new virtual environment 'local-env'?" && python3 -m venv local-env
    fi
else
    prompt_continue "Do you want to create a virtual environment 'local-env'?" && python3 -m venv local-env
fi


# Activate virtual environment
echo "Activating virtual environment..."
source local-env/bin/activate

# 4. Install PostgreSQL and dependencies
if prompt_continue "Do you want to install PostgreSQL and dependencies?"; then
    echo "Installing PostgreSQL..."
    sudo apt install -y postgresql postgresql-contrib libpq-dev
    sudo systemctl enable postgresql
    sudo systemctl start postgresql
fi

# 5. Install Python packages from requirements.txt
if [ -f "requirements.txt" ]; then
    if prompt_continue "Do you want to install Python packages from requirements.txt in 'local-env'?"; then
        echo "Installing Python packages..."
        pip install --upgrade pip
        pip install -r requirements.txt
    fi
else
    echo "requirements.txt not found. Skipping Python package installation."
fi

echo "Setup complete!"

