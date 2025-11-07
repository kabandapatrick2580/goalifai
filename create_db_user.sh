#!/usr/bin/env bash
set -e  # Exit immediately if a command fails

# === Configuration ===
DB_NAME="goalifai"
DB_USER="patrick"
DB_PASSWORD="pass123"

# === Execution ===
echo "Creating PostgreSQL user and database..."

# Create user if it doesn't exist
psql -v ON_ERROR_STOP=1 --username=postgres <<-EOSQL
DO
\$do\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles WHERE rolname = '${DB_USER}'
   ) THEN
      CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
      RAISE NOTICE 'User ${DB_USER} created.';
   ELSE
      RAISE NOTICE 'User ${DB_USER} already exists.';
   END IF;
END
\$do\$;
EOSQL

# Create database if it doesn't exist
psql -v ON_ERROR_STOP=1 --username=postgres <<-EOSQL
DO
\$do\$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_database WHERE datname = '${DB_NAME}'
   ) THEN
      CREATE DATABASE ${DB_NAME} OWNER ${DB_USER};
      RAISE NOTICE 'Database ${DB_NAME} created and assigned to ${DB_USER}.';
   ELSE
      RAISE NOTICE 'Database ${DB_NAME} already exists.';
   END IF;
END
\$do\$;
EOSQL

echo "✅ PostgreSQL user '${DB_USER}' and database '${DB_NAME}' setup complete."
