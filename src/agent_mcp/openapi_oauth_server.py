"""
OAuth-compliant OpenAPI server for ChatGPT Enterprise integration.

Uses OAuth 2.0 Client Credentials flow for service-to-service authentication.
Includes well-known discovery endpoints required by ChatGPT Enterprise.
"""

import json
import os
import httpx
import secrets
import copy
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Depends, Request, status, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.security import OAuth2
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
LANGGRAPH_BASE_URL = os.getenv("LANGGRAPH_BASE_URL", "http://localhost:2024").rstrip("/")
OAUTH_ENABLED = os.getenv("OAUTH_ENABLED", "true").lower() == "true"
OAUTH_PROVIDER = os.getenv("OAUTH_PROVIDER", "okta")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
API_KEYS = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") \
    else []
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8001")

# Plugin metadata
CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "support@example.com")
PLUGIN_NAME = os.getenv("PLUGIN_NAME", "LangGraph Agent")

# Okta Configuration
OKTA_DOMAIN = os.getenv("OKTA_DOMAIN", "")
OKTA_INTROSPECT_URL = os.getenv(
    "OKTA_INTROSPECT_URL",
    f"https://{os.getenv('OKTA_DOMAIN', '')}/oauth2/default/v1/introspect"
)
OKTA_CLIENT_ID = os.getenv("OKTA_CLIENT_ID", "")
OKTA_CLIENT_SECRET = os.getenv("OKTA_CLIENT_SECRET", "")

# Google Configuration
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

# Public endpoints that don't require authentication (ChatGPT Enterprise compatibility)
PUBLIC_ENDPOINTS = {
    "/health",
    "/.well-known/ai-plugin.json",
    "/.well-known/openid-configuration",
    "/.well-known/oauth-authorization-server",
    "/.well-known/jwks.json",
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-authorization-server/openapi.json",
    "/.well-known/openid-configuration/openapi.json",
    "/.well-known/oauth-protected-resource/openapi.json",
    "/openapi.json/.well-known/openid-configuration",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/openapi.actions.json",
    "/openapi.test.json",
    "/favicon.ico",
    "/logo.png",
    "/test",
    "/telephony",
    "/"
}

# Create FastAPI app with OpenAPI metadata
app = FastAPI(
    title="LangGraph Agent API",
    description="OAuth-secured API for LangGraph agents",
    version="1.0.0",
    servers=[
        {
            "url": SERVER_BASE_URL,
            "description": "API Server"
        }
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Customize OpenAPI schema to include OAuth2 Client Credentials
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    from fastapi.openapi.utils import get_openapi
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Add servers configuration (CRITICAL for ChatGPT)
    openapi_schema["servers"] = [
        {
            "url": SERVER_BASE_URL,
            "description": "API Server"
        }
    ]
    
    # Add API Key security scheme
    # ChatGPT GPTs only support ONE security scheme, so we use API Key
    # (OAuth is still supported in backend, just not advertised in OpenAPI)
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    # Apply API Key security globally to all endpoints
    openapi_schema["security"] = [
        {"ApiKeyAuth": []}
    ]
    
    # IMPORTANT: ChatGPT recommends explicitly declaring security
    # on each endpoint in addition to the global security declaration
    if "paths" in openapi_schema:
        for path, path_item in openapi_schema["paths"].items():
            for method, operation in path_item.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # Add security to each operation unless public endpoint
                    # Skip security for well-known endpoints and docs
                    is_public = (
                        path.startswith("/.well-known") or
                        path in ["/openapi.json", "/docs", "/redoc"]
                    )
                    if not is_public and isinstance(operation, dict):
                        operation["security"] = [{"ApiKeyAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


def _get_actions_openapi_schema() -> Dict[str, Any]:
    """Return a cleaned OpenAPI schema containing only the action endpoints.

    This helps ChatGPT Enterprise import only the relevant actions and avoid
    picking up metadata/well-known endpoints which may confuse the Actions UI.
    """
    # Use the full generated schema and deep-copy it before filtering
    schema = app.openapi()
    schema_copy = copy.deepcopy(schema)

    allowed_paths = {"/health", "/invoke", "/stream", "/agents"}
    paths = schema_copy.get("paths", {})

    filtered_paths = {p: v for p, v in paths.items() if p in allowed_paths}
    schema_copy["paths"] = filtered_paths

    # Keep components (security schemes) and servers as-is so auth is preserved
    # If other components are present that's fine — ChatGPT only needs security
    return schema_copy


@app.get("/openapi.actions.json")
async def openapi_actions():
    """Serve a trimmed OpenAPI schema with only the action endpoints.

    Use this URL when importing actions into ChatGPT Enterprise to avoid
    unrelated endpoints (like /.well-known) being included.
    """
    return _get_actions_openapi_schema()


@app.get("/openapi.test.json")
async def openapi_test():
    """Minimal OpenAPI schema for testing connectivity."""
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "LangGraph Agent API - Test",
            "description": "Minimal test schema for verifying "
                          "ChatGPT Enterprise connectivity",
            "version": "1.0.0"
        },
        "servers": [
            {
                "url": SERVER_BASE_URL,
                "description": "API Server"
            }
        ],
        "paths": {
            "/health": {
                "get": {
                    "operationId": "health_check",
                    "summary": "Health Check",
                    "description": "Check if the API server is healthy",
                    "tags": ["System"],
                    "responses": {
                        "200": {
                            "description": "Server is healthy",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string",
                                                "example": "healthy"
                                            },
                                            "service": {
                                                "type": "string"
                                            },
                                            "version": {
                                                "type": "string"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            },
            "/test": {
                "get": {
                    "operationId": "test_connection",
                    "summary": "Test Connection",
                    "description": "Test API connectivity",
                    "tags": ["Testing"],
                    "responses": {
                        "200": {
                            "description": "Connection successful",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "status": {
                                                "type": "string"
                                            },
                                            "message": {
                                                "type": "string"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key"
                }
            }
        }
    }


# Add session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    max_age=3600
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request logging middleware for debugging Enterprise integration
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for debugging Enterprise integration."""
    import time
    from datetime import datetime
    
    start_time = time.time()
    
    # Log incoming request
    print(f"\\n{'='*70}")
    print(f"📥 REQUEST - {datetime.now().isoformat()}")
    print(f"{'='*70}")
    print(f"Method: {request.method}")
    print(f"Path: {request.url.path}")
    print(f"Client: {request.client.host if request.client else 'Unknown'}")
    
    # Check if from ChatGPT
    user_agent = request.headers.get("user-agent", "")
    if "ChatGPT" in user_agent or "OpenAI" in user_agent:
        print("🤖 REQUEST FROM CHATGPT/OPENAI DETECTED!")
    
    # Process request
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Log response
        print(f"\\n📤 RESPONSE: {response.status_code} "
              f"({duration:.3f}s)")
        if response.status_code >= 400:
            print(f"⚠️  ERROR")
        else:
            print(f"✅ SUCCESS")
        print(f"{'='*70}\\n")
        
        return response
        
    except Exception as e:
        print(f"\\n❌ EXCEPTION: {str(e)}")
        print(f"{'='*70}\\n")
        raise


# OAuth2 scheme for Client Credentials flow (ChatGPT Enterprise)
class OAuth2ClientCredentials(OAuth2):
    """OAuth2 Client Credentials flow for ChatGPT Enterprise."""
    def __init__(self, tokenUrl: str, auto_error: bool = True):
        flows = {
            "clientCredentials": {
                "tokenUrl": tokenUrl,
                "scopes": {}
            }
        }
        super().__init__(flows=flows, auto_error=auto_error)


oauth2_scheme = OAuth2ClientCredentials(
    tokenUrl=f"{SERVER_BASE_URL}/oauth/token",
    auto_error=False
)


# ==========================================
# Pydantic Models
# ==========================================

class InvokeRequest(BaseModel):
    """Request model for invoking the agent."""
    prompt: str = Field(
        ...,
        description="The user prompt/query to send to the agent",
        example="What is the weather like today?"
    )
    assistant_id: str = Field(
        default="supervisor",
        description="The assistant/agent ID to invoke",
        example="supervisor"
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID for conversation continuity",
        example="thread-abc-123"
    )
    conversationId: Optional[str] = Field(
        default=None,
        description="Optional conversation ID from ChatGPT",
        example="conv-abc-123"
    )


class InvokeResponse(BaseModel):
    """Response model for agent invocation."""
    run_id: str = Field(..., description="The run ID")
    thread_id: str = Field(..., description="The thread ID")
    output: Dict[str, Any] = Field(..., description="Agent response")
    status: str = Field(..., description="Status", example="success")


class StreamRequest(BaseModel):
    """Request model for streaming agent responses."""
    prompt: str = Field(
        ...,
        description="The user prompt/query",
        example="Explain quantum computing"
    )
    assistant_id: str = Field(
        default="supervisor",
        description="The assistant/agent ID",
        example="supervisor"
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID",
        example="thread-xyz-789"
    )
    conversationId: Optional[str] = Field(
        default=None,
        description="Optional conversation ID from ChatGPT",
        example="conv-xyz-789"
    )


class StreamResponse(BaseModel):
    """Response model for streaming."""
    output: str = Field(..., description="The streamed content")
    chunks_received: int = Field(..., description="Chunks received")
    status: str = Field(..., description="Status", example="success")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., example="healthy")
    service: str = Field(..., example="LangGraph Agent API")
    version: str = Field(..., example="1.0.0")
    auth_enabled: bool = Field(..., example=True)


class OAuthConfigResponse(BaseModel):
    """OAuth configuration response."""
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    userinfo_endpoint: Optional[str] = None
    jwks_uri: Optional[str] = None
    response_types_supported: list = ["code", "token"]
    grant_types_supported: list = ["authorization_code", "client_credentials"]  # noqa: E501
    subject_types_supported: list = ["public"]
    id_token_signing_alg_values_supported: list = ["RS256"]
    scopes_supported: list = ["openid", "profile", "email"]


# ==========================================
# Authentication
# ==========================================

async def verify_token(request: Request):
    """Verify OAuth token (from Okta) or API key."""
    
    # Allow public endpoints without authentication (Enterprise compatibility)
    if request.url.path in PUBLIC_ENDPOINTS:
        print(f"DEBUG: ✅ Public endpoint accessed: {request.url.path}")
        return {"authenticated": True, "method": "public", "public": True}
    
    # DEBUG: Log all headers received
    print("=" * 70)
    print("DEBUG: Authentication Request")
    print("=" * 70)
    print(f"Path: {request.url.path}")
    print(f"Method: {request.method}")
    print("Headers:")
    for header_name, header_value in request.headers.items():
        # Mask sensitive values for security
        if header_name.lower() in ["authorization", "x-api-key"]:
            if header_value:
                masked = header_value[:10] + "..." if len(header_value) > 10 else "***"
                print(f"  {header_name}: {masked}")
        else:
            print(f"  {header_name}: {header_value}")
    print()
    
    # Check for API key in header
    api_key = request.headers.get("X-API-Key")
    print(f"DEBUG: X-API-Key header present: {api_key is not None}")
    if api_key:
        print(f"DEBUG: API Key (first 10 chars): {api_key[:10]}...")
        print(f"DEBUG: Configured API_KEYS: {len(API_KEYS)} keys")
        if API_KEYS:
            print(f"DEBUG: First configured key (first 10 chars): {API_KEYS[0][:10]}...")
    
    if api_key and api_key in API_KEYS:
        print("DEBUG: ✅ API Key authentication SUCCESSFUL")
        print("=" * 70)
        return {"authenticated": True, "method": "api_key"}
    elif api_key:
        print("DEBUG: ❌ API Key NOT FOUND in configured keys")
        print("=" * 70)
    
    # Check for Bearer token
    auth_header = request.headers.get("Authorization")
    print(f"DEBUG: Authorization header present: {auth_header is not None}")
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        print(f"DEBUG: Bearer token found (first 10 chars): {token[:10]}...")
        
        # Validate token with Okta if OAuth is enabled
        if OAUTH_ENABLED and OAUTH_PROVIDER == "okta":
            print(f"DEBUG: Validating token with Okta (OAUTH_ENABLED={OAUTH_ENABLED})")
            print(f"DEBUG: Using introspect URL: {OKTA_INTROSPECT_URL}")
            try:
                import httpx
                
                introspect_url = OKTA_INTROSPECT_URL
                
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        introspect_url,
                        data={
                            "token": token,
                            "token_type_hint": "access_token"
                        },
                        auth=(OKTA_CLIENT_ID, OKTA_CLIENT_SECRET),
                        timeout=10.0
                    )
                    
                    if response.status_code == 200:
                        token_info = response.json()
                        if token_info.get("active"):
                            print("DEBUG: ✅ Okta token validation SUCCESSFUL")
                            claims = list(token_info.keys())
                            print(f"DEBUG: Token claims: {claims}")
                            print("=" * 70)
                            return {
                                "authenticated": True,
                                "method": "oauth",
                                "token": token,
                                "token_info": token_info
                            }
                        else:
                            print("DEBUG: ❌ Token is not active")
                            print("=" * 70)
                            raise HTTPException(
                                status_code=401,
                                detail="Token is not active or has expired",
                                headers={"WWW-Authenticate": "Bearer"}
                            )
                    else:
                        print(
                            f"DEBUG: ❌ Okta returned status "
                            f"{response.status_code}"
                        )
                        print("=" * 70)
                        raise HTTPException(
                            status_code=401,
                            detail=(
                                f"Token validation failed with status "
                                f"{response.status_code}"
                            ),
                            headers={"WWW-Authenticate": "Bearer"}
                        )
            except Exception as e:
                print(f"DEBUG: ❌ Token validation error: {e}")
                print("=" * 70)
                raise HTTPException(
                    status_code=401,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )
    
    # Check session
    if request.session.get("user"):
        print("DEBUG: ✅ Session authentication")
        print("=" * 70)
        return {"authenticated": True, "method": "session",
                "user": request.session.get("user")}
    
    # If OAuth not enabled, allow unauthenticated access
    if not OAUTH_ENABLED:
        print("DEBUG: ✅ Unauthenticated access (OAUTH_ENABLED=false)")
        print("=" * 70)
        return {"authenticated": True, "method": "none"}
    
    print("DEBUG: ❌ AUTHENTICATION FAILED - No valid credentials found")
    print("=" * 70)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )


# ==========================================
# Well-Known Endpoints (Required by ChatGPT)
# ==========================================

@app.get("/.well-known/ai-plugin.json")
async def ai_plugin_manifest():
    """
    AI Plugin manifest for ChatGPT Enterprise.
    This is REQUIRED for ChatGPT to discover your actions.
    
    Reference: https://platform.openai.com/docs/plugins
    """
    return {
        "schema_version": "v1",
        "name_for_human": PLUGIN_NAME,
        "name_for_model": "langgraph_agent",
        "description_for_human": (
            "Access to LangGraph AI agents for complex reasoning, "
            "analysis, and content generation."
        ),
        "description_for_model": (
            "You can invoke LangGraph agents to help with complex queries, "
            "detailed analysis, reasoning tasks, and content generation. "
            "Use the invoke endpoint for complete responses or stream "
            "endpoint for longer queries."
        ),
        "auth": {
            "type": "service_http",
            "authorization_type": "bearer",
            "verification_tokens": {
                "openai": OKTA_CLIENT_ID or "your-verification-token-here"
            }
        },
        "api": {
            "type": "openapi",
            "url": f"{SERVER_BASE_URL}/openapi.actions.json",
            "is_user_authenticated": False
        },
        "logo_url": f"{SERVER_BASE_URL}/logo.png",
        "contact_email": CONTACT_EMAIL,
        "legal_info_url": f"{SERVER_BASE_URL}/legal",
        "privacy_policy_url": f"{SERVER_BASE_URL}/privacy"
    }


@app.get("/.well-known/openid-configuration")
async def openid_configuration():
    """
    OpenID Connect discovery endpoint.
    Points to Okta as the OAuth provider.
    """
    okta_issuer = f"https://{OKTA_DOMAIN}/oauth2/default"
    return {
        "issuer": okta_issuer,
        "authorization_endpoint": f"{okta_issuer}/v1/authorize",
        "token_endpoint": f"{okta_issuer}/v1/token",
        "userinfo_endpoint": f"{okta_issuer}/v1/userinfo",
        "jwks_uri": f"{okta_issuer}/v1/keys",
        "response_types_supported": ["code", "token", "id_token"],
        "grant_types_supported": ["client_credentials", "authorization_code"],
        "subject_types_supported": ["public"],
        "id_token_signing_alg_values_supported": ["RS256"],
        "scopes_supported": ["openid", "profile", "email"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post"
        ],
        "claims_supported": ["sub", "name", "email", "email_verified"]
    }


@app.get("/.well-known/oauth-authorization-server")
async def oauth_authorization_server():
    """
    OAuth 2.0 authorization server metadata.
    Points to Okta as the OAuth provider.
    """
    okta_issuer = f"https://{OKTA_DOMAIN}/oauth2/default"
    return {
        "issuer": okta_issuer,
        "token_endpoint": f"{okta_issuer}/v1/token",
        "jwks_uri": f"{okta_issuer}/v1/keys",
        "grant_types_supported": ["client_credentials"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_basic",
            "client_secret_post"
        ],
        "scopes_supported": ["openid", "profile", "email"]
    }


@app.get("/.well-known/jwks.json")
async def jwks():
    """JSON Web Key Set endpoint."""
    # In production, return actual public keys
    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "kid": "1",
                "alg": "RS256",
                "n": "example_modulus",
                "e": "AQAB"
            }
        ]
    }


@app.get("/.well-known/oauth-protected-resource")
async def oauth_protected_resource():
    """OAuth 2.0 protected resource metadata."""
    return {
        "resource": SERVER_BASE_URL,
        "authorization_servers": [SERVER_BASE_URL],
        "scopes_supported": ["openid", "profile", "email"],
        "bearer_methods_supported": ["header", "query"],
        "resource_documentation": f"{SERVER_BASE_URL}/docs"
    }


@app.get("/.well-known/oauth-authorization-server/openapi.json")
async def oauth_server_openapi():
    """OpenAPI spec for OAuth authorization server."""
    # Return a reference to the main OpenAPI spec
    return RedirectResponse(url="/openapi.json", status_code=302)


@app.get("/.well-known/openid-configuration/openapi.json")
async def openid_config_openapi():
    """OpenAPI spec for OpenID configuration."""
    # Return a reference to the main OpenAPI spec
    return RedirectResponse(url="/openapi.json", status_code=302)


@app.get("/.well-known/oauth-protected-resource/openapi.json")
async def oauth_protected_resource_openapi():
    """OpenAPI spec for OAuth protected resource."""
    # Return a reference to the main OpenAPI spec
    return RedirectResponse(url="/openapi.json", status_code=302)


@app.get("/openapi.json/.well-known/openid-configuration")
async def openapi_openid_config():
    """OpenID configuration at alternate path (for some OAuth clients)."""
    # Return the same OpenID configuration
    return await openid_configuration()


# ==========================================
# OAuth Token Endpoint (Client Credentials)
# ==========================================

@app.post("/oauth/token")
async def oauth_token(
    grant_type: str = Form(...),
    client_id: str = Form(...),
    client_secret: str = Form(...),
    scope: Optional[str] = Form(None)
):
    """
    OAuth 2.0 token endpoint for Client Credentials flow.
    
    Validates client credentials and issues access tokens.
    For ChatGPT Enterprise integration.
    """
    # Validate grant type
    if grant_type != "client_credentials":
        raise HTTPException(
            status_code=400,
            detail="unsupported_grant_type"
        )
    
    # Validate client credentials against Okta config
    if client_id != OKTA_CLIENT_ID or client_secret != OKTA_CLIENT_SECRET:
        raise HTTPException(
            status_code=401,
            detail="invalid_client"
        )
    
    # Generate access token
    access_token = secrets.token_urlsafe(32)
    
    # Return token response
    return {
        "access_token": access_token,
        "token_type": "Bearer",
        "expires_in": 3600,
        "scope": scope or ""
    }


# ==========================================
# OAuth Userinfo Endpoint
# ==========================================

@app.get("/oauth/userinfo")
async def oauth_userinfo(auth: dict = Depends(verify_token)):
    """OAuth userinfo endpoint - returns user info from validated token."""
    if not auth.get("authenticated"):
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # If token was already validated by verify_token, use that info
    if auth.get("method") == "oauth" and auth.get("token_info"):
        token_info = auth["token_info"]
        return {
            "sub": token_info.get("sub", "unknown"),
            "name": token_info.get("username", "ChatGPT Enterprise"),
            "email": token_info.get("username", "chatgpt@openai.com"),
            "email_verified": True
        }
    
    # Fallback for API key auth
    return {
        "sub": "api-key-user",
        "name": "API Key User",
        "email": "api@example.com",
        "email_verified": False
    }


# ==========================================
# Telephony Endpoint (No Authentication Required)
# ==========================================

@app.post("/telephony")
async def telephony_webhook(request: Request):
    """
    Simple telephony webhook endpoint that logs headers and body.
    No authentication required.
    """
    # Get all headers
    headers = dict(request.headers)
    
    # Get the raw body
    body = await request.body()
    
    # Try to parse as JSON, fallback to raw text
    try:
        body_json = await request.json()
        body_content = body_json
    except:
        body_content = body.decode('utf-8') if body else ""
    
    # Log everything
    print("=" * 70)
    print("TELEPHONY WEBHOOK RECEIVED")
    print("=" * 70)
    print("\n📞 HEADERS:")
    for header_name, header_value in headers.items():
        print(f"  {header_name}: {header_value}")
    
    print("\n📄 BODY:")
    if isinstance(body_content, dict):
        print(json.dumps(body_content, indent=2))
    else:
        print(body_content)
    print("=" * 70)
    print()
    
    # Return a simple success response
    return {
        "status": "received",
        "message": "Telephony webhook processed successfully",
        "headers_received": len(headers),
        "body_size": len(body)
    }


# ==========================================
# Root Endpoint
# ==========================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API information."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LangGraph Agent API</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            h1 { color: #333; }
            .endpoint { 
                background: #f5f5f5;
                padding: 10px;
                margin: 10px 0;
                border-radius: 5px;
            }
            a { color: #0066cc; }
        </style>
    </head>
    <body>
        <h1>🚀 LangGraph Agent API</h1>
        <p>OAuth-secured API for ChatGPT Enterprise integration</p>
        
        <h2>📚 Documentation</h2>
        <div class="endpoint">
            <a href="/docs">Interactive API Docs (Swagger UI)</a>
        </div>
        <div class="endpoint">
            <a href="/redoc">API Documentation (ReDoc)</a>
        </div>
        <div class="endpoint">
            <a href="/openapi.json">OpenAPI Specification</a>
        </div>
        
        <h2>🔐 OAuth Endpoints</h2>
        <div class="endpoint">
            <a href="/.well-known/openid-configuration">
                OpenID Configuration
            </a>
        </div>
        <div class="endpoint">
            <a href="/.well-known/oauth-authorization-server">
                OAuth Authorization Server
            </a>
        </div>
        
        <h2>🏥 System</h2>
        <div class="endpoint">
            <a href="/health">Health Check</a>
        </div>
    </body>
    </html>
    """


@app.get("/logo.png")
async def logo():
    """Serve a placeholder logo for ChatGPT plugin manifest."""
    # Return a redirect to a default image or serve a simple SVG
    # For now, return a simple text response
    return HTMLResponse(
        content='<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#4A90E2"/><text x="50" y="55" font-size="40" text-anchor="middle" fill="white">LG</text></svg>',  # noqa: E501
        media_type="image/svg+xml"
    )


@app.get("/legal", response_class=HTMLResponse)
async def legal_info():
    """Legal information endpoint for ChatGPT plugin manifest."""
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Legal Information - {PLUGIN_NAME} API</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }}
        </style>
    </head>
    <body>
        <h1>Legal Information</h1>
        <h2>Terms of Service</h2>
        <p>This API is provided as-is for authorized users only.</p>
        
        <h2>Privacy Policy</h2>
        <p>We do not store or share user data without consent.</p>
        
        <h2>Contact</h2>
        <p>Email: {CONTACT_EMAIL}</p>
    </body>
    </html>
    """


@app.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """
    Privacy policy endpoint for ChatGPT plugin compliance.
    Required by ChatGPT to inform users about data handling.
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Privacy Policy - {PLUGIN_NAME} API</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                line-height: 1.6;
            }}
            h1 {{ color: #333; }}
            h2 {{ color: #555; margin-top: 30px; }}
            .section {{ margin-bottom: 20px; }}
            .highlight {{ 
                background-color: #f0f8ff;
                padding: 15px;
                border-left: 4px solid #0066cc;
                margin: 20px 0;
            }}
        </style>
    </head>
    <body>
        <h1>Privacy Policy</h1>
        <p><strong>Last Updated:</strong> November 15, 2025</p>
        
        <div class="highlight">
            <strong>Summary:</strong> We prioritize your privacy. This API 
            processes requests in real-time and does not store conversation 
            data or personal information.
        </div>
        
        <div class="section">
            <h2>1. Information We Collect</h2>
            <p>When you use this API through ChatGPT or directly:</p>
            <ul>
                <li><strong>Query Data:</strong> The prompts and requests 
                you send to the LangGraph agent</li>
                <li><strong>Technical Data:</strong> API usage logs, 
                timestamps, and error logs for service reliability</li>
                <li><strong>Authentication Data:</strong> API keys or OAuth 
                tokens for access control</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>2. How We Use Your Information</h2>
            <p>Your information is used solely to:</p>
            <ul>
                <li>Process your requests and return agent responses</li>
                <li>Authenticate and authorize API access</li>
                <li>Monitor service health and performance</li>
                <li>Debug and improve the service</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>3. Data Storage and Retention</h2>
            <ul>
                <li><strong>Conversation Data:</strong> Not stored 
                permanently. Processed in real-time only.</li>
                <li><strong>Log Data:</strong> Technical logs retained for 
                30 days for debugging purposes</li>
                <li><strong>Authentication Tokens:</strong> Session tokens 
                expire after 1 hour</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>4. Data Sharing</h2>
            <p>We do not sell, trade, or share your data with third parties, 
            except:</p>
            <ul>
                <li><strong>LangGraph Service:</strong> Requests are 
                forwarded to the LangGraph agent backend for processing</li>
                <li><strong>OAuth Provider:</strong> Authentication 
                credentials validated with Okta when using OAuth</li>
                <li><strong>Legal Requirements:</strong> If required by law 
                or to protect our rights</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>5. Security</h2>
            <p>We implement security measures including:</p>
            <ul>
                <li>HTTPS encryption for all API communications</li>
                <li>OAuth 2.0 and API Key authentication</li>
                <li>Regular security updates and monitoring</li>
                <li>Access control and rate limiting</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>6. Your Rights</h2>
            <p>You have the right to:</p>
            <ul>
                <li>Request information about data we process</li>
                <li>Request deletion of your API keys or access tokens</li>
                <li>Opt-out of using the service at any time</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>7. ChatGPT Integration</h2>
            <p>When using this API through ChatGPT:</p>
            <ul>
                <li>ChatGPT's own privacy policy also applies</li>
                <li>OpenAI may process and store conversation data 
                according to their policies</li>
                <li>We only receive the specific requests sent to our API</li>
            </ul>
        </div>
        
        <div class="section">
            <h2>8. Children's Privacy</h2>
            <p>This service is not intended for users under 13 years of age. 
            We do not knowingly collect information from children.</p>
        </div>
        
        <div class="section">
            <h2>9. Changes to Privacy Policy</h2>
            <p>We may update this privacy policy from time to time. Changes 
            will be posted on this page with an updated revision date.</p>
        </div>
        
        <div class="section">
            <h2>10. Contact Us</h2>
            <p>If you have questions about this privacy policy or our data 
            practices:</p>
            <p><strong>Email:</strong> {CONTACT_EMAIL}</p>
            <p><strong>API Documentation:</strong> 
            <a href="{SERVER_BASE_URL}/docs">{SERVER_BASE_URL}/docs</a></p>
        </div>
        
        <hr style="margin: 40px 0;">
        <p style="text-align: center; color: #666;">
            <a href="/">Home</a> | 
            <a href="/legal">Legal Information</a> | 
            <a href="/docs">API Documentation</a>
        </p>
    </body>
    </html>
    """


# ==========================================
# API Endpoints
# ==========================================

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    tags=["System"],
    description="Check API health status."
)
async def health_check():
    """Check API health status."""
    return {
        "status": "healthy",
        "service": "LangGraph Agent API",
        "version": "1.0.0",
        "auth_enabled": OAUTH_ENABLED
    }


@app.get(
    "/test",
    summary="Test Connection",
    description="Simple test endpoint that returns a success message. "
                "Use this to verify connectivity between ChatGPT "
                "Enterprise and your API.",
    tags=["Testing"],
    operation_id="test_connection"
)
async def test_endpoint():
    """Test endpoint for verifying connectivity."""
    from datetime import datetime
    return {
        "status": "success",
        "message": "Connection to LangGraph Agent API is working!",
        "timestamp": datetime.now().isoformat(),
        "server": SERVER_BASE_URL,
        "version": "1.0.0"
    }


@app.post(
    "/invoke",
    response_model=InvokeResponse,
    summary="Invoke Agent",
    description="Invoke the LangGraph agent with a prompt",
    tags=["Agent"]
)
async def invoke_agent(
    request: InvokeRequest,
    auth: dict = Depends(verify_token)
):
    """Invoke the LangGraph agent with a prompt."""
    try:
        # Extract userId from token if available
        user_id = None
        if auth.get("token_info"):
            # Try common claims for user identification
            token_info = auth["token_info"]
            user_id = (
                token_info.get("sub") or
                token_info.get("uid") or
                token_info.get("username") or
                token_info.get("email") or
                token_info.get("client_id")
            )
            print(f"DEBUG: Extracted userId from token: {user_id}")
        elif auth.get("method") == "api_key":
            print("DEBUG: API key auth - no userId available")
        else:
            print("DEBUG: No token_info available for userId extraction")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Build input with messages, userId, and conversationId
            payload = {
                "assistant_id": request.assistant_id,
                "input": {
                    "messages": [
                        {
                            "role": "user",
                            "content": request.prompt
                        }
                    ]
                }
            }
            
            # Add userId to input if available
            if user_id:
                payload["input"]["userId"] = user_id
            
            # Add conversationId to input if available
            if request.conversationId:
                payload["input"]["conversationId"] = request.conversationId
            
            # Add thread_id to config for conversation persistence
            if request.thread_id:
                payload["config"] = {
                    "configurable": {
                        "thread_id": request.thread_id
                    }
                }
            
            print(
                f"DEBUG: Payload to supervisor - "
                f"userId: {user_id}, "
                f"conversationId: {request.conversationId}, "
                f"thread_id: {request.thread_id}"
            )
            
            # Use /runs/stream endpoint which returns SSE format
            stream_url = f"{LANGGRAPH_BASE_URL}/runs/stream"
            print(f"DEBUG: Calling {stream_url} with payload: {payload}")
            
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
                                    final_messages = data_obj["messages"]
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
                                    final_messages = data_obj["messages"]
                            except json.JSONDecodeError:
                                pass
                        current_event = None
                        current_data = []
                
                # Debug: Print final messages structure
                messages_json = json.dumps(final_messages, indent=2)
                print(f"DEBUG: Final messages: {messages_json}")
                
                # Extract the final assistant response
                output_text = "Task completed"
                for msg in reversed(final_messages):
                    # Try different message structures
                    is_assistant = (
                        msg.get("role") == "assistant" or
                        msg.get("type") == "ai"
                    )
                    if is_assistant:
                        # Check for content directly or in message field
                        content = None
                        if "content" in msg:
                            content = msg["content"]
                        elif "message" in msg and isinstance(
                            msg["message"], dict
                        ):
                            content = msg["message"].get("content", "")
                        
                        if content and not str(content).startswith("{"):
                            output_text = content
                            break
                
                return {
                    "run_id": run_id or "unknown",
                    "thread_id": request.thread_id or "auto-generated",
                    "output": {
                        "content": output_text,
                        "all_messages": final_messages
                    },
                    "status": "success"
                }
            
    except httpx.HTTPError as e:
        import traceback
        error_detail = f"HTTP error invoking agent: {str(e)}"
        print(f"ERROR: {error_detail}")
        print(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    except Exception as e:
        import traceback
        error_detail = f"Error invoking agent: {str(e)}"
        print(f"ERROR: {error_detail}")
        print(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@app.post(
    "/stream",
    response_model=StreamResponse,
    summary="Stream Agent Response",
    description="Stream responses from the LangGraph agent",
    tags=["Agent"]
)
async def stream_agent(
    request: StreamRequest,
    auth: dict = Depends(verify_token)
):
    """Stream responses from the LangGraph agent."""
    try:
        # Extract userId from token if available
        user_id = None
        if auth.get("token_info"):
            token_info = auth["token_info"]
            user_id = (
                token_info.get("sub") or
                token_info.get("uid") or
                token_info.get("username") or
                token_info.get("email") or
                token_info.get("client_id")
            )
            print(f"DEBUG: Extracted userId from token: {user_id}")
        elif auth.get("method") == "api_key":
            print("DEBUG: API key auth - no userId available")
        else:
            print("DEBUG: No token_info available for userId extraction")
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Build input with messages, userId, and conversationId
            payload = {
                "assistant_id": request.assistant_id,
                "input": {
                    "messages": [
                        {
                            "type": "human",
                            "content": request.prompt
                        }
                    ]
                },
                "stream_mode": ["messages"]
            }
            
            # Add userId to input if available
            if user_id:
                payload["input"]["userId"] = user_id
            
            # Add conversationId to input if available
            if request.conversationId:
                payload["input"]["conversationId"] = request.conversationId
            
            # Add thread_id to config for conversation persistence
            if request.thread_id:
                payload["config"] = {
                    "configurable": {
                        "thread_id": request.thread_id
                    }
                }
            
            print(
                f"DEBUG: Payload to supervisor - "
                f"userId: {user_id}, "
                f"conversationId: {request.conversationId}, "
                f"thread_id: {request.thread_id}"
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
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )
    except Exception as e:
        import traceback
        error_detail = f"Error streaming from agent: {str(e)}"
        print(f"ERROR: {error_detail}")
        print(f"Traceback:\n{traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=error_detail
        )


@app.get(
    "/agents",
    summary="List Agents",
    description="Get available agents",
    tags=["System"]
)
async def list_agents(auth: dict = Depends(verify_token)):
    """List available agents."""
    return {
        "agents": [
            {
                "id": "agent",
                "name": "General Agent",
                "description": "General purpose LangGraph agent"
            },
            {
                "id": "health",
                "name": "Health Agent",
                "description": "System health monitoring agent"
            }
        ]
    }

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 70)
    print("OAuth-Compliant OpenAPI Server for ChatGPT Enterprise")
    print("=" * 70)
    print(f"Server URL: {SERVER_BASE_URL}")
    print(f"OpenAPI Spec: {SERVER_BASE_URL}/openapi.json")
    print(f"API Docs: {SERVER_BASE_URL}/docs")
    print(f"OAuth Enabled: {OAUTH_ENABLED}")
    print(f"OAuth Provider: {OAUTH_PROVIDER}")
    print()
    print("ChatGPT Enterprise Endpoints:")
    print(f"  AI Plugin Manifest: {SERVER_BASE_URL}/.well-known/ai-plugin.json")  # noqa: E501
    print(f"  OpenID Config: {SERVER_BASE_URL}/.well-known/openid-configuration")  # noqa: E501
    print(f"  OAuth Server: {SERVER_BASE_URL}/.well-known/oauth-authorization-server")  # noqa: E501
    print(f"  JWKS: {SERVER_BASE_URL}/.well-known/jwks.json")
    print()
    print("⚠️  IMPORTANT: Use this URL in ChatGPT Enterprise:")
    print(f"  {SERVER_BASE_URL}/.well-known/ai-plugin.json")
    print("=" * 70)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
