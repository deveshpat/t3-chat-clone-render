#!/usr/bin/env python3
"""
T3 Chat Clone - COMPREHENSIVE TESTING SCRIPT
Tests every single feature to ensure competition readiness
"""

import requests
import sqlite3
import os
import time
import json
import subprocess
import sys
from pathlib import Path

class T3ChatTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.db_path = "chat_history.db"
        self.passed_tests = 0
        self.failed_tests = 0
        self.test_results = []

    def log_test(self, test_name, passed, message=""):
        """Log test result"""
        status = "✅ PASS" if passed else "❌ FAIL"
        result = f"{status}: {test_name}"
        if message:
            result += f" - {message}"
        print(result)
        self.test_results.append(result)
        
        if passed:
            self.passed_tests += 1
        else:
            self.failed_tests += 1

    def test_application_running(self):
        """Test if application is accessible"""
        try:
            response = requests.get(self.base_url, timeout=10)
            self.log_test("Application Running", response.status_code == 200, f"HTTP {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            self.log_test("Application Running", False, str(e))
            return False

    def test_database_setup(self):
        """Test database initialization"""
        try:
            if not os.path.exists(self.db_path):
                self.log_test("Database File Exists", False, "Database file not found")
                return False
            
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Test conversations table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversations'")
            conversations_table = cursor.fetchone()
            
            # Test messages table
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
            messages_table = cursor.fetchone()
            
            conn.close()
            
            tables_exist = conversations_table and messages_table
            self.log_test("Database Tables", tables_exist, "conversations and messages tables")
            return tables_exist
            
        except Exception as e:
            self.log_test("Database Setup", False, str(e))
            return False

    def test_database_operations(self):
        """Test database CRUD operations"""
        try:
            # Import the database functions
            sys.path.append('.')
            from app import init_database, create_conversation, save_message, get_conversation_history
            
            # Initialize database
            init_database()
            
            # Test conversation creation
            conv_id = create_conversation("test_user", "Test Conversation")
            self.log_test("Create Conversation", bool(conv_id), f"Created conversation: {conv_id}")
            
            # Test message saving
            save_message(conv_id, "user", "Test message", "test-model")
            save_message(conv_id, "assistant", "Test response", "test-model")
            
            # Test message retrieval
            history = get_conversation_history(conv_id)
            messages_saved = len(history) == 2
            self.log_test("Save/Retrieve Messages", messages_saved, f"Retrieved {len(history)} messages")
            
            return bool(conv_id) and messages_saved
            
        except Exception as e:
            self.log_test("Database Operations", False, str(e))
            return False

    def test_file_processing(self):
        """Test file processing utilities"""
        try:
            sys.path.append('.')
            from app import process_text_file, highlight_code, detect_and_highlight_code
            
            # Test text file processing
            test_content = "Hello, this is a test file!"
            with open("test_file.txt", "w") as f:
                f.write(test_content)
            
            processed = process_text_file("test_file.txt")
            text_processing_works = test_content in processed
            self.log_test("Text File Processing", text_processing_works)
            
            # Test code highlighting
            test_code = "def hello():\n    print('Hello World')"
            highlighted = highlight_code(test_code, "python")
            highlighting_works = "<pre" in highlighted and "def" in highlighted
            self.log_test("Code Highlighting", highlighting_works)
            
            # Test code detection
            markdown_code = "```python\ndef test():\n    pass\n```"
            detected = detect_and_highlight_code(markdown_code)
            detection_works = "<pre" in detected
            self.log_test("Code Detection", detection_works)
            
            # Cleanup
            os.remove("test_file.txt")
            
            return text_processing_works and highlighting_works and detection_works
            
        except Exception as e:
            self.log_test("File Processing", False, str(e))
            return False

    def test_authentication_logic(self):
        """Test authentication callback"""
        try:
            sys.path.append('.')
            from app import auth_callback
            
            # Test judge credentials
            judge_user = auth_callback("t3", "clonethon")
            judge_auth_works = judge_user and judge_user.identifier == "t3_judge"
            self.log_test("Judge Authentication", judge_auth_works)
            
            # Test demo credentials
            demo_user = auth_callback("demo", "demo")
            demo_auth_works = demo_user and demo_user.identifier == "demo_user"
            self.log_test("Demo Authentication", demo_auth_works)
            
            # Test invalid credentials
            invalid_user = auth_callback("invalid", "invalid")
            invalid_auth_works = invalid_user is None
            self.log_test("Invalid Authentication", invalid_auth_works)
            
            return judge_auth_works and demo_auth_works and invalid_auth_works
            
        except Exception as e:
            self.log_test("Authentication Logic", False, str(e))
            return False

    def test_demo_responses(self):
        """Test demo mode responses"""
        try:
            sys.path.append('.')
            from app import DEMO_RESPONSES
            
            # Test demo responses exist
            required_keys = ["hello", "code", "default"]
            responses_exist = all(key in DEMO_RESPONSES for key in required_keys)
            self.log_test("Demo Responses Exist", responses_exist)
            
            # Test response content
            hello_response = DEMO_RESPONSES.get("hello", "")
            hello_valid = "Welcome" in hello_response and len(hello_response) > 100
            self.log_test("Hello Response Valid", hello_valid)
            
            code_response = DEMO_RESPONSES.get("code", "")
            code_valid = "```python" in code_response and "def" in code_response
            self.log_test("Code Response Valid", code_valid)
            
            return responses_exist and hello_valid and code_valid
            
        except Exception as e:
            self.log_test("Demo Responses", False, str(e))
            return False

    def test_imports_and_dependencies(self):
        """Test all required imports work"""
        try:
            import chainlit as cl
            self.log_test("Chainlit Import", True)
            
            import openai
            self.log_test("OpenAI Import", True)
            
            import pygments
            self.log_test("Pygments Import", True)
            
            from PIL import Image
            self.log_test("PIL Import", True)
            
            import PyPDF2
            self.log_test("PyPDF2 Import", True)
            
            import sqlite3
            self.log_test("SQLite3 Import", True)
            
            return True
            
        except Exception as e:
            self.log_test("Imports and Dependencies", False, str(e))
            return False

    def test_environment_setup(self):
        """Test environment and configuration"""
        try:
            # Test if auth secret is set
            auth_secret = os.environ.get("CHAINLIT_AUTH_SECRET")
            auth_secret_set = bool(auth_secret)
            self.log_test("Auth Secret Set", auth_secret_set)
            
            # Test if required files exist
            required_files = ["app.py", "requirements.txt", "README.md"]
            files_exist = all(os.path.exists(f) for f in required_files)
            self.log_test("Required Files Exist", files_exist)
            
            return auth_secret_set and files_exist
            
        except Exception as e:
            self.log_test("Environment Setup", False, str(e))
            return False

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print("🏆 T3 CHAT CLONE - COMPREHENSIVE TEST SUITE")
        print("=" * 50)
        print()
        
        # Test categories
        test_categories = [
            ("Environment & Dependencies", [
                self.test_imports_and_dependencies,
                self.test_environment_setup
            ]),
            ("Database & Storage", [
                self.test_database_setup,
                self.test_database_operations
            ]),
            ("Core Functionality", [
                self.test_file_processing,
                self.test_authentication_logic,
                self.test_demo_responses
            ]),
            ("Application Runtime", [
                self.test_application_running
            ])
        ]
        
        for category_name, tests in test_categories:
            print(f"📋 {category_name}")
            print("-" * 30)
            
            for test_func in tests:
                test_func()
            
            print()
        
        # Final results
        print("🏆 FINAL TEST RESULTS")
        print("=" * 50)
        total_tests = self.passed_tests + self.failed_tests
        pass_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        print(f"✅ Passed: {self.passed_tests}")
        print(f"❌ Failed: {self.failed_tests}")
        print(f"📊 Pass Rate: {pass_rate:.1f}%")
        print()
        
        if self.failed_tests == 0:
            print("🎉 ALL TESTS PASSED! Competition ready! 🏆")
        else:
            print("⚠️  Some tests failed. Review and fix issues above.")
            print()
            print("Failed tests:")
            for result in self.test_results:
                if "❌ FAIL" in result:
                    print(f"  {result}")
        
        return self.failed_tests == 0

def main():
    """Main test execution"""
    tester = T3ChatTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 