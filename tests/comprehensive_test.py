"""
Comprehensive System Test Suite for Local RAG Agent
Tests all API endpoints, error handling, and edge cases
"""

import requests
import json
import time
import os
import sys

BASE_URL = "http://127.0.0.1:8501"
PASSED = 0
FAILED = 0
WARNINGS = 0

def log_result(test_name, success, message="", warning=False):
    global PASSED, FAILED, WARNINGS
    if warning:
        WARNINGS += 1
        print(f"[WARN] {test_name}")
        if message:
            print(f"       {message}")
    elif success:
        PASSED += 1
        print(f"[PASS] {test_name}")
    else:
        FAILED += 1
        print(f"[FAIL] {test_name}")
        if message:
            print(f"       {message}")

def test_server_running():
    """Test 1: Server is running and responds"""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        return r.status_code == 200
    except:
        return False

def test_health_endpoint():
    """Test 2: Health endpoint returns valid JSON"""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        data = r.json()
        return "status" in data and "ollama" in data
    except Exception as e:
        return False

def test_stats_endpoint():
    """Test 3: Stats endpoint works"""
    try:
        r = requests.get(f"{BASE_URL}/api/stats", timeout=5)
        data = r.json()
        return "total_documents" in data or "indexed_files" in data
    except:
        return False

def test_settings_get():
    """Test 4: GET settings"""
    try:
        r = requests.get(f"{BASE_URL}/api/settings", timeout=5)
        data = r.json()
        return "model" in data and "ollama_host" in data
    except:
        return False

def test_settings_update():
    """Test 5: POST settings update"""
    try:
        r = requests.post(f"{BASE_URL}/api/settings",
                          json={"show_sources": True},
                          timeout=5)
        return r.status_code == 200
    except:
        return False

# ===== SESSION MANAGEMENT TESTS =====

def test_list_sessions():
    """Test 6: List sessions"""
    try:
        r = requests.get(f"{BASE_URL}/api/sessions", timeout=5)
        data = r.json()
        return "sessions" in data
    except:
        return False

def test_create_session():
    """Test 7: Create new session"""
    try:
        r = requests.post(f"{BASE_URL}/api/sessions",
                          json={"name": "Test Session"},
                          headers={"Content-Type": "application/json"},
                          timeout=5)
        data = r.json()
        return "session_id" in data
    except:
        return False

def test_get_session():
    """Test 8: Get session by ID"""
    try:
        # First create a session
        r = requests.post(f"{BASE_URL}/api/sessions",
                          json={},
                          headers={"Content-Type": "application/json"},
                          timeout=5)
        session_id = r.json().get("session_id")
        
        # Then get it
        r2 = requests.get(f"{BASE_URL}/api/sessions/{session_id}", timeout=5)
        return r2.status_code == 200
    except:
        return False

def test_delete_session():
    """Test 9: Delete session"""
    try:
        # Create then delete
        r = requests.post(f"{BASE_URL}/api/sessions",
                          json={},
                          headers={"Content-Type": "application/json"},
                          timeout=5)
        session_id = r.json().get("session_id")
        
        r2 = requests.delete(f"{BASE_URL}/api/sessions/{session_id}", timeout=5)
        return r2.status_code == 200
    except:
        return False

def test_session_export():
    """Test 10: Export session"""
    try:
        # Get existing sessions
        r = requests.get(f"{BASE_URL}/api/sessions", timeout=5)
        sessions = r.json().get("sessions", [])
        
        if not sessions:
            return None  # Skip if no sessions
        
        session_id = sessions[0]["id"]
        r2 = requests.get(f"{BASE_URL}/api/sessions/{session_id}/export?format=txt", timeout=5)
        return r2.status_code == 200
    except:
        return False

# ===== BROWSER BRIDGE TESTS =====

def test_browser_sync():
    """Test 11: Browser sync endpoint"""
    try:
        r = requests.post(f"{BASE_URL}/api/browser/sync",
                          json={
                              "url": "https://example.com",
                              "title": "Test Page",
                              "content": "This is test content for browser sync."
                          },
                          timeout=5)
        data = r.json()
        return data.get("status") == "synced"
    except:
        return False

def test_browser_context():
    """Test 12: Get browser context"""
    try:
        r = requests.get(f"{BASE_URL}/api/browser/context", timeout=5)
        data = r.json()
        return "url" in data and "content" in data
    except:
        return False

def test_browser_clear():
    """Test 13: Clear browser context"""
    try:
        r = requests.post(f"{BASE_URL}/api/browser/clear", timeout=5)
        data = r.json()
        return data.get("status") == "cleared"
    except:
        return False

# ===== CHAT TESTS =====

def test_chat_empty_message():
    """Test 14: Chat with empty message (should fail)"""
    try:
        r = requests.post(f"{BASE_URL}/chat",
                          json={"message": ""},
                          timeout=10)
        return r.status_code == 400
    except:
        return False

def test_chat_valid_message():
    """Test 15: Chat with valid message"""
    try:
        r = requests.post(f"{BASE_URL}/chat",
                          json={"message": "Hello, what is 2+2?"},
                          timeout=60)  # LLM can be slow
        return r.status_code == 200
    except Exception as e:
        return False

def test_chat_with_session_id():
    """Test 16: Chat with explicit session ID"""
    try:
        # Create session first
        r1 = requests.post(f"{BASE_URL}/api/sessions",
                           json={},
                           headers={"Content-Type": "application/json"},
                           timeout=5)
        session_id = r1.json().get("session_id")
        
        # Chat with that session
        r2 = requests.post(f"{BASE_URL}/chat",
                           json={"message": "Test message", "session_id": session_id},
                           timeout=60)
        return r2.status_code == 200
    except:
        return False

# ===== FILE MANAGEMENT TESTS =====

def test_list_files():
    """Test 17: List files endpoint"""
    try:
        r = requests.get(f"{BASE_URL}/api/files", timeout=5)
        return r.status_code == 200
    except:
        return False

def test_index_stats():
    """Test 18: Index stats endpoint"""
    try:
        r = requests.get(f"{BASE_URL}/api/index/stats", timeout=5)
        return r.status_code == 200
    except:
        return False

# ===== EDGE CASES & ERROR HANDLING =====

def test_invalid_session_id():
    """Test 19: Get non-existent session"""
    try:
        r = requests.get(f"{BASE_URL}/api/sessions/999999", timeout=5)
        return r.status_code == 404 or "error" in r.json()
    except:
        return False

def test_invalid_endpoint():
    """Test 20: Non-existent endpoint returns 404"""
    try:
        r = requests.get(f"{BASE_URL}/api/nonexistent", timeout=5)
        return r.status_code == 404
    except:
        return False

def test_malformed_json():
    """Test 21: Malformed JSON handling"""
    try:
        r = requests.post(f"{BASE_URL}/chat",
                          data="not valid json",
                          headers={"Content-Type": "application/json"},
                          timeout=5)
        return r.status_code in [400, 415, 500]
    except:
        return False

def test_large_message():
    """Test 22: Large message handling"""
    try:
        large_msg = "x" * 10000  # 10KB message
        r = requests.post(f"{BASE_URL}/chat",
                          json={"message": large_msg},
                          timeout=60)
        return r.status_code in [200, 400]  # Either works or gracefully fails
    except:
        return False

def test_special_characters():
    """Test 23: Special characters in message"""
    try:
        r = requests.post(f"{BASE_URL}/chat",
                          json={"message": "Test <script>alert('xss')</script> message"},
                          timeout=60)
        return r.status_code == 200
    except:
        return False

def test_unicode_message():
    """Test 24: Unicode/emoji in message"""
    try:
        r = requests.post(f"{BASE_URL}/chat",
                          json={"message": "Hello 你好 مرحبا 🌍🚀"},
                          timeout=60)
        return r.status_code == 200
    except:
        return False

def test_concurrent_requests():
    """Test 25: Multiple concurrent requests"""
    import concurrent.futures
    
    def make_request():
        try:
            r = requests.get(f"{BASE_URL}/health", timeout=5)
            return r.status_code == 200
        except:
            return False
    
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request) for _ in range(10)]
            results = [f.result() for f in futures]
        return all(results)
    except:
        return False

def test_set_mode():
    """Test 26: Set mode endpoint"""
    try:
        r = requests.post(f"{BASE_URL}/set_mode",
                          json={"mode": "browser"},
                          timeout=5)
        return r.status_code == 200
    except:
        return False

# ===== PERFORMANCE TESTS =====

def test_response_time_health():
    """Test 27: Health endpoint response time < 500ms"""
    try:
        start = time.time()
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        elapsed = (time.time() - start) * 1000
        return elapsed < 500
    except:
        return False

def test_response_time_sessions():
    """Test 28: Sessions endpoint response time < 1s"""
    try:
        start = time.time()
        r = requests.get(f"{BASE_URL}/api/sessions", timeout=5)
        elapsed = (time.time() - start) * 1000
        return elapsed < 1000
    except:
        return False

# ===== MAIN TEST RUNNER =====

def run_all_tests():
    global PASSED, FAILED, WARNINGS
    
    print("\n" + "="*60)
    print("🧪 LOCAL RAG AGENT - COMPREHENSIVE SYSTEM TEST")
    print("="*60 + "\n")
    
    # Check server first
    if not test_server_running():
        print("❌ CRITICAL: Server not running at", BASE_URL)
        print("   Please start: python app.py")
        sys.exit(1)
    
    print("🟢 Server is running\n")
    print("-"*40)
    print("HEALTH & STATUS TESTS")
    print("-"*40)
    
    log_result("Health endpoint", test_health_endpoint())
    log_result("Stats endpoint", test_stats_endpoint())
    log_result("Settings GET", test_settings_get())
    log_result("Settings UPDATE", test_settings_update())
    
    print("\n" + "-"*40)
    print("SESSION MANAGEMENT TESTS")
    print("-"*40)
    
    log_result("List sessions", test_list_sessions())
    log_result("Create session", test_create_session())
    log_result("Get session by ID", test_get_session())
    log_result("Delete session", test_delete_session())
    
    result = test_session_export()
    if result is None:
        log_result("Export session", False, "Skipped - no sessions", warning=True)
    else:
        log_result("Export session", result)
    
    print("\n" + "-"*40)
    print("BROWSER BRIDGE TESTS")
    print("-"*40)
    
    log_result("Browser sync", test_browser_sync())
    log_result("Get browser context", test_browser_context())
    log_result("Clear browser context", test_browser_clear())
    
    print("\n" + "-"*40)
    print("CHAT TESTS")
    print("-"*40)
    
    log_result("Empty message (should fail)", test_chat_empty_message())
    log_result("Valid chat message", test_chat_valid_message())
    log_result("Chat with session ID", test_chat_with_session_id())
    
    print("\n" + "-"*40)
    print("FILE MANAGEMENT TESTS")
    print("-"*40)
    
    log_result("List files", test_list_files())
    log_result("Index stats", test_index_stats())
    
    print("\n" + "-"*40)
    print("ERROR HANDLING & EDGE CASES")
    print("-"*40)
    
    log_result("Invalid session ID", test_invalid_session_id())
    log_result("Invalid endpoint (404)", test_invalid_endpoint())
    log_result("Malformed JSON", test_malformed_json())
    log_result("Large message (10KB)", test_large_message())
    log_result("Special characters/XSS", test_special_characters())
    log_result("Unicode/emoji", test_unicode_message())
    log_result("Set mode", test_set_mode())
    
    print("\n" + "-"*40)
    print("CONCURRENCY & PERFORMANCE")
    print("-"*40)
    
    log_result("10 concurrent requests", test_concurrent_requests())
    log_result("Health response < 500ms", test_response_time_health())
    log_result("Sessions response < 1s", test_response_time_sessions())
    
    # Summary
    total = PASSED + FAILED
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"✅ Passed:   {PASSED}/{total}")
    print(f"❌ Failed:   {FAILED}/{total}")
    print(f"⚠️  Warnings: {WARNINGS}")
    
    if FAILED == 0:
        print("\n🎉 ALL TESTS PASSED! System is healthy.")
    elif FAILED <= 3:
        print(f"\n⚠️  {FAILED} test(s) failed. Minor issues detected.")
    else:
        print(f"\n🚨 {FAILED} test(s) failed. System needs attention!")
    
    print("="*60 + "\n")
    
    return FAILED == 0

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
