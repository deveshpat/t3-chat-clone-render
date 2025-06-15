
# 🚀 T3 Chat Clone - Render Deployment Guide

## Automated Deployment (Recommended)

Your app is ready for deployment! Follow these simple steps:

### Step 1: Deploy to Render.com
1. Go to [render.com](https://render.com) and create a free account
2. Click "New +" → "Web Service"
3. Connect your GitHub account
4. Select this repository: `t3-chat-clone-render`
5. Use these settings:
   - **Name**: `t3-chat-clone`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements_chainlit.txt`
   - **Start Command**: `chainlit run app.py --host 0.0.0.0 --port $PORT`
6. Click "Create Web Service"

### Step 2: Set Environment Variables
In your Render dashboard, go to Environment and add:
- `CHAINLIT_AUTH_SECRET`: Generate a random secret (or use: `t3-chat-secret-2024`)

### Step 3: Access Your App
- Your app will be live at: `https://t3-chat-clone.onrender.com`
- Judge login: `t3` / `clonethon`
- Demo login: `demo` / `demo`

## Features Included ✅
- 🤖 Multiple AI Models (OpenRouter integration)
- 🔐 Authentication & User Management
- 📎 File Upload Support (Images, PDFs, Text)
- 🎨 Syntax Highlighting
- 💾 Chat History Persistence
- 🔍 Web Search Integration
- 📱 Mobile-Friendly Interface

## Competition Ready! 🏆
This deployment meets all T3 Chat Cloneathon requirements:
- Core features: ✅ All implemented
- Bonus features: ✅ All implemented
- Easy to try: ✅ Judge demo mode
- Browser friendly: ✅ Web-based interface

**Total deployment time: ~5 minutes**
**Cost: $0 (Free tier)**
