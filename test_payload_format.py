#!/usr/bin/env python3
"""
Test to verify the exact payload format being sent to LangGraph supervisor
"""

import httpx
import json
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("API_KEYS", "").split(",")[0]
BASE_URL = "http://localhost:8001"

print("=" * 70)
print("Expected LangGraph Format:")
print("=" * 70)
print(json.dumps({
    "assistant_id": "supervisor",
    "input": {
        "messages": [
            {
                "role": "user",
                "content": "Find current grocery deals for apples."
            }
        ],
        "userId": "user-123",           # From OAuth token
        "conversationId": "conv-456"    # From ChatGPT request
    },
    "config": {
        "configurable": {
            "thread_id": "conv-456"     # For conversation persistence
        }
    }
}, indent=2))
print()

print("=" * 70)
print("Testing with API Key (no userId):")
print("=" * 70)

response = httpx.post(
    f"{BASE_URL}/invoke",
    headers={
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    },
    json={
        "assistant_id": "supervisor",
        "prompt": "Find current grocery deals for apples.",
        "conversationId": "conv-456",
        "thread_id": "conv-456"
    },
    timeout=30.0
)

print(f"Status: {response.status_code}")
if response.status_code == 200:
    print("✓ Request successful")
    result = response.json()
    print(f"Run ID: {result.get('run_id')}")
    print(f"Thread ID: {result.get('thread_id')}")
else:
    print(f"✗ Failed: {response.text}")

print()
print("=" * 70)
print("Check server logs for:")
print("  DEBUG: Payload to supervisor - userId: ..., conversationId: ..., thread_id: ...")
print("  DEBUG: Calling http://localhost:2024/runs/stream with payload: {...}")
print("=" * 70)
