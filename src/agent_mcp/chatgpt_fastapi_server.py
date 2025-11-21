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

# Okta Configuration (for external token validation)
OKTA_INTROSPECT_URL = os.getenv("OKTA_INTROSPECT_URL", "")
OKTA_DOMAIN = os.getenv("OKTA_DOMAIN", "")

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


async def validate_okta_token(token: str) -> bool:
    """Validate token with Okta introspection endpoint."""
    if not OKTA_INTROSPECT_URL:
        print("⚠️  Okta introspection URL not configured")
        return False
    
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
                    return True
                else:
                    print("✗ Okta token is inactive or invalid")
                    return False
            else:
                print(f"✗ Okta introspection failed: {response.status_code}")
                print(f"Response: {response.text}")
                return False
    except Exception as e:
        print(f"✗ Error validating token with Okta: {e}")
        return False


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
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
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
            # Token expired
            del active_tokens[token]
            print("✗ Token expired, removing from active tokens")
            print("=" * 80 + "\n")
            raise HTTPException(
                status_code=401,
                detail="Token expired",
                headers={"WWW-Authenticate": "Bearer"}
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
        is_valid = await validate_okta_token(token)
        if is_valid:
            print("✓ Token validated by Okta")
            print("=" * 80 + "\n")
            return {"type": "okta_token", "valid": True}
    
    print("✗ Invalid token - not found in active tokens, API keys, or Okta")
    print(f"Token to validate: {token[:30]}...")
    print(f"Active tokens: {list(active_tokens.keys())[:3]}..." if active_tokens else "Active tokens: []")
    print("=" * 80 + "\n")
    raise HTTPException(
        status_code=401,
        detail="Invalid token or API key",
        headers={"WWW-Authenticate": "Bearer"}
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
    assistant_id: str = "agent",
    thread_id: Optional[str] = None
) -> dict:
    """
    Invoke the LangGraph agent with a prompt.
    
    Args:
        prompt: The user prompt/query
        assistant_id: The assistant/agent ID (default: "agent")
        thread_id: Optional thread ID for conversation continuity
    
    Returns:
        Agent response with output and metadata
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
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
                "stream_mode": ["values"]
            }
            
            if thread_id:
                payload["thread_id"] = thread_id
            
            async with client.stream(
                "POST",
                f"{LANGGRAPH_BASE_URL}/runs/stream",
                json=payload
            ) as response:
                response.raise_for_status()
                
                chunks = []
                run_id = None
                thread_id_result = None
                final_output = None
                
                async for chunk in response.aiter_text():
                    if chunk.strip():
                        chunks.append(chunk)
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, list) and len(data) > 0:
                                if "run_id" in data[0]:
                                    run_id = data[0]["run_id"]
                                if "thread_id" in data[0]:
                                    thread_id_result = data[0]["thread_id"]
                                final_output = data
                        except json.JSONDecodeError:
                            pass
                
                return {
                    "run_id": run_id or "unknown",
                    "thread_id": thread_id_result or "unknown",
                    "output": final_output or {"messages": chunks},
                    "status": "success"
                }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


async def stream_langgraph_agent(
    prompt: str,
    assistant_id: str = "agent",
    thread_id: Optional[str] = None
) -> dict:
    """Stream responses from the LangGraph agent."""
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            payload = {
                "assistant_id": assistant_id,
                "input": {
                    "messages": [
                        {
                            "type": "human",
                            "content": prompt
                        }
                    ]
                }
            }
            
            if thread_id:
                payload["thread_id"] = thread_id
            
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
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


async def check_system_health_tool(assistant_id: str = "health") -> dict:
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
                                final_output = data
                        except json.JSONDecodeError:
                            pass
                
                return {
                    "health_check": final_output or {"messages": chunks},
                    "run_id": run_id or "unknown",
                    "status": "success"
                }
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }


async def check_agent_status_tool(agent_name: str, assistant_id: str = "health") -> dict:
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
                                final_output = data
                        except json.JSONDecodeError:
                            pass
                
                return {
                    "agent": agent_name,
                    "status_check": final_output or {"messages": chunks},
                    "run_id": run_id or "unknown",
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
            
            return {
                "state": response.json(),
                "thread_id": thread_id,
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
            
            return {
                "threads": response.json(),
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

async def execute_tool(tool_name: str, arguments: dict) -> dict:
    """
    Execute a tool by name with given arguments.
    
    Args:
        tool_name: Name of the tool to execute
        arguments: Tool arguments
    
    Returns:
        Tool execution result
    """
    # Echo tool
    if tool_name == "echo":
        text = arguments.get("text", "")
        return {"echo": text}
    
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
        assistant_id = arguments.get("assistant_id", "agent")
        thread_id = arguments.get("thread_id")
        return await invoke_langgraph_agent(prompt, assistant_id, thread_id)
    
    # Stream agent
    elif tool_name == "stream_agent":
        prompt = arguments.get("prompt", "")
        assistant_id = arguments.get("assistant_id", "agent")
        thread_id = arguments.get("thread_id")
        return await stream_langgraph_agent(prompt, assistant_id, thread_id)
    
    # Check system health
    elif tool_name == "check_system_health":
        assistant_id = arguments.get("assistant_id", "health")
        return await check_system_health_tool(assistant_id)
    
    # Check agent status
    elif tool_name == "check_agent_status":
        agent_name = arguments.get("agent_name", "")
        assistant_id = arguments.get("assistant_id", "health")
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
                "name": "check_system_health",
                "description": "Check comprehensive system health",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "assistant_id": {
                            "type": "string",
                            "description": "Assistant ID to check",
                            "default": "health"
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
                            "default": "health"
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
            
            # Execute the tool
            result = await execute_tool(tool_name, arguments)
            
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
