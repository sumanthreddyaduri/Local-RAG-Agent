from database import init_db, create_session, toggle_pin_session, get_all_sessions, delete_session
import time

def test_pinning():
    print("Testing Pinning Logic...")
    
    # Create sessions
    s1 = create_session("Session 1 (Old)")
    time.sleep(1)
    s2 = create_session("Session 2 (New)")
    
    # Verify initial order (Newest first)
    sessions = get_all_sessions(limit=10)
    # Filter to only our test sessions to avoid noise from existing DB
    my_sessions = [s for s in sessions if s['id'] in [s1, s2]]
    
    if len(my_sessions) >= 2:
        # Check relative order
        first = my_sessions[0]
        second = my_sessions[1]
        print(f"Initial: First={first['name']}, Second={second['name']}")
        # By default updated_at DESC, so New (s2) should be first
        if first['id'] == s2:
             print("Initial order correct (Time-based)")
        else:
             print("WARNING: Initial order incorrect")

    
    # Pin Session 1 (Old)
    print("Pinning Session 1...")
    toggle_pin_session(s1, True)
    
    # Verify new order (Pinned first)
    sessions = get_all_sessions(limit=100)
    my_sessions = [s for s in sessions if s['id'] in [s1, s2]]
    
    if len(my_sessions) >= 2:
        first = my_sessions[0]
        second = my_sessions[1]
        print(f"After Pin: First={first['name']} (Pinned={first['is_pinned']}), Second={second['name']}")
        
        if first['id'] == s1:
            print("Pinned order correct (Pin-based)")
        else:
            print("FAILED: Pinned session is not first")
    
    # Cleanup
    delete_session(s1)
    delete_session(s2)
    print("Cleanup done.")

if __name__ == "__main__":
    test_pinning()
