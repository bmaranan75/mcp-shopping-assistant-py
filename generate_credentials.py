"""
Quick test script to verify OAuth installation and generate credentials.
"""

import secrets
import sys

def generate_secret_key():
    """Generate a secure secret key for session management."""
    return secrets.token_urlsafe(32)

def generate_api_key():
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)

def main():
    print("=" * 60)
    print("MCP Server OAuth Setup Helper")
    print("=" * 60)
    print()
    
    print("Generated Credentials:")
    print("-" * 60)
    print()
    
    # Generate secret key
    secret_key = generate_secret_key()
    print("SECRET_KEY (for session management):")
    print(f"  {secret_key}")
    print()
    
    # Generate API keys
    print("API_KEYS (for service authentication):")
    for i in range(3):
        api_key = generate_api_key()
        print(f"  Key {i+1}: {api_key}")
    print()
    
    print("-" * 60)
    print()
    print("Next Steps:")
    print("1. Copy .env.example to .env")
    print("2. Add the generated SECRET_KEY to your .env file")
    print("3. Add one or more API_KEYS to your .env file (comma-separated)")
    print("4. Get Google OAuth credentials from:")
    print("   https://console.cloud.google.com/apis/credentials")
    print("5. Add GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET to .env")
    print("6. Set OAUTH_ENABLED=true to enable authentication")
    print()
    print("For detailed setup instructions, see OAUTH_SETUP.md")
    print("=" * 60)

if __name__ == "__main__":
    main()
