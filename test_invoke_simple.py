#!/usr/bin/env python3
"""Simple test of the /invoke endpoint"""
import requests
import json

# Test without auth first to see error
print("Testing /invoke endpoint...")
response = requests.post(
    "http://localhost:8001/invoke",
    json={
        "prompt": "Hello",
        "assistant_id": "supervisor"
    },
    headers={"Content-Type": "application/json"}
)

print(f"Status: {response.status_code}")
print(f"Response: {response.text}")

# If we need auth, set OAUTH_ENABLED=false in .env or disable auth temporarily
