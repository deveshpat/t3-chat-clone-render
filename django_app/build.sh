#!/bin/bash

# Build script for T3 Chat Clone Django deployment
set -o errexit  # Exit on error

echo "🚀 Starting T3 Chat Clone build..."

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements_render.txt

# Set Django settings
export DJANGO_SETTINGS_MODULE=config.settings_production

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "🗄️ Running database migrations..."
python manage.py migrate

# Create demo users
echo "👤 Creating demo users..."
python manage.py shell -c "
from django.contrib.auth.models import User
try:
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@t3chat.com', 't3chat123')
        print('✅ Admin user created')
    if not User.objects.filter(username='demo').exists():
        User.objects.create_user('demo', 'demo@t3chat.com', 'demo123')
        print('✅ Demo user created')
    if not User.objects.filter(username='judge').exists():
        User.objects.create_user('judge', 'judge@t3chat.com', 'judge123')
        print('✅ Judge user created')
except Exception as e:
    print(f'⚠️ User creation error: {e}')
"

echo "🎉 Build completed successfully!" 