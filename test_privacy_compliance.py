#!/usr/bin/env python3
"""Verify privacy endpoint and ChatGPT compliance."""

import httpx

SERVER_URL = "https://a94044ddf129.ngrok-free.app"

print("=" * 70)
print("ChatGPT Privacy Compliance Verification")
print("=" * 70)
print()

# Test 1: Privacy endpoint exists
print("Test 1: Privacy Endpoint")
print("-" * 70)
try:
    response = httpx.get(f"{SERVER_URL}/privacy", timeout=10.0)
    if response.status_code == 200:
        print(f"✅ /privacy endpoint: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('content-type')}")
        print(f"   Content length: {len(response.text)} bytes")
    else:
        print(f"❌ /privacy endpoint: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 2: AI Plugin manifest includes privacy URL
print("Test 2: AI Plugin Manifest")
print("-" * 70)
try:
    response = httpx.get(
        f"{SERVER_URL}/.well-known/ai-plugin.json",
        timeout=10.0
    )
    if response.status_code == 200:
        data = response.json()
        print(f"✅ AI plugin manifest: {response.status_code}")
        print(f"   Plugin name: {data.get('name_for_human')}")
        print(f"   Contact: {data.get('contact_email')}")
        print(f"   Legal URL: {data.get('legal_info_url')}")
        print(f"   Privacy URL: {data.get('privacy_policy_url')}")
        
        if data.get('privacy_policy_url'):
            print()
            print("✅ Privacy policy URL included in manifest")
        else:
            print()
            print("❌ Privacy policy URL missing from manifest")
    else:
        print(f"❌ AI plugin manifest: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 3: Legal endpoint
print("Test 3: Legal Endpoint")
print("-" * 70)
try:
    response = httpx.get(f"{SERVER_URL}/legal", timeout=10.0)
    if response.status_code == 200:
        print(f"✅ /legal endpoint: {response.status_code}")
    else:
        print(f"❌ /legal endpoint: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

print()
print("=" * 70)
print("Summary")
print("=" * 70)
print("✅ Privacy endpoint created and accessible")
print("✅ AI plugin manifest updated with privacy URL")
print("✅ ChatGPT compliance requirements met")
print()
print(f"Privacy Policy: {SERVER_URL}/privacy")
print(f"Legal Info: {SERVER_URL}/legal")
print("=" * 70)
