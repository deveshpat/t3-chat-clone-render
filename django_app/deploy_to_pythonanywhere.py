#!/usr/bin/env python3
"""
Automated PythonAnywhere Deployment Script for T3 Chat Clone
Uses PythonAnywhere API to deploy the application
"""

import requests
import json
import os
import time
import subprocess

# PythonAnywhere API Configuration
USERNAME = 't3clone'
API_TOKEN = '7dbdc91099430b8976f7424594e954e5ad92cd4b'
DOMAIN_NAME = f'{USERNAME}.pythonanywhere.com'
BASE_URL = 'https://www.pythonanywhere.com/api/v0'

def api_request(method, endpoint, data=None):
    """Make API request to PythonAnywhere"""
    url = f"{BASE_URL}{endpoint}"
    headers = {
        'Authorization': f'Token {API_TOKEN}',
        'Content-Type': 'application/json'
    }
    
    if method.upper() == 'GET':
        response = requests.get(url, headers=headers)
    elif method.upper() == 'POST':
        response = requests.post(url, headers=headers, json=data)
    elif method.upper() == 'PATCH':
        response = requests.patch(url, headers=headers, json=data)
    elif method.upper() == 'DELETE':
        response = requests.delete(url, headers=headers)
    
    return response

def create_web_app():
    """Create a new web app"""
    print("🌐 Creating web app...")
    
    # Check if web app already exists
    response = api_request('GET', f'/user/{USERNAME}/webapps/')
    if response.status_code == 200:
        webapps = response.json()
        if any(app['domain_name'] == DOMAIN_NAME for app in webapps):
            print(f"✅ Web app {DOMAIN_NAME} already exists")
            return True
    
    # Create new web app
    data = {
        'domain_name': DOMAIN_NAME,
        'python_version': 'python310'
    }
    
    response = api_request('POST', f'/user/{USERNAME}/webapps/', data)
    if response.status_code == 201:
        print(f"✅ Web app created: {DOMAIN_NAME}")
        return True
    else:
        print(f"❌ Failed to create web app: {response.status_code} - {response.text}")
        return False

def upload_wsgi_file():
    """Update WSGI configuration"""
    print("📝 Updating WSGI configuration...")
    
    wsgi_content = f"""#!/usr/bin/env python3.10

import os
import sys

# Add your project directory to sys.path
path = '/home/{USERNAME}/t3-chat-clone/django_app'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_production'

from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler

application = StaticFilesHandler(get_wsgi_application())
"""
    
    # Update WSGI file via API
    data = {
        'content': wsgi_content
    }
    
    response = api_request('PATCH', f'/user/{USERNAME}/webapps/{DOMAIN_NAME}/wsgi_file/', data)
    if response.status_code == 200:
        print("✅ WSGI file updated")
        return True
    else:
        print(f"❌ Failed to update WSGI file: {response.status_code} - {response.text}")
        return False

def configure_static_files():
    """Configure static file mappings"""
    print("📁 Configuring static files...")
    
    static_mappings = [
        {
            'url': '/static/',
            'path': f'/home/{USERNAME}/t3-chat-clone/django_app/staticfiles/'
        },
        {
            'url': '/media/',
            'path': f'/home/{USERNAME}/t3-chat-clone/django_app/media/'
        }
    ]
    
    for mapping in static_mappings:
        response = api_request('POST', f'/user/{USERNAME}/webapps/{DOMAIN_NAME}/static_files/', mapping)
        if response.status_code == 201:
            print(f"✅ Static mapping added: {mapping['url']}")
        else:
            print(f"⚠️  Static mapping may already exist: {mapping['url']}")

def reload_web_app():
    """Reload the web application"""
    print("🔄 Reloading web app...")
    
    response = api_request('POST', f'/user/{USERNAME}/webapps/{DOMAIN_NAME}/reload/')
    if response.status_code == 200:
        print("✅ Web app reloaded successfully")
        return True
    else:
        print(f"❌ Failed to reload web app: {response.status_code} - {response.text}")
        return False

def run_local_setup():
    """Run local setup commands"""
    print("🔧 Running local setup...")
    
    commands = [
        "pip3.10 install --user -r requirements_pythonanywhere.txt",
        "python3.10 manage.py migrate --settings=config.settings_production",
        "python3.10 manage.py collectstatic --noinput --settings=config.settings_production",
        "python3.10 manage.py setup_t3_chat --settings=config.settings_production"
    ]
    
    for cmd in commands:
        print(f"Running: {cmd}")
        try:
            result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
            print(f"✅ Command completed: {cmd}")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Command failed: {cmd}")
            print(f"Error: {e.stderr}")

def update_settings():
    """Update production settings with correct domain"""
    print("⚙️  Updating production settings...")
    
    settings_file = 'config/settings_production.py'
    
    # Read current settings
    with open(settings_file, 'r') as f:
        content = f.read()
    
    # Update ALLOWED_HOSTS
    content = content.replace('yourusername.pythonanywhere.com', DOMAIN_NAME)
    content = content.replace('YOURUSERNAME', USERNAME)
    
    # Write updated settings
    with open(settings_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Settings updated for domain: {DOMAIN_NAME}")

def main():
    """Main deployment function"""
    print("🚀 T3 Chat Clone - Automated PythonAnywhere Deployment")
    print("=" * 60)
    print(f"Username: {USERNAME}")
    print(f"Domain: {DOMAIN_NAME}")
    print("=" * 60)
    
    # Check if we're in the right directory
    if not os.path.exists('manage.py'):
        print("❌ Error: manage.py not found. Please run this script from the django_app directory.")
        return False
    
    # Update settings first
    update_settings()
    
    # Run local setup
    run_local_setup()
    
    # Create web app
    if not create_web_app():
        return False
    
    # Upload WSGI file
    if not upload_wsgi_file():
        return False
    
    # Configure static files
    configure_static_files()
    
    # Reload web app
    if not reload_web_app():
        return False
    
    print("\n" + "=" * 60)
    print("🎉 Deployment completed successfully!")
    print("=" * 60)
    print(f"\n🌐 Your T3 Chat Clone is now live at:")
    print(f"   https://{DOMAIN_NAME}")
    print(f"\n🔑 Demo Accounts:")
    print(f"   • Judge: judge / judge123")
    print(f"   • Demo: demo / demo123")
    print(f"   • Admin: admin / t3chat123")
    print(f"\n📊 Admin Panel:")
    print(f"   https://{DOMAIN_NAME}/admin/")
    print(f"\n📝 Next Steps:")
    print(f"   1. Visit your live app and test the features")
    print(f"   2. Configure API keys in the settings")
    print(f"   3. Share the URL for the competition!")
    print("\n" + "=" * 60)
    
    return True

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🏆 Ready for T3 Chat Cloneathon submission!")
    else:
        print("\n❌ Deployment failed. Check the errors above.") 