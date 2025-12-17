import requests
import json

# Test the RAG agent with more complex questions
url = "http://127.0.0.1:8501/chat"

questions = [
    # Complex reasoning
    "If I have 3 apples and give away 2, then buy 5 more, how many do I have?",
    # Follow-up context test
    "Now if I eat one apple from that, how many remain?",
    # Explanation
    "Explain quantum entanglement in simple terms",
    # Creative writing
    "Write a short poem about coding",
    # Opinion/preference
    "What's better for beginners: Python or JavaScript?",
    # Multi-step reasoning
    "A train leaves NYC at 10am going 60mph. Another leaves Boston (200 miles away) at 11am going 80mph toward NYC. When do they meet?",
    # General knowledge
    "Who was the first person to walk on the moon and when?",
    # Context retention test
    "What was my first question about?"
]

session_id = None

for i, q in enumerate(questions):
    print(f"\n{'='*60}")
    print(f"Q{i+1}: {q}")
    print("="*60)
    try:
        payload = {"message": q}
        if session_id:
            payload["session_id"] = session_id
        response = requests.post(url, json=payload, timeout=120)
        answer = response.text
        print(f"ANSWER: {answer[:600]}{'...' if len(answer) > 600 else ''}")
    except Exception as e:
        print(f"ERROR: {e}")
