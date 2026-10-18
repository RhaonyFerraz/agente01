#!/usr/bin/env bash
# Exit on error
set -o errexit

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input

# Apply database migrations (Supabase PostgreSQL)
python manage.py migrate

# Seed initial themes and preferences
python seed_data.py
