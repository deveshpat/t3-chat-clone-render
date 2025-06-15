#!/usr/bin/env python3
"""
Simplified PythonAnywhere Deployment Script for T3 Chat Clone
"""

import requests
import json

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
    
    print(f"Making {method} request to: {url}")
    if data:
        print(f"Data: {json.dumps(data, indent=2)}")
    
    try:
        if method.upper() == 'GET':
            response = requests.get(url, headers=headers)
        elif method.upper() == 'POST':
            response = requests.post(url, headers=headers, json=data)
        elif method.upper() == 'PATCH':
            response = requests.patch(url, headers=headers, json=data)
        elif method.upper() == 'DELETE':
            response = requests.delete(url, headers=headers)
        
        print(f"Response: {response.status_code}")
        if response.text:
            print(f"Response body: {response.text}")
        
        return response
    except Exception as e:
        print(f"Error making request: {e}")
        return None

def check_account():
    """Check account status"""
    print("🔍 Checking account status...")
    response = api_request('GET', f'/user/{USERNAME}/cpu/')
    if response and response.status_code == 200:
        print("✅ Account access confirmed")
        return True
    else:
        print("❌ Account access failed")
        return False

def list_webapps():
    """List existing web apps"""
    print("📋 Listing existing web apps...")
    response = api_request('GET', f'/user/{USERNAME}/webapps/')
    if response and response.status_code == 200:
        webapps = response.json()
        print(f"Found {len(webapps)} web apps:")
        for app in webapps:
            print(f"  - {app.get('domain_name', 'Unknown')}")
        return webapps
    return []

def create_web_app():
    """Create a new web app"""
    print("🌐 Creating web app...")
    
    # First check if it exists
    webapps = list_webapps()
    if any(app.get('domain_name') == DOMAIN_NAME for app in webapps):
        print(f"✅ Web app {DOMAIN_NAME} already exists")
        return True
    
    # Create new web app - try different approaches
    data_options = [
        {
            'domain_name': DOMAIN_NAME,
            'python_version': 'python310'
        },
        {
            'domain_name': DOMAIN_NAME,
            'python_version': '3.10'
        },
        {
            'domain_name': DOMAIN_NAME
        }
    ]
    
    for i, data in enumerate(data_options):
        print(f"Attempt {i+1}: Creating web app with data: {data}")
        response = api_request('POST', f'/user/{USERNAME}/webapps/', data)
        if response and response.status_code == 201:
            print(f"✅ Web app created: {DOMAIN_NAME}")
            return True
        elif response:
            print(f"❌ Attempt {i+1} failed: {response.status_code} - {response.text}")
    
    return False

def main():
    """Main function"""
    print("🚀 T3 Chat Clone - Simple PythonAnywhere Deployment")
    print("=" * 60)
    print(f"Username: {USERNAME}")
    print(f"Domain: {DOMAIN_NAME}")
    print("=" * 60)
    
    # Check account access
    if not check_account():
        print("❌ Cannot access PythonAnywhere account")
        return False
    
    # List existing web apps
    list_webapps()
    
    # Create web app
    if create_web_app():
        print("\n" + "=" * 60)
        print("🎉 Web app setup initiated!")
        print("=" * 60)
        print(f"\n🌐 Your domain will be: https://{DOMAIN_NAME}")
        print(f"\n📋 Manual steps needed:")
        print(f"1. Upload your code to PythonAnywhere")
        print(f"2. Configure WSGI file")
        print(f"3. Set up static files")
        print(f"4. Install dependencies")
        print(f"5. Run migrations")
        print("\nSee DEPLOYMENT_GUIDE.md for detailed instructions.")
        return True
    else:
        print("❌ Failed to create web app")
        return False

if __name__ == "__main__":
    main() 