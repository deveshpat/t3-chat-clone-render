# 🚀 T3 Chat Clone - PythonAnywhere Deployment Guide

This guide will help you deploy the T3 Chat Clone to PythonAnywhere and get a live URL.

## 📋 Prerequisites

1. **PythonAnywhere Account**: Sign up at [pythonanywhere.com](https://www.pythonanywhere.com)
2. **Git Repository**: Your code should be in a Git repository (GitHub, GitLab, etc.)

## 🔧 Step-by-Step Deployment

### Step 1: Upload Your Code

**Option A: Using Git (Recommended)**
```bash
# In PythonAnywhere Bash console
cd ~
git clone https://github.com/yourusername/t3-chat-clone.git
cd t3-chat-clone/django_app
```

**Option B: Upload Files**
- Use PythonAnywhere's file manager to upload your `django_app` folder

### Step 2: Install Dependencies

```bash
# In PythonAnywhere Bash console
cd ~/t3-chat-clone/django_app
pip3.10 install --user -r requirements_pythonanywhere.txt
```

### Step 3: Run Deployment Script

```bash
python3.10 deploy_pythonanywhere.py
```

### Step 4: Configure Web App

1. Go to PythonAnywhere Dashboard → **Web** tab
2. Click **"Add a new web app"**
3. Choose **"Manual configuration"**
4. Select **Python 3.10**

### Step 5: Configure WSGI File

1. In the Web tab, click on **WSGI configuration file**
2. Replace the contents with:

```python
#!/usr/bin/env python3.10

import os
import sys

# Add your project directory to sys.path
path = '/home/YOURUSERNAME/t3-chat-clone/django_app'
if path not in sys.path:
    sys.path.insert(0, path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings_production'

from django.core.wsgi import get_wsgi_application
from django.contrib.staticfiles.handlers import StaticFilesHandler

application = StaticFilesHandler(get_wsgi_application())
```

**⚠️ Important**: Replace `YOURUSERNAME` with your actual PythonAnywhere username!

### Step 6: Configure Static Files

In the Web tab, add these static file mappings:

| URL | Directory |
|-----|-----------|
| `/static/` | `/home/YOURUSERNAME/t3-chat-clone/django_app/staticfiles/` |
| `/media/` | `/home/YOURUSERNAME/t3-chat-clone/django_app/media/` |

### Step 7: Update Settings

Edit `config/settings_production.py`:

```python
# Update ALLOWED_HOSTS with your domain
ALLOWED_HOSTS = [
    'YOURUSERNAME.pythonanywhere.com',
    'localhost',
    '127.0.0.1',
]

# Update CORS settings
CORS_ALLOWED_ORIGINS = [
    "https://YOURUSERNAME.pythonanywhere.com",
]
```

### Step 8: Reload Web App

1. Go back to the **Web** tab
2. Click **"Reload YOURUSERNAME.pythonanywhere.com"**

## 🎉 Your App is Live!

Your T3 Chat Clone will be available at:
**https://YOURUSERNAME.pythonanywhere.com**

## 🔑 Configure API Keys

1. Visit your live app
2. Register a new account or use demo accounts:
   - Username: `demo`, Password: `demo123`
   - Username: `judge`, Password: `judge123`
3. Go to settings and add your API keys:
   - **OpenRouter API Key** (required for AI chat)
   - **Tavily API Key** (optional for web search)

## 🛠️ Troubleshooting

### Common Issues:

**1. Import Errors**
```bash
# Check if all packages are installed
pip3.10 list --user
```

**2. Static Files Not Loading**
```bash
# Recollect static files
cd ~/t3-chat-clone/django_app
python3.10 manage.py collectstatic --noinput
```

**3. Database Issues**
```bash
# Reset database
python3.10 manage.py migrate --run-syncdb
python3.10 manage.py setup_t3_chat
```

**4. Permission Errors**
```bash
# Fix file permissions
chmod +x deploy_pythonanywhere.py
```

### Check Logs

View error logs in PythonAnywhere:
1. Go to **Web** tab
2. Click on **Error log** and **Server log**

## 📊 Features Available in Production

✅ **Core Features:**
- Chat with multiple AI models
- User authentication and registration
- Chat history and persistence
- File upload and processing
- Admin interface at `/admin/`

⚠️ **Limited Features (Free PythonAnywhere):**
- WebSocket real-time chat (disabled)
- Background tasks (Celery not available)
- Redis caching (using dummy cache)

## 🔄 Updating Your App

To update your deployed app:

```bash
# Pull latest changes
cd ~/t3-chat-clone
git pull origin main

# Update dependencies if needed
cd django_app
pip3.10 install --user -r requirements_pythonanywhere.txt

# Run migrations and collect static files
python3.10 manage.py migrate
python3.10 manage.py collectstatic --noinput

# Reload web app from PythonAnywhere dashboard
```

## 🎯 Competition Submission

Your live demo URL: **https://YOURUSERNAME.pythonanywhere.com**

### Demo Accounts for Judges:
- **Judge Account**: `judge` / `judge123`
- **Demo Account**: `demo` / `demo123`
- **Admin Account**: `admin` / `t3chat123`

### Key Features to Showcase:
1. **Multiple AI Models** - Try different models in settings
2. **File Upload** - Upload images, PDFs, or code files
3. **Chat History** - Multiple conversations with persistence
4. **Admin Interface** - Visit `/admin/` to see backend management
5. **API Documentation** - Visit `/api/docs/` for API reference

## 📞 Support

If you encounter issues:
1. Check the error logs in PythonAnywhere
2. Verify all file paths use your correct username
3. Ensure all dependencies are installed
4. Check that static files are properly collected

---

**🏆 Your T3 Chat Clone is now live and ready for the competition!** 