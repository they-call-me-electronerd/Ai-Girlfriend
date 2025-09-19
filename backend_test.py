#!/usr/bin/env python3
"""
Backend API Testing for Gemini Chatbot
Tests all backend endpoints with real API calls
"""

import requests
import json
import time
import os
from datetime import datetime

# Load environment variables
BACKEND_URL = "https://gemini-chat-16.preview.emergentagent.com/api"
GEMINI_API_KEY = "AIzaSyBf-YLHLu6RLz9GOa96qnr0RztBNazAy7U"

class GeminiChatbotTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.session = requests.Session()
        self.test_session_id = None
        self.test_results = []
        
    def log_test(self, test_name, success, message, details=None):
        """Log test results"""
        result = {
            "test": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "details": details
        }
        self.test_results.append(result)
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details and not success:
            print(f"   Details: {details}")
    
    def test_root_endpoint(self):
        """Test the root API endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/")
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_test("Root Endpoint", True, "API root accessible")
                    return True
                else:
                    self.log_test("Root Endpoint", False, "Unexpected response format", data)
                    return False
            else:
                self.log_test("Root Endpoint", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Root Endpoint", False, f"Connection error: {str(e)}")
            return False
    
    def test_create_session(self):
        """Test POST /api/sessions - Create new chat session"""
        try:
            payload = {"title": "Test Chat Session"}
            response = self.session.post(
                f"{self.base_url}/sessions",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                data = response.json()
                if "id" in data and "title" in data:
                    self.test_session_id = data["id"]
                    self.log_test("Create Session", True, f"Session created with ID: {self.test_session_id}")
                    return True
                else:
                    self.log_test("Create Session", False, "Missing required fields in response", data)
                    return False
            else:
                self.log_test("Create Session", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Create Session", False, f"Request error: {str(e)}")
            return False
    
    def test_list_sessions(self):
        """Test GET /api/sessions - List all chat sessions"""
        try:
            response = self.session.get(f"{self.base_url}/sessions")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    session_count = len(data)
                    self.log_test("List Sessions", True, f"Retrieved {session_count} sessions")
                    
                    # Verify our test session is in the list
                    if self.test_session_id:
                        session_found = any(session.get("id") == self.test_session_id for session in data)
                        if session_found:
                            self.log_test("Session Persistence", True, "Test session found in session list")
                        else:
                            self.log_test("Session Persistence", False, "Test session not found in session list")
                    return True
                else:
                    self.log_test("List Sessions", False, "Response is not a list", data)
                    return False
            else:
                self.log_test("List Sessions", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("List Sessions", False, f"Request error: {str(e)}")
            return False
    
    def test_send_chat_message(self):
        """Test POST /api/chat - Send message and get Gemini AI response (MOST IMPORTANT)"""
        if not self.test_session_id:
            self.log_test("Send Chat Message", False, "No test session available")
            return False
        
        try:
            # Test message that should get a meaningful response from Gemini
            test_message = "Hello! Can you tell me what 2+2 equals and explain why?"
            payload = {
                "session_id": self.test_session_id,
                "content": test_message
            }
            
            response = self.session.post(
                f"{self.base_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30  # Gemini API might take some time
            )
            
            if response.status_code == 200:
                data = response.json()
                if "user_message" in data and "assistant_message" in data:
                    user_msg = data["user_message"]
                    assistant_msg = data["assistant_message"]
                    
                    # Verify user message structure
                    if user_msg.get("content") == test_message and user_msg.get("role") == "user":
                        # Verify assistant message structure
                        if assistant_msg.get("role") == "assistant" and assistant_msg.get("content"):
                            assistant_content = assistant_msg.get("content")
                            # Check if response seems reasonable (contains "4" for 2+2 question)
                            if "4" in assistant_content or "four" in assistant_content.lower():
                                self.log_test("Gemini AI Integration", True, f"Gemini responded correctly: {assistant_content[:100]}...")
                                self.log_test("Send Chat Message", True, "Chat message sent and AI response received")
                                return True
                            else:
                                self.log_test("Gemini AI Integration", False, f"Unexpected AI response: {assistant_content[:100]}...")
                                return False
                        else:
                            self.log_test("Send Chat Message", False, "Invalid assistant message structure", assistant_msg)
                            return False
                    else:
                        self.log_test("Send Chat Message", False, "Invalid user message structure", user_msg)
                        return False
                else:
                    self.log_test("Send Chat Message", False, "Missing required fields in response", data)
                    return False
            else:
                self.log_test("Send Chat Message", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Send Chat Message", False, f"Request error: {str(e)}")
            return False
    
    def test_get_chat_history(self):
        """Test GET /api/sessions/{session_id}/messages - Get chat history"""
        if not self.test_session_id:
            self.log_test("Get Chat History", False, "No test session available")
            return False
        
        try:
            response = self.session.get(f"{self.base_url}/sessions/{self.test_session_id}/messages")
            
            if response.status_code == 200:
                data = response.json()
                if isinstance(data, list):
                    message_count = len(data)
                    if message_count >= 2:  # Should have user + assistant messages
                        # Verify message structure
                        has_user_msg = any(msg.get("role") == "user" for msg in data)
                        has_assistant_msg = any(msg.get("role") == "assistant" for msg in data)
                        
                        if has_user_msg and has_assistant_msg:
                            self.log_test("Get Chat History", True, f"Retrieved {message_count} messages with correct roles")
                            return True
                        else:
                            self.log_test("Get Chat History", False, "Missing user or assistant messages", data)
                            return False
                    else:
                        self.log_test("Get Chat History", False, f"Expected at least 2 messages, got {message_count}")
                        return False
                else:
                    self.log_test("Get Chat History", False, "Response is not a list", data)
                    return False
            else:
                self.log_test("Get Chat History", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Get Chat History", False, f"Request error: {str(e)}")
            return False
    
    def test_multi_turn_conversation(self):
        """Test multi-turn conversation flow"""
        if not self.test_session_id:
            self.log_test("Multi-turn Conversation", False, "No test session available")
            return False
        
        try:
            # Send a follow-up message
            follow_up_message = "What about 3+3?"
            payload = {
                "session_id": self.test_session_id,
                "content": follow_up_message
            }
            
            response = self.session.post(
                f"{self.base_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if "assistant_message" in data:
                    assistant_content = data["assistant_message"].get("content", "")
                    if "6" in assistant_content or "six" in assistant_content.lower():
                        self.log_test("Multi-turn Conversation", True, "Follow-up message handled correctly")
                        return True
                    else:
                        self.log_test("Multi-turn Conversation", False, f"Unexpected follow-up response: {assistant_content[:100]}...")
                        return False
                else:
                    self.log_test("Multi-turn Conversation", False, "Missing assistant message in response")
                    return False
            else:
                self.log_test("Multi-turn Conversation", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Multi-turn Conversation", False, f"Request error: {str(e)}")
            return False
    
    def test_invalid_session_id(self):
        """Test error handling for invalid session ID"""
        try:
            invalid_session_id = "invalid-session-id-12345"
            payload = {
                "session_id": invalid_session_id,
                "content": "Test message"
            }
            
            response = self.session.post(
                f"{self.base_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 404:
                self.log_test("Invalid Session Error Handling", True, "Correctly returned 404 for invalid session")
                return True
            else:
                self.log_test("Invalid Session Error Handling", False, f"Expected 404, got {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Invalid Session Error Handling", False, f"Request error: {str(e)}")
            return False
    
    def test_empty_message(self):
        """Test error handling for empty message"""
        if not self.test_session_id:
            self.log_test("Empty Message Handling", False, "No test session available")
            return False
        
        try:
            payload = {
                "session_id": self.test_session_id,
                "content": ""
            }
            
            response = self.session.post(
                f"{self.base_url}/chat",
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Either should handle gracefully (200) or return error (400/422)
            if response.status_code in [200, 400, 422]:
                self.log_test("Empty Message Handling", True, f"Handled empty message appropriately (HTTP {response.status_code})")
                return True
            else:
                self.log_test("Empty Message Handling", False, f"Unexpected status code: {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Empty Message Handling", False, f"Request error: {str(e)}")
            return False
    
    def test_delete_session(self):
        """Test DELETE /api/sessions/{session_id} - Delete session"""
        if not self.test_session_id:
            self.log_test("Delete Session", False, "No test session available")
            return False
        
        try:
            response = self.session.delete(f"{self.base_url}/sessions/{self.test_session_id}")
            
            if response.status_code == 200:
                data = response.json()
                if "message" in data:
                    self.log_test("Delete Session", True, "Session deleted successfully")
                    
                    # Verify session is actually deleted
                    verify_response = self.session.get(f"{self.base_url}/sessions")
                    if verify_response.status_code == 200:
                        sessions = verify_response.json()
                        session_exists = any(session.get("id") == self.test_session_id for session in sessions)
                        if not session_exists:
                            self.log_test("Session Deletion Verification", True, "Session successfully removed from database")
                        else:
                            self.log_test("Session Deletion Verification", False, "Session still exists after deletion")
                    
                    return True
                else:
                    self.log_test("Delete Session", False, "Unexpected response format", data)
                    return False
            else:
                self.log_test("Delete Session", False, f"HTTP {response.status_code}", response.text)
                return False
        except Exception as e:
            self.log_test("Delete Session", False, f"Request error: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print("=" * 60)
        print("GEMINI CHATBOT BACKEND API TESTING")
        print("=" * 60)
        print(f"Backend URL: {self.base_url}")
        print(f"Gemini API Key: {GEMINI_API_KEY[:20]}...")
        print("=" * 60)
        
        # Test sequence
        tests = [
            self.test_root_endpoint,
            self.test_create_session,
            self.test_list_sessions,
            self.test_send_chat_message,
            self.test_get_chat_history,
            self.test_multi_turn_conversation,
            self.test_invalid_session_id,
            self.test_empty_message,
            self.test_delete_session
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"❌ FAIL {test.__name__}: Unexpected error: {str(e)}")
                failed += 1
            
            # Small delay between tests
            time.sleep(0.5)
        
        print("=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"✅ Passed: {passed}")
        print(f"❌ Failed: {failed}")
        print(f"📊 Total: {passed + failed}")
        print(f"📈 Success Rate: {(passed/(passed+failed)*100):.1f}%" if (passed+failed) > 0 else "0%")
        print("=" * 60)
        
        return passed, failed, self.test_results

if __name__ == "__main__":
    tester = GeminiChatbotTester()
    passed, failed, results = tester.run_all_tests()
    
    # Save detailed results to file
    with open("/app/backend_test_results.json", "w") as f:
        json.dump({
            "summary": {"passed": passed, "failed": failed, "total": passed + failed},
            "results": results
        }, f, indent=2)
    
    print(f"\nDetailed results saved to: /app/backend_test_results.json")