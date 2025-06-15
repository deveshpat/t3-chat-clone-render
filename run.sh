#!/bin/bash

# T3 Chat Clone - Production Startup Script
# Competition Entry for T3 Chat Cloneathon

echo "🏆 T3 Chat Clone - Starting Competition Entry"
echo "=============================================="

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed."
    exit 1
fi

# Check if required packages are installed
echo "📦 Checking dependencies..."
python3 -c "import chainlit, openai, pygments, PIL, PyPDF2" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "📥 Installing required dependencies..."
    pip3 install chainlit openai pygments pillow PyPDF2
fi

# Initialize database and demo data
echo "🗄️ Setting up database..."
python3 demo.py

# Set authentication secret if not provided
if [ -z "$CHAINLIT_AUTH_SECRET" ]; then
    export CHAINLIT_AUTH_SECRET="@5dtaCFDcBcrT?w>R8X1ihZK>*tVGoRU_PJ20B4,PJ1Y1tpQxSu0~92J:F~LLJTG"
    echo "🔐 Authentication configured"
fi

echo ""
echo "🚀 JUDGE QUICK START GUIDE"
echo "=========================="
echo "1. 🔐 Login: t3 / clonethon (instant demo mode)"
echo "2. 💬 Type 'hello' or 'code' for feature showcase"
echo "3. 📎 Upload files to test attachment processing"
echo "4. 🔄 Refresh page to verify chat persistence"
echo "5. ✅ All features demonstrated in 30 seconds!"
echo ""
echo "🌐 Starting application at http://localhost:8000"
echo "⚡ Press Ctrl+C to stop"
echo ""

# Start the application
python3 -m chainlit run app.py -w --no-cache 