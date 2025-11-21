"""
ChatGPT Enterprise Server - FastAPI Stateless Wrapper

This server provides a stateless HTTP API for ChatGPT Enterprise Apps & Connectors.
Unlike the FastMCP streamable-http transport which requires session management,
this implementation uses FastAPI to provide simple, stateless REST endpoints.

Key features:
- Stateless HTTP requests (no session management)
- JSON-RPC 2.0 compatible /mcp endpoint
- Direct REST API endpoints for each tool
- Works seamlessly with ChatGPT Actions
- Simple deployment and testing

Usage:
    python -m src.agent_mcp.chatgpt_fastapi_server
    
    Or use the startup script:
    ./start_chatgpt_mcp.sh
"""

import httpx
import json
import os
import secrets
import time
from typing import Any, Dict, Optional
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import uvicorn

# Load environment variables
load_dotenv()

# Configuration
LANGGRAPH_BASE_URL = os.getenv("LANGGRAPH_BASE_URL", "http://localhost:2024")
CHATGPT_MCP_PORT = int(os.getenv("CHATGPT_MCP_PORT", "8001"))
API_KEYS = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []

# Server URL configuration
SERVER_URL = os.getenv("SERVER_URL", f"http://localhost:{CHATGPT_MCP_PORT}")

# OAuth 2.0 Configuration
OAUTH_ENABLED = os.getenv("CHATGPT_OAUTH_ENABLED", "false").lower() == "true"
OAUTH_CLIENT_ID = os.getenv("CHATGPT_OAUTH_CLIENT_ID", "")
OAUTH_CLIENT_SECRET = os.getenv("CHATGPT_OAUTH_CLIENT_SECRET", "")
OAUTH_TOKEN_EXPIRY = int(os.getenv("CHATGPT_OAUTH_TOKEN_EXPIRY", "3600"))
OAUTH_ISSUER = os.getenv("OAUTH_ISSUER", SERVER_URL)
OAUTH_TOKEN_ENDPOINT = os.getenv("OAUTH_TOKEN_ENDPOINT", f"{SERVER_URL}/oauth/token")
OAUTH_AUTHORIZE_URL = os.getenv(
    "OAUTH_AUTHORIZE_URL",
    f"{SERVER_URL}/oauth/authorize"
)

# Okta Configuration (for external token validation)
OKTA_DOMAIN = os.getenv("OKTA_DOMAIN", "")
OKTA_AUTHORIZE_URL = os.getenv(
    "OKTA_AUTHORIZE_URL",
    f"https://{OKTA_DOMAIN}/oauth2/default/v1/authorize" if OKTA_DOMAIN else ""
)
OKTA_INTROSPECT_URL = os.getenv("OKTA_INTROSPECT_URL", "")

# In-memory token storage (use Redis in production)
active_tokens: Dict[str, Dict[str, Any]] = {}

# Initialize FastAPI
app = FastAPI(
    title="LangGraph Agent MCP Server",
    description="ChatGPT Enterprise compatible MCP server for LangGraph agents",
    version="1.0.0"
)

# OAuth 2.0 Models
class TokenRequest(BaseModel):
    grant_type: str
    client_id: str
    client_secret: str
    scope: Optional[str] = "mcp:access"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    expires_in: int
    scope: str


# Security
security = HTTPBearer(auto_error=False)


async def validate_okta_token(token: str) -> Optional[Dict[str, Any]]:
    """Validate token with Okta introspection endpoint.
    
    Returns:
        Token info dict if valid, None if invalid
    """
    if not OKTA_INTROSPECT_URL:
        print("⚠️  Okta introspection URL not configured")
        return None
    
    try:
        print(f"🔍 Validating token with Okta: {OKTA_INTROSPECT_URL}")
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                OKTA_INTROSPECT_URL,
                auth=(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET),
                data={"token": token, "token_type_hint": "access_token"}
            )
            
            print(f"Okta response status: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"Okta response: {json.dumps(data, indent=2)}")
                
                is_active = data.get("active", False)
                if is_active:
                    print("✓ Okta token is active and valid")
                    return data
                else:
                    print("✗ Okta token is inactive or invalid")
                    return None
            else:
                print(f"✗ Okta introspection failed: {response.status_code}")
                print(f"Response: {response.text}")
                return None
    except Exception as e:
        print(f"✗ Error validating token with Okta: {e}")
        return None


async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify OAuth token or API key."""
    print("\n" + "=" * 80)
    print("AUTHENTICATION CHECK")
    print("=" * 80)
    print(f"OAuth Enabled: {OAUTH_ENABLED}")
    print(f"Credentials Provided: {credentials is not None}")
    
    if not OAUTH_ENABLED:
        print("✓ OAuth disabled, allowing request")
        print("=" * 80 + "\n")
        return True
    
    if not credentials:
        print("✗ No credentials provided (missing Authorization header)")
        print(f"Active tokens in memory: {len(active_tokens)}")
        print(f"API keys configured: {len(API_KEYS)}")
        print("=" * 80 + "\n")
        # Build re-authentication URL
        reauth_url = (
            f"{OKTA_AUTHORIZE_URL or OAUTH_AUTHORIZE_URL}?"
            f"client_id={OAUTH_CLIENT_ID}&"
            f"response_type=code&"
            f"scope=openid%20profile%20email&"
            f"redirect_uri={SERVER_URL}/oauth/callback"
        )
        # Return OAuth-compliant error with re-auth link
        raise HTTPException(
            status_code=401,
            detail=(
                f"invalid_token: Authentication required. "
                f"Please authenticate here: {reauth_url}"
            ),
            headers={
                "WWW-Authenticate": (
                    'Bearer realm="ChatGPT", '
                    'error="invalid_token", '
                    'error_description="Authentication required"'
                ),
                "X-Reauth-URL": reauth_url
            }
        )
    
    token = credentials.credentials
    print(f"Token received: {token[:20]}..." if len(token) > 20 else f"Token: {token}")
    print(f"Token length: {len(token)}")
    
    # Check if it's a valid OAuth token
    print(f"\nChecking against {len(active_tokens)} active tokens...")
    if token in active_tokens:
        token_data = active_tokens[token]
        expires_at = token_data["expires_at"]
        current_time = time.time()
        time_remaining = expires_at - current_time
        
        print(f"✓ Token found in active tokens")
        print(f"  Expires at: {expires_at}")
        print(f"  Current time: {current_time}")
        print(f"  Time remaining: {time_remaining:.0f} seconds")
        
        if token_data["expires_at"] > time.time():
            print("✓ Token is valid and not expired")
            print("=" * 80 + "\n")
            return token_data
        else:
            # Token expired - return OAuth-compliant error for re-auth
            del active_tokens[token]
            print("✗ Token expired, removing from active tokens")
            print("=" * 80 + "\n")
            # Build re-authentication URL
            reauth_url = (
                f"{OKTA_AUTHORIZE_URL or OAUTH_AUTHORIZE_URL}?"
                f"client_id={OAUTH_CLIENT_ID}&"
                f"response_type=code&"
                f"scope=openid%20profile%20email&"
                f"redirect_uri={SERVER_URL}/oauth/callback"
            )
            raise HTTPException(
                status_code=401,
                detail=(
                    f"invalid_token: The access token expired. "
                    f"Please re-authenticate: {reauth_url}"
                ),
                headers={
                    "WWW-Authenticate": (
                        'Bearer realm="ChatGPT", '
                        'error="invalid_token", '
                        'error_description="The access token expired"'
                    ),
                    "X-Reauth-URL": reauth_url
                }
            )
    
    # Check if it's a valid API key
    print(f"\nToken not in active tokens, checking API keys...")
    print(f"Configured API keys: {len(API_KEYS)}")
    if API_KEYS:
        for i, key in enumerate(API_KEYS):
            print(f"  API Key {i+1}: {key[:10]}..." if len(key) > 10 else f"  API Key {i+1}: {key}")
    
    if API_KEYS and token in API_KEYS:
        print("✓ Valid API key")
        print("=" * 80 + "\n")
        return {"type": "api_key", "valid": True}
    
    # Try validating with Okta (external OAuth provider)
    print(f"\nToken not in API keys, trying Okta validation...")
    print(f"Okta introspection URL configured: {bool(OKTA_INTROSPECT_URL)}")
    
    if OKTA_INTROSPECT_URL:
        token_info = await validate_okta_token(token)
        if token_info:
            print("✓ Token validated by Okta")
            print("=" * 80 + "\n")
            return {
                "type": "okta_token",
                "valid": True,
                "token": token,
                "token_info": token_info
            }
    
    print("✗ Invalid token - not found in active tokens, API keys, or Okta")
    print(f"Token to validate: {token[:30]}...")
    print(f"Active tokens: {list(active_tokens.keys())[:3]}..." if active_tokens else "Active tokens: []")
    print("=" * 80 + "\n")
    # Build re-authentication URL
    reauth_url = (
        f"{OKTA_AUTHORIZE_URL or OAUTH_AUTHORIZE_URL}?"
        f"client_id={OAUTH_CLIENT_ID}&"
        f"response_type=code&"
        f"scope=openid%20profile%20email&"
        f"redirect_uri={SERVER_URL}/oauth/callback"
    )
    # Return OAuth-compliant error with re-auth link
    raise HTTPException(
        status_code=401,
        detail=(
            f"invalid_token: The access token is invalid. "
            f"Please re-authenticate: {reauth_url}"
        ),
        headers={
            "WWW-Authenticate": (
                'Bearer realm="ChatGPT", '
                'error="invalid_token", '
                'error_description="The access token is invalid"'
            ),
            "X-Reauth-URL": reauth_url
        }
    )


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Request Logging Middleware
# ============================================================================

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests with full details."""
    print("\n" + "🔵" * 40)
    print("INCOMING HTTP REQUEST")
    print("🔵" * 40)
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Path: {request.url.path}")
    print(f"Client: {request.client.host if request.client else 'Unknown'}:{request.client.port if request.client else 'Unknown'}")
    
    print("\nHeaders:")
    for header, value in request.headers.items():
        print(f"  {header}: {value}")
    
    # For POST/PUT requests, try to read body
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.body()
            if body:
                print(f"\nBody ({len(body)} bytes):")
                try:
                    body_str = body.decode('utf-8')
                    print(body_str)
                    # Re-create request with body for downstream processing
                    async def receive():
                        return {"type": "http.request", "body": body}
                    request._receive = receive
                except Exception as e:
                    print(f"[Could not decode body: {e}]")
            else:
                print("\nBody: (empty)")
        except Exception as e:
            print(f"\n[Error reading body: {e}]")
    
    print("🔵" * 40 + "\n")
    
    # Process the request
    response = await call_next(request)
    
    # Log response status
    print("\n" + "🟢" * 40)
    print("HTTP RESPONSE")
    print("🟢" * 40)
    print(f"Status: {response.status_code}")
    print("🟢" * 40 + "\n")
    
    return response


# ============================================================================
# Request/Response Models
# ============================================================================

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str
    method: str
    params: Dict[str, Any] = Field(default_factory=dict)


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: int | str
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None


class ToolCallParams(BaseModel):
    name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Helper Functions
# ============================================================================

async def invoke_langgraph_agent(
    prompt: str,
    assistant_id: str = "supervisor",
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> dict:
    """
    Invoke the LangGraph agent with a prompt.
    
    Args:
        prompt: The user prompt/query
        assistant_id: The assistant/agent ID (default: "supervisor")
        thread_id: Optional thread ID for conversation continuity
        user_id: Optional user ID from authentication
        conversation_id: Optional conversation ID from ChatGPT
    
    Returns:
        Agent response with output and metadata
    """
    try:
        # Generate thread_id if not provided
        if not thread_id:
            thread_id = f"thread-{secrets.token_urlsafe(16)}"
            print(f"DEBUG: Generated thread_id: {thread_id}")
        
        # Generate conversation_id if not provided
        if not conversation_id:
            conversation_id = f"conv-{secrets.token_urlsafe(16)}"
            print(f"DEBUG: Generated conversation_id: {conversation_id}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Build input with messages
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
            }
            
            # Add userId to input if available
            if user_id:
                payload["input"]["userId"] = user_id
            
            # Add conversationId to input
            payload["input"]["conversationId"] = conversation_id
            
            # Add thread_id to config for conversation persistence
            payload["config"] = {
                "configurable": {
                    "thread_id": thread_id
                }
            }
            
            print(
                f"DEBUG: Payload to supervisor - "
                f"userId: {user_id}, "
                f"conversationId: {conversation_id}, "
                f"thread_id: {thread_id}"
            )
            
            # Use /runs/stream endpoint which returns SSE format
            stream_url = f"{LANGGRAPH_BASE_URL}/runs/stream"
            print(f"DEBUG: Calling {stream_url}")
            
            async with client.stream(
                "POST",
                stream_url,
                json=payload
            ) as response:
                print(f"DEBUG: Response status: {response.status_code}")
                
                # Check for error before parsing
                if response.status_code >= 400:
                    error_text = b""
                    async for chunk in response.aiter_bytes():
                        error_text += chunk
                    print(
                        f"ERROR: LangGraph returned "
                        f"{response.status_code}"
                    )
                    print(f"ERROR: Response: {error_text.decode()}")
                    raise httpx.HTTPStatusError(
                        f"LangGraph error: {response.status_code}",
                        request=response.request,
                        response=response
                    )
                
                response.raise_for_status()
                
                # Parse Server-Sent Events (SSE) format
                run_id = None
                final_messages = []
                all_message_snapshots = []  # Track all snapshots
                current_event = None
                current_data = []
                
                async for line in response.aiter_lines():
                    line = line.strip()
                    
                    if line.startswith("event:"):
                        # Save previous event data if exists
                        if current_event and current_data:
                            data_str = "\n".join(current_data)
                            try:
                                data_obj = json.loads(data_str)
                                if current_event == "metadata" and "run_id" in data_obj:
                                    run_id = data_obj["run_id"]
                                elif current_event == "values" and "messages" in data_obj:
                                    # Keep ALL values events, last one wins
                                    final_messages = data_obj["messages"]
                                    all_message_snapshots.append(
                                        data_obj["messages"]
                                    )
                                    print(f"DEBUG: Captured values event with "
                                          f"{len(final_messages)} messages")
                            except json.JSONDecodeError:
                                pass
                        
                        # Start new event
                        current_event = line.split(":", 1)[1].strip()
                        current_data = []
                    
                    elif line.startswith("data:"):
                        # Accumulate data lines
                        data_content = line.split(":", 1)[1].strip()
                        current_data.append(data_content)
                    
                    elif line == "":
                        # Empty line marks end of event
                        if current_event and current_data:
                            data_str = "\n".join(current_data)
                            try:
                                data_obj = json.loads(data_str)
                                if current_event == "metadata" and "run_id" in data_obj:
                                    run_id = data_obj["run_id"]
                                elif current_event == "values" and "messages" in data_obj:
                                    # Keep ALL values events, last one wins
                                    final_messages = data_obj["messages"]
                                    all_message_snapshots.append(
                                        data_obj["messages"]
                                    )
                                    print(f"DEBUG: Captured values event with "
                                          f"{len(final_messages)} messages")
                            except json.JSONDecodeError:
                                pass
                        current_event = None
                        current_data = []
                
                print(f"DEBUG: Total value snapshots received: "
                      f"{len(all_message_snapshots)}")
                
                # Debug: Print final messages structure
                print(f"DEBUG: Received {len(final_messages)} messages")
                if final_messages:
                    messages_json = json.dumps(
                        final_messages[:3], indent=2
                    )  # First 3 for brevity
                    print(f"DEBUG: First messages: {messages_json}")
                
                # Extract the final assistant response
                # SKIP ephemeral progress messages, return substantial content only
                output_text = None
                
                for msg in reversed(final_messages):
                    # Skip ephemeral progress messages entirely
                    if msg.get("progress", {}).get("ephemeral"):
                        print(f"DEBUG: Skipping ephemeral progress message")
                        continue
                    
                    print(f"DEBUG: Checking message: {msg.get('type')} / "
                          f"{msg.get('role')}")
                    
                    # Try different message structures
                    is_assistant = (
                        msg.get("role") == "assistant" or
                        msg.get("type") == "ai" or
                        msg.get("type") == "AIMessage"
                    )
                    
                    if is_assistant:
                        # Check for content in nested message object first
                        content = None
                        if "message" in msg and isinstance(
                            msg["message"], dict
                        ):
                            content = msg["message"].get("content", "")
                        elif "content" in msg:
                            content = msg["content"]
                        
                        # Skip empty content or JSON objects
                        if content and not str(content).startswith("{"):
                            output_text = content
                            print(f"DEBUG: Found substantial content from "
                                  f"{msg.get('agent', 'unknown')}: "
                                  f"{str(content)[:100]}")
                            break
                
                # Final fallback only if no substantial content found
                if not output_text:
                    output_text = "Agent is processing your request. Please try again in a moment."
                    print("DEBUG: No substantial content found, using fallback message")
                
                # Return MCP-compliant response format
                # The messages should be in the content field per MCP spec
                response = {
                    "content": [
                        {
                            "type": "text",
                            "text": str(output_text)
                        }
                    ],
                    "isError": False
                }
                
                print(f"DEBUG: Returning response with {len(str(output_text))} chars")
                print(f"DEBUG: Response: {json.dumps(response)[:300]}")
                
                return response
            
    except httpx.HTTPError as e:
        import traceback
        error_detail = f"HTTP error invoking agent: {str(e)}"
        print(f"ERROR: {error_detail}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": error_detail
                }
            ],
            "isError": True
        }
    except Exception as e:
        import traceback
        error_detail = f"Error invoking agent: {str(e)}"
        print(f"ERROR: {error_detail}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return {
            "content": [
                {
                    "type": "text",
                    "text": error_detail
                }
            ],
            "isError": True
        }


async def stream_langgraph_agent(
    prompt: str,
    assistant_id: str = "supervisor",
    thread_id: Optional[str] = None,
    user_id: Optional[str] = None,
    conversation_id: Optional[str] = None
) -> dict:
    """Stream responses from the LangGraph agent."""
    try:
        # Generate thread_id if not provided
        if not thread_id:
            thread_id = f"thread-{secrets.token_urlsafe(16)}"
            print(f"DEBUG: Generated thread_id: {thread_id}")
        
        # Generate conversation_id if not provided
        if not conversation_id:
            conversation_id = f"conv-{secrets.token_urlsafe(16)}"
            print(f"DEBUG: Generated conversation_id: {conversation_id}")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Build input with messages
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {
                            "type": "human",
                            "content": prompt
                        }
                    ]
                },
                "stream_mode": ["messages"]
            }
            
            # Add userId to input if available
            if user_id:
                payload["input"]["userId"] = user_id
            
            # Add conversationId to input
            payload["input"]["conversationId"] = conversation_id
            
            # Add thread_id to config for conversation persistence
            payload["config"] = {
                "configurable": {
                    "thread_id": thread_id
                }
            }
            
            print(
                f"DEBUG: Stream payload - "
                f"userId: {user_id}, "
                f"conversationId: {conversation_id}, "
                f"thread_id: {thread_id}"
            )
            
            async with client.stream(
                "POST",
                f"{LANGGRAPH_BASE_URL}/runs/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                chunks = []
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                
                return {
                    "output": "".join(chunks),
                    "chunks_received": len(chunks),
                    "status": "success"
                }
                
    except httpx.HTTPError as e:
        import traceback
        error_detail = f"HTTP error streaming from agent: {str(e)}"
        print(f"ERROR: {error_detail}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return {
            "error": error_detail,
            "status": "failed"
        }
    except Exception as e:
        import traceback
        error_detail = f"Error streaming from agent: {str(e)}"
        print(f"ERROR: {error_detail}")
        print(f"Traceback:\n{traceback.format_exc()}")
        return {
            "error": error_detail,
            "status": "failed"
        }


async def check_system_health_tool(assistant_id: str = "supervisor") -> dict:
    """Check comprehensive system health."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {
                            "type": "human",
                            "content": "Check system health"
                        }
                    ]
                },
                "stream_mode": ["values"]
            }
            
            async with client.stream(
                "POST",
                f"{LANGGRAPH_BASE_URL}/runs/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                chunks = []
                run_id = None
                final_output = None
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, list) and len(data) > 0:
                                if "run_id" in data[0]:
                                    run_id = data[0]["run_id"]
                                # Store as string to avoid parsing issues
                                final_output = chunk
                        except json.JSONDecodeError:
                            pass
                
                return {
                    "health_check": final_output or "".join(chunks),
                    "run_id": str(run_id or "unknown"),
                    "status": "success"
                }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


async def check_agent_status_tool(agent_name: str, assistant_id: str = "supervisor") -> dict:
    """Check the status of a specific agent."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {
                            "type": "human",
                            "content": f"Check {agent_name} agent status"
                        }
                    ]
                },
                "stream_mode": ["values"]
            }
            
            async with client.stream(
                "POST",
                f"{LANGGRAPH_BASE_URL}/runs/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                chunks = []
                run_id = None
                final_output = None
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, list) and len(data) > 0:
                                if "run_id" in data[0]:
                                    run_id = data[0]["run_id"]
                                # Store as string to avoid parsing issues
                                final_output = chunk
                        except json.JSONDecodeError:
                            pass
                
                return {
                    "agent": str(agent_name),
                    "status_check": final_output or "".join(chunks),
                    "run_id": str(run_id or "unknown"),
                    "status": "success"
                }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


async def get_thread_state_tool(thread_id: str) -> dict:
    """Get the current state of a conversation thread."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{LANGGRAPH_BASE_URL}/threads/{thread_id}/state"
            )
            response.raise_for_status()
            
            # Convert to string to ensure JSON serializability
            state_data = response.text
            
            return {
                "state": state_data,
                "thread_id": str(thread_id),
                "status": "success"
            }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


async def list_threads_tool(limit: int = 10) -> dict:
    """List available conversation threads."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                f"{LANGGRAPH_BASE_URL}/threads",
                params={"limit": limit}
            )
            response.raise_for_status()
            
            # Convert to string to ensure JSON serializability
            threads_data = response.text
            
            return {
                "threads": threads_data,
                "count": limit,
                "status": "success"
            }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


# ============================================================================
# Tool Router
# ============================================================================

async def execute_tool(
    tool_name: str,
    arguments: dict,
    auth: dict = None
) -> dict:
    """
    Execute a tool by name with given arguments.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
        auth: Authentication context (contains token_info for userId)
    
    Returns:
        Tool execution result
    """
    # Extract userId from auth token if available
    user_id = None
    if auth and auth.get("token_info"):
        token_info = auth["token_info"]
        user_id = (
            token_info.get("sub") or
            token_info.get("uid") or
            token_info.get("username") or
            token_info.get("email") or
            token_info.get("client_id")
        )
        print(f"DEBUG: Extracted userId from token: {user_id}")
    elif auth and auth.get("method") == "api_key":
        print("DEBUG: API key auth - no userId available")
    
    # Get conversationId from arguments if passed by ChatGPT
    conversation_id = arguments.get("conversationId")
    
    # Echo tool
    if tool_name == "echo":
        text = arguments.get("text", "")
        return {
            "content": [
                {
                    "type": "text",
                    "text": str(text)
                }
            ],
            "isError": False
        }
    
    # Get server info
    elif tool_name == "get_server_info":
        return {
            "name": "LangGraph Agent MCP Server",
            "version": "1.0.0",
            "transport": "fastapi-stateless",
            "endpoint": "/mcp",
            "langgraph_base_url": LANGGRAPH_BASE_URL,
            "port": CHATGPT_MCP_PORT,
            "chatgpt_compatible": True,
            "tools": [
                "echo",
                "get_server_info",
                "invoke_agent",
                "stream_agent",
                "check_system_health",
                "check_agent_status",
                "get_thread_state",
                "list_threads"
            ]
        }
    
    # Invoke agent
    elif tool_name == "invoke_agent":
        prompt = arguments.get("prompt", "")
        # Always use supervisor assistant
        assistant_id = "supervisor"
        thread_id = arguments.get("thread_id")
        return await invoke_langgraph_agent(
            prompt, assistant_id, thread_id, user_id, conversation_id
        )
    
    # Stream agent
    elif tool_name == "stream_agent":
        prompt = arguments.get("prompt", "")
        # Always use supervisor assistant
        assistant_id = "supervisor"
        thread_id = arguments.get("thread_id")
        return await stream_langgraph_agent(
            prompt, assistant_id, thread_id, user_id, conversation_id
        )
    
    # Check system health
    elif tool_name == "check_system_health":
        # Always use supervisor assistant
        assistant_id = "supervisor"
        return await check_system_health_tool(assistant_id)
    
    # Check agent status
    elif tool_name == "check_agent_status":
        agent_name = arguments.get("agent_name", "")
        # Always use supervisor assistant
        assistant_id = "supervisor"
        if not agent_name:
            return {"error": "agent_name is required", "status": "failed"}
        return await check_agent_status_tool(agent_name, assistant_id)
    
    # Get thread state
    elif tool_name == "get_thread_state":
        thread_id = arguments.get("thread_id", "")
        if not thread_id:
            return {"error": "thread_id is required", "status": "failed"}
        return await get_thread_state_tool(thread_id)
    
    # List threads
    elif tool_name == "list_threads":
        limit = arguments.get("limit", 10)
        return await list_threads_tool(limit)
    
    # Unknown tool
    else:
        return {
            "error": f"Unknown tool: {tool_name}",
            "status": "failed"
        }


# ============================================================================
# OAuth 2.0 Endpoints
# ============================================================================

@app.post("/oauth/token")
async def oauth_token(request: Request):
    """OAuth 2.0 token endpoint for Client Credentials flow."""
    if not OAUTH_ENABLED:
        return JSONResponse(
            status_code=400,
            content={
                "error": "unsupported_grant_type",
                "error_description": "OAuth is not enabled"
            }
        )
    
    try:
        body = await request.json()
    except:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "Invalid JSON body"
            }
        )
    
    grant_type = body.get("grant_type")
    client_id = body.get("client_id")
    client_secret = body.get("client_secret")
    scope = body.get("scope", "mcp:access")
    
    # Validate grant type
    if grant_type != "client_credentials":
        return JSONResponse(
            status_code=400,
            content={
                "error": "unsupported_grant_type",
                "error_description": "Only client_credentials supported"
            }
        )
    
    # Validate client credentials
    if not client_id or not client_secret:
        return JSONResponse(
            status_code=400,
            content={
                "error": "invalid_request",
                "error_description": "client_id and client_secret required"
            }
        )
    
    if client_id != OAUTH_CLIENT_ID or client_secret != OAUTH_CLIENT_SECRET:
        return JSONResponse(
            status_code=401,
            content={
                "error": "invalid_client",
                "error_description": "Invalid client credentials"
            }
        )
    
    # Generate access token
    access_token = secrets.token_urlsafe(32)
    expires_at = time.time() + OAUTH_TOKEN_EXPIRY
    
    # Store token
    active_tokens[access_token] = {
        "client_id": client_id,
        "scope": scope,
        "expires_at": expires_at,
        "created_at": time.time()
    }
    
    print(f"[OAuth] Token issued for client: {client_id}, scope: {scope}")
    
    return JSONResponse({
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": OAUTH_TOKEN_EXPIRY,
        "scope": scope
    })


@app.get("/oauth/info")
async def oauth_info():
    """OAuth 2.0 configuration information."""
    if not OAUTH_ENABLED:
        return JSONResponse({
            "enabled": False,
            "message": "OAuth is not enabled"
        })
    
    return JSONResponse({
        "enabled": True,
        "issuer": OAUTH_ISSUER,
        "token_endpoint": OAUTH_TOKEN_ENDPOINT,
        "grant_types_supported": ["client_credentials"],
        "scopes_supported": ["mcp:access"],
        "token_expiry_seconds": OAUTH_TOKEN_EXPIRY
    })


# ============================================================================
# OAuth 2.0 Discovery Endpoints (RFC 8414)
# ============================================================================

@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server_metadata():
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    if not OAUTH_ENABLED:
        return JSONResponse(
            status_code=404,
            content={"error": "OAuth not enabled"}
        )
    
    return JSONResponse({
        "issuer": OAUTH_ISSUER,
        "token_endpoint": OAUTH_TOKEN_ENDPOINT,
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic"
        ],
        "grant_types_supported": ["client_credentials"],
        "response_types_supported": [],
        "scopes_supported": ["mcp:access"],
        "service_documentation": f"{SERVER_URL}/docs",
        "revocation_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic"
        ]
    })


@app.get("/.well-known/oauth-authorization-server/mcp")
async def oauth_authorization_server_mcp():
    """OAuth 2.0 Authorization Server Metadata for MCP resource."""
    return await oauth_authorization_server_metadata()


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource_metadata():
    """OAuth 2.0 Protected Resource Metadata."""
    if not OAUTH_ENABLED:
        return JSONResponse(
            status_code=404,
            content={"error": "OAuth not enabled"}
        )
    
    return JSONResponse({
        "resource": SERVER_URL,
        "authorization_servers": [OAUTH_ISSUER],
        "scopes_supported": ["mcp:access"],
        "bearer_methods_supported": ["header"],
        "resource_documentation": f"{SERVER_URL}/docs"
    })


@app.get("/.well-known/oauth-protected-resource/mcp")
async def oauth_protected_resource_mcp():
    """OAuth 2.0 Protected Resource Metadata for MCP."""
    return await oauth_protected_resource_metadata()


@app.get("/.well-known/openid-configuration")
async def openid_configuration():
    """OpenID Connect Discovery metadata."""
    if not OAUTH_ENABLED:
        return JSONResponse(
            status_code=404,
            content={"error": "OAuth not enabled"}
        )
    
    return JSONResponse({
        "issuer": OAUTH_ISSUER,
        "token_endpoint": OAUTH_TOKEN_ENDPOINT,
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic"
        ],
        "grant_types_supported": ["client_credentials"],
        "response_types_supported": [],
        "scopes_supported": ["mcp:access"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": [],
        "claims_supported": ["sub", "iat", "exp"]
    })


@app.get("/.well-known/openid-configuration/mcp")
async def openid_configuration_mcp():
    """OpenID Connect Discovery for MCP resource."""
    return await openid_configuration()


@app.get("/mcp/.well-known/openid-configuration")
async def mcp_openid_configuration():
    """OpenID Connect Discovery under /mcp path."""
    return await openid_configuration()


# ============================================================================
# MCP Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with server information."""
    return {
        "name": "LangGraph Agent MCP Server",
        "version": "1.0.0",
        "transport": "fastapi-stateless",
        "endpoints": {
            "mcp": "/mcp (JSON-RPC 2.0)",
            "health": "/health",
            "tools": "/tools (list available tools)"
        },
        "chatgpt_compatible": True
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{LANGGRAPH_BASE_URL}/ok")
            response.raise_for_status()
            langgraph_ok = response.json().get("ok", False)
    except:
        langgraph_ok = False
    
    return {
        "status": "ok",
        "server": "running",
        "langgraph_backend": "connected" if langgraph_ok else "disconnected",
        "langgraph_url": LANGGRAPH_BASE_URL
    }


@app.get("/tools")
async def list_tools():
    """List all available tools in MCP-compliant format."""
    return {
        "tools": [
            {
                "name": "echo",
                "description": "Echo text back - test connectivity",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "Text to echo back"
                        }
                    },
                    "required": ["text"]
                }
            },
            {
                "name": "get_server_info",
                "description": "Get server information and capabilities",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "invoke_agent",
                "description": "Execute the LangGraph agent with a prompt",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt to send to the agent"
                        },
                        "assistant_id": {
                            "type": "string",
                            "description": "Assistant ID to use",
                            "default": "agent"
                        },
                        "thread_id": {
                            "type": "string",
                            "description": "Thread ID for conversation context"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "stream_agent",
                "description": "Stream responses from the LangGraph agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "prompt": {
                            "type": "string",
                            "description": "The prompt to send to the agent"
                        },
                        "assistant_id": {
                            "type": "string",
                            "description": "Assistant ID to use",
                            "default": "supervisor"
                        },
                        "thread_id": {
                            "type": "string",
                            "description": "Thread ID for conversation context"
                        }
                    },
                    "required": ["prompt"]
                }
            },
            {
                "name": "check_system_health",
                "description": "Check comprehensive system health",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "assistant_id": {
                            "type": "string",
                            "description": "Assistant ID to check",
                            "default": "supervisor"
                        }
                    }
                }
            },
            {
                "name": "check_agent_status",
                "description": "Check status of a specific agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_name": {
                            "type": "string",
                            "description": "Name of the agent to check"
                        },
                        "assistant_id": {
                            "type": "string",
                            "description": "Assistant ID to use",
                            "default": "supervisor"
                        }
                    },
                    "required": ["agent_name"]
                }
            },
            {
                "name": "get_thread_state",
                "description": "Get current conversation thread state",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "thread_id": {
                            "type": "string",
                            "description": "Thread ID to retrieve state for"
                        }
                    },
                    "required": ["thread_id"]
                }
            },
            {
                "name": "list_threads",
                "description": "List available conversation threads",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of threads to return",
                            "default": 10
                        }
                    }
                }
            }
        ]
    }


@app.get("/mcp")
async def mcp_info():
    """GET endpoint for /mcp - provides information about the MCP endpoint."""
    return JSONResponse({
        "name": "LangGraph Agent MCP Server",
        "version": "1.0.0",
        "protocol": "JSON-RPC 2.0",
        "transport": "HTTP POST",
        "authentication": "OAuth 2.0 Bearer Token" if OAUTH_ENABLED else "None",
        "endpoints": {
            "mcp": "POST /mcp (JSON-RPC 2.0 requests)",
            "tools": "GET /tools (list available tools)",
            "health": "GET /health (server health check)",
            "oauth_token": "POST /oauth/token (get access token)" if OAUTH_ENABLED else None,
            "oauth_info": "GET /oauth/info (OAuth configuration)" if OAUTH_ENABLED else None
        },
        "documentation": f"{SERVER_URL}/docs",
        "message": "This endpoint accepts POST requests with JSON-RPC 2.0 format. Use POST /mcp with proper authentication."
    })


@app.post("/mcp")
async def mcp_endpoint(
    request: Request,
    auth: dict = Depends(verify_token)
):
    """
    Main MCP endpoint - JSON-RPC 2.0 compatible.
    
    This endpoint handles stateless JSON-RPC requests from ChatGPT Enterprise.
    Requires OAuth token or API key authentication if OAuth is enabled.
    """
    # Log incoming request for debugging
    print("\n" + "=" * 80)
    print("INCOMING REQUEST TO /mcp")
    print("=" * 80)
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Client: {request.client.host if request.client else 'Unknown'}:{request.client.port if request.client else 'Unknown'}")
    print("\nHeaders:")
    for header, value in request.headers.items():
        print(f"  {header}: {value}")
    
    try:
        # Read and log raw body
        body_bytes = await request.body()
        print(f"\nRaw Body ({len(body_bytes)} bytes):")
        print(body_bytes.decode('utf-8'))
        
        # Parse JSON
        try:
            body = json.loads(body_bytes)
            print("\nParsed JSON:")
            print(json.dumps(body, indent=2))
        except json.JSONDecodeError as e:
            print(f"\nJSON Parse Error: {e}")
            print("=" * 80 + "\n")
            return JSONResponse(
                status_code=400,
                content={
                    "jsonrpc": "2.0",
                    "id": "error",
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: Invalid JSON - {str(e)}"
                    }
                }
            )
        
        # Validate JSON-RPC format
        if not isinstance(body, dict):
            error_response = {
                "jsonrpc": "2.0",
                "id": "error",
                "error": {
                    "code": -32600,
                    "message": "Invalid Request: body must be an object"
                }
            }
            print("\nResponse (400 Bad Request):")
            print(json.dumps(error_response, indent=2))
            print("=" * 80 + "\n")
            return JSONResponse(
                status_code=400,
                content=error_response
            )
        
        req_id = body.get("id", "unknown")
        method = body.get("method", "")
        params = body.get("params", {})
        
        print(f"\nExtracted:")
        print(f"  ID: {req_id}")
        print(f"  Method: {method}")
        print(f"  Params: {json.dumps(params, indent=4)}")
        
        # Handle MCP notifications (no response required)
        if method.startswith("notifications/"):
            print(f"\nHandling notification: {method}")
            print("Response (204 No Content - Notification acknowledged)")
            print("=" * 80 + "\n")
            return Response(status_code=204)
        
        # Handle initialize method (for MCP protocol compliance)
        if method == "initialize":
            response_data = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {
                        "name": "LangGraph Agent MCP Server",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": {},
                        "resources": {}
                    }
                }
            }
            print("\nResponse (200 OK):")
            print(json.dumps(response_data, indent=2))
            print("=" * 80 + "\n")
            return JSONResponse(response_data)
        
        # Handle tools/call method
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            
            if not tool_name:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32602,
                        "message": "Invalid params: 'name' is required"
                    }
                }
                print("\nResponse (400 Bad Request):")
                print(json.dumps(error_response, indent=2))
                print("=" * 80 + "\n")
                return JSONResponse(
                    status_code=400,
                    content=error_response
                )
            
            # Execute the tool with auth context
            result = await execute_tool(tool_name, arguments, auth)
            
            # Check if tool execution failed
            if result.get("status") == "failed":
                error_msg = result.get('error', 'Unknown error')
                error_response = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {
                        "code": -32603,
                        "message": f"Tool execution failed: {error_msg}"
                    }
                }
                print("\nResponse (500 Internal Server Error):")
                print(json.dumps(error_response, indent=2))
                print("=" * 80 + "\n")
                return JSONResponse(
                    status_code=500,
                    content=error_response
                )
            
            # Return successful result
            success_response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result
            }
            print("\nResponse (200 OK - Tool executed):")
            print(json.dumps(success_response, indent=2))
            print("=" * 80 + "\n")
            return JSONResponse(success_response)
        
        # Handle tools/list method
        elif method == "tools/list":
            tools_data = await list_tools()
            list_response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": tools_data
            }
            print("\nResponse (200 OK - Tools list):")
            print(json.dumps(list_response, indent=2))
            print("=" * 80 + "\n")
            return JSONResponse(list_response)
        
        # Unknown method
        else:
            unknown_response = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32601,
                    "message": f"Method not found: {method}"
                }
            }
            print("\nResponse (400 Bad Request - Unknown method):")
            print(json.dumps(unknown_response, indent=2))
            print("=" * 80 + "\n")
            return JSONResponse(
                status_code=400,
                content=unknown_response
            )
    
    except json.JSONDecodeError:
        decode_error = {
            "jsonrpc": "2.0",
            "id": "error",
            "error": {
                "code": -32700,
                "message": "Parse error: Invalid JSON"
            }
        }
        print("\nResponse (400 Bad Request - JSON Parse Error):")
        print(json.dumps(decode_error, indent=2))
        print("=" * 80 + "\n")
        return JSONResponse(
            status_code=400,
            content=decode_error
        )
    except Exception as e:
        req_id = "error"
        if isinstance(body, dict):
            req_id = body.get("id", "error")
        
        server_error = {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32603,
                "message": f"Internal error: {str(e)}"
            }
        }
        print("\nResponse (500 Internal Server Error):")
        print(json.dumps(server_error, indent=2))
        print("=" * 80 + "\n")
        return JSONResponse(
            status_code=500,
            content=server_error
        )


# ============================================================================
# Main Entry Point
# ============================================================================

if __name__ == "__main__":
    print("=" * 80)
    print("ChatGPT Enterprise MCP Server (FastAPI Stateless)")
    print("=" * 80)
    print(f"Server Name: LangGraph Agent MCP Server")
    print(f"Transport: FastAPI (stateless HTTP)")
    print(f"Port: {CHATGPT_MCP_PORT}")
    print(f"MCP Endpoint: http://0.0.0.0:{CHATGPT_MCP_PORT}/mcp")
    print(f"Health: http://0.0.0.0:{CHATGPT_MCP_PORT}/health")
    print(f"Tools: http://0.0.0.0:{CHATGPT_MCP_PORT}/tools")
    print(f"LangGraph Backend: {LANGGRAPH_BASE_URL}")
    print()
    print("ChatGPT Enterprise Setup:")
    print(f"  1. Use URL: http://your-server:{CHATGPT_MCP_PORT}/mcp")
    print(f"  2. Add to ChatGPT Apps & Connectors")
    print(f"  3. Test with: python test_chatgpt_mcp.py")
    print()
    print("Available Tools:")
    print("  - echo: Test connectivity")
    print("  - get_server_info: Server information")
    print("  - invoke_agent: Execute LangGraph agent")
    print("  - stream_agent: Stream agent responses")
    print("  - check_system_health: System diagnostics")
    print("  - check_agent_status: Check specific agent")
    print("  - get_thread_state: Get conversation state")
    print("  - list_threads: List conversations")
    print("=" * 80)
    print()
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=CHATGPT_MCP_PORT,
        log_level="info"
    )
