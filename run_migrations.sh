#!/bin/bash

# Prompt for migration message
read -p "Enter migration message: " MESSAGE

if [ -z "$MESSAGE" ]; then
    echo "Migration message cannot be empty."
    exit 1
fi

# Run migration
echo "Generating migration..."
flask db migrate -m "$MESSAGE"

if [ $? -ne 0 ]; then
    echo "Migration generation failed."
    exit 1
fi

# Apply migration
echo "Applying migration..."
flask db upgrade

if [ $? -ne 0 ]; then
    echo "Migration upgrade failed."
    exit 1
fi

echo "Migration completed successfully."

