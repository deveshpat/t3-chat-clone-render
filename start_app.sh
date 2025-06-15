#!/bin/bash

# T3 Chat Clone - WORKING STARTUP SCRIPT
echo "🏆 Starting T3 Chat Clone..."

# Kill any existing processes
pkill -f "chainlit run app.py" 2>/dev/null

# Wait a moment
sleep 2

# Start the application with proper authentication
CHAINLIT_AUTH_SECRET="@5dtaCFDcBcrT?w>R8X1ihZK>*tVGoRU_PJ20B4,PJ1Y1tpQxSu0~92J:F~LLJTG" python3 -m chainlit run app.py -w --no-cache

echo "🌐 Application available at http://localhost:8000"
echo "🔐 Judge Login: t3 / clonethon"
echo "👤 Demo Login: demo / demo" 