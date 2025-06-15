#!/usr/bin/env python3
"""
PythonAnywhere Deployment Script for T3 Chat Clone
Run this script after uploading your files to PythonAnywhere
"""

import os
import sys
import subprocess

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    print("🚀 T3 Chat Clone - PythonAnywhere Deployment")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Please run this script from the django_app directory.")
        sys.exit(1)
    
    # Install requirements
    if not run_command("pip3.10 install --user -r requirements_pythonanywhere.txt", "Installing Python packages"):
        print("⚠️  Some packages may have failed to install. Check the output above.")
    
    # Set production settings
    os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_production'
    
    # Run migrations
    run_command("python3.10 manage.py migrate", "Running database migrations")
    
    # Collect static files
    run_command("python3.10 manage.py collectstatic --noinput", "Collecting static files")
    
    # Create superuser (optional)
    print("\n🔧 Creating superuser account...")
    print("You can create a superuser manually later with: python3.10 manage.py createsuperuser")
    
    # Setup demo data
    run_command("python3.10 manage.py setup_t3_chat", "Setting up demo data")
    
    print("\n" + "=" * 50)
    print("🎉 Deployment completed!")
    print("\n📋 Next steps:")
    print("1. Update your WSGI file in the PythonAnywhere web tab")
    print("2. Set your domain in ALLOWED_HOSTS in settings_production.py")
    print("3. Configure your API keys through the web interface")
    print("4. Reload your web app")
    print("\n🌐 Your app will be available at: https://yourusername.pythonanywhere.com")

if __name__ == "__main__":
    main() 