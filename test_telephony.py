#!/usr/bin/env python3
"""
Test script for the /telephony endpoint
"""
import requests
import json

# Test endpoint
url = "http://localhost:8001/telephony"

# Test data
test_data = {
    "call_id": "12345",
    "from": "+1234567890",
    "to": "+0987654321",
    "status": "ringing",
    "timestamp": "2025-11-20T10:30:00Z"
}

# Custom headers
headers = {
    "Content-Type": "application/json",
    "X-Custom-Header": "test-value",
    "User-Agent": "TelephonyWebhook/1.0"
}

print("Testing POST /telephony endpoint...")
print(f"URL: {url}")
print(f"\nRequest Headers:")
print(json.dumps(headers, indent=2))
print(f"\nRequest Body:")
print(json.dumps(test_data, indent=2))
print("\n" + "=" * 70)

try:
    response = requests.post(url, json=test_data, headers=headers)
    print(f"\nResponse Status: {response.status_code}")
    print(f"Response Body:")
    print(json.dumps(response.json(), indent=2))
    print("=" * 70)
    print("\n✅ Test completed successfully!")
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("=" * 70)
