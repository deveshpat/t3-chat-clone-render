#!/usr/bin/env python3
"""
T3 Chat Clone - Comprehensive Feature Testing Script
Tests all competition requirements and bonus features
"""

import requests
import sqlite3
import os
import time
import json
from pathlib import Path

def test_application_running():
    """Test if the application is accessible"""
    try:
        response = requests.get("http://localhost:8000", timeout=5)
        print(f"✅ Application Running: HTTP {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Application Not Running: {e}")
        return False

def test_database_setup():
    """Test if SQLite database is properly initialized"""
    try:
        conn = sqlite3.connect('chat_history.db')
        cursor = conn.cursor()
        
        # Check if tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = ['conversations', 'messages']
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            print(f"❌ Database Missing Tables: {missing_tables}")
            return False
        
        # Check table structure
        cursor.execute("PRAGMA table_info(conversations);")
        conv_columns = [row[1] for row in cursor.fetchall()]
        
        cursor.execute("PRAGMA table_info(messages);")
        msg_columns = [row[1] for row in cursor.fetchall()]
        
        print(f"✅ Database Setup: Tables {tables}")
        print(f"✅ Conversations Columns: {conv_columns}")
        print(f"✅ Messages Columns: {msg_columns}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Database Error: {e}")
        return False

def test_file_processing():
    """Test file processing utilities"""
    try:
        # Test imports
        from app import process_image, process_pdf, process_text_file, highlight_code
        
        # Test syntax highlighting
        test_code = "def hello():\n    print('Hello World')"
        highlighted = highlight_code(test_code, "python")
        
        if "<pre" in highlighted or "<code" in highlighted:
            print("✅ Syntax Highlighting: Working")
        else:
            print("❌ Syntax Highlighting: Failed")
            return False
            
        print("✅ File Processing: Imports successful")
        return True
        
    except Exception as e:
        print(f"❌ File Processing Error: {e}")
        return False

def test_authentication_setup():
    """Test authentication callback"""
    try:
        from app import auth_callback
        
        # Test judge credentials
        judge_user = auth_callback("t3", "clonethon")
        if judge_user and judge_user.identifier == "t3_judge":
            print("✅ Judge Authentication: Working")
        else:
            print("❌ Judge Authentication: Failed")
            return False
            
        # Test demo credentials
        demo_user = auth_callback("demo", "demo")
        if demo_user and demo_user.identifier == "demo_user":
            print("✅ Demo Authentication: Working")
        else:
            print("❌ Demo Authentication: Failed")
            return False
            
        # Test invalid credentials
        invalid_user = auth_callback("invalid", "invalid")
        if invalid_user is None:
            print("✅ Invalid Authentication: Properly rejected")
        else:
            print("❌ Invalid Authentication: Security issue")
            return False
            
        return True
        
    except Exception as e:
        print(f"❌ Authentication Error: {e}")
        return False

def test_demo_responses():
    """Test demo mode responses"""
    try:
        from app import DEMO_RESPONSES
        
        required_keys = ["hello", "code", "default"]
        missing_keys = [k for k in required_keys if k not in DEMO_RESPONSES]
        
        if missing_keys:
            print(f"❌ Demo Responses Missing: {missing_keys}")
            return False
            
        # Check content quality
        for key, response in DEMO_RESPONSES.items():
            if len(response) < 50:
                print(f"❌ Demo Response Too Short: {key}")
                return False
                
        print(f"✅ Demo Responses: {len(DEMO_RESPONSES)} responses ready")
        return True
        
    except Exception as e:
        print(f"❌ Demo Responses Error: {e}")
        return False

def test_environment_setup():
    """Test environment and dependencies"""
    try:
        # Test required imports
        import chainlit
        import openai
        import pygments
        import PIL
        import PyPDF2
        
        print("✅ Dependencies: All imports successful")
        
        # Test environment variables
        auth_secret = os.environ.get('CHAINLIT_AUTH_SECRET')
        if auth_secret:
            print("✅ Environment: AUTH_SECRET configured")
        else:
            print("⚠️ Environment: AUTH_SECRET not set (may need manual setup)")
            
        return True
        
    except ImportError as e:
        print(f"❌ Dependencies Missing: {e}")
        return False
    except Exception as e:
        print(f"❌ Environment Error: {e}")
        return False

def test_file_structure():
    """Test if all required files exist"""
    required_files = [
        'app.py',
        'demo.py', 
        'requirements.txt',
        'README.md',
        'SUBMISSION.md',
        'run.sh'
    ]
    
    missing_files = []
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
            
    if missing_files:
        print(f"❌ Missing Files: {missing_files}")
        return False
        
    print(f"✅ File Structure: All {len(required_files)} files present")
    return True

def test_api_integration():
    """Test OpenAI/OpenRouter integration setup"""
    try:
        from openai import AsyncOpenAI
        
        # Test client creation (without actual API call)
        client = AsyncOpenAI(
            api_key="test-key",
            base_url="https://openrouter.ai/api/v1"
        )
        
        print("✅ API Integration: Client setup working")
        return True
        
    except Exception as e:
        print(f"❌ API Integration Error: {e}")
        return False

def run_comprehensive_test():
    """Run all tests and provide summary"""
    print("🏆 T3 Chat Clone - Comprehensive Feature Testing")
    print("=" * 50)
    
    tests = [
        ("Application Running", test_application_running),
        ("Database Setup", test_database_setup),
        ("File Processing", test_file_processing),
        ("Authentication", test_authentication_setup),
        ("Demo Responses", test_demo_responses),
        ("Environment Setup", test_environment_setup),
        ("File Structure", test_file_structure),
        ("API Integration", test_api_integration),
    ]
    
    results = {}
    for test_name, test_func in tests:
        print(f"\n🔍 Testing: {test_name}")
        print("-" * 30)
        results[test_name] = test_func()
    
    print("\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Overall Score: {passed}/{total} ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🏆 ALL TESTS PASSED - COMPETITION READY!")
    else:
        print("⚠️ SOME TESTS FAILED - NEEDS ATTENTION")
        
    return passed == total

if __name__ == "__main__":
    run_comprehensive_test() 