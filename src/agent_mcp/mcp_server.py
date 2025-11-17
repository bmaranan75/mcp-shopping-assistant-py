"""
FastMCP Server for LangGraph Agent Integration.

ChatGPT Enterprise compliant MCP server.
Integrates with LangGraph CLI server using standard API endpoints.
Supports OAuth 2.0 authentication for secure access.
"""

import httpx
import json
import os
from typing import Any, Dict, Optional
from fastmcp import FastMCP, Context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastMCP server with metadata for ChatGPT Enterprise
mcp = FastMCP("LangGraph Agent Server")

# LangGraph agent base URL
LANGGRAPH_BASE_URL = os.getenv("LANGGRAPH_BASE_URL", "http://localhost:2024")


@mcp.tool()
async def invoke_agent(
    prompt: str,
    assistant_id: str = "agent",
    thread_id: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Invoke the LangGraph agent with a prompt using the /runs API.
    
    Args:
        prompt: The user prompt/query to send to the agent
        assistant_id: The assistant/agent ID to invoke (default: "agent")
        thread_id: Optional thread ID for conversation continuity
        ctx: MCP context for logging and progress reporting
    
    Returns:
        Agent response with output and metadata
    """
    if ctx:
        msg = f"Invoking LangGraph agent '{assistant_id}': {prompt[:50]}..."
        await ctx.info(msg)
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create run using LangGraph API with streaming
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
            
            if ctx:
                await ctx.info("Invoking agent with streaming API")
            
            # Use streaming endpoint to get results
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
                        # Try to parse chunk to extract metadata
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, list) and len(data) > 0:
                                # Extract run_id and thread_id from metadata
                                if "run_id" in data[0]:
                                    run_id = data[0]["run_id"]
                                if "thread_id" in data[0]:
                                    thread_id_result = data[0]["thread_id"]
                                # Store the last complete output
                                final_output = data
                        except json.JSONDecodeError:
                            pass
                
                if ctx:
                    await ctx.info("Agent invocation completed successfully")
                
                return {
                    "run_id": run_id or "unknown",
                    "thread_id": thread_id_result or "unknown",
                    "output": final_output or {"messages": chunks},
                    "status": "success"
                }
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error invoking agent: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error invoking agent: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def stream_agent(
    prompt: str,
    assistant_id: str = "agent",
    thread_id: Optional[str] = None,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Stream responses from the LangGraph agent using /runs/stream API.
    
    Args:
        prompt: The user prompt/query to send to the agent
        assistant_id: The assistant/agent ID to invoke (default: "agent")
        thread_id: Optional thread ID for conversation continuity
        ctx: MCP context for progress reporting
    
    Returns:
        Streamed agent responses
    """
    if ctx:
        await ctx.info("Starting stream from LangGraph agent...")
    
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
                        if ctx:
                            await ctx.report_progress(len(chunks), None)
                
                return {
                    "output": "".join(chunks),
                    "chunks_received": len(chunks),
                    "status": "success"
                }
                
    except httpx.HTTPError as e:
        error_msg = f"HTTP error streaming from agent: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error streaming from agent: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def check_system_health(
    assistant_id: str = "health",
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Check comprehensive system health using the health agent.
    
    Uses LangGraph API to invoke the health agent for detailed diagnostics
    including agent status, dependencies, and performance metrics.
    
    Args:
        assistant_id: The health assistant ID (default: "health")
        ctx: MCP context for logging
    
    Returns:
        Comprehensive health status
    """
    if ctx:
        await ctx.info("Checking comprehensive system health...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Create health check run using streaming API
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
            
            # Use streaming endpoint to get results
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
                        # Try to parse chunk to extract metadata
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, list) and len(data) > 0:
                                # Extract run_id from metadata
                                if "run_id" in data[0]:
                                    run_id = data[0]["run_id"]
                                # Store the last complete output
                                final_output = data
                        except json.JSONDecodeError:
                            pass
                
                return {
                    "health_check": final_output or {"messages": chunks},
                    "run_id": run_id or "unknown",
                    "status": "success"
                }
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error checking health: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error checking health: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def check_agent_status(
    agent_name: str,
    assistant_id: str = "health",
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Check the status of a specific agent.
    
    Args:
        agent_name: Name of the agent to check (e.g., "supervisor", "shopping")
        assistant_id: The health assistant ID (default: "health")
        ctx: MCP context for logging
    
    Returns:
        Specific agent health status
    """
    if ctx:
        await ctx.info(f"Checking status of {agent_name} agent...")
    
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
            
            # Use streaming endpoint to get results
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
                        # Try to parse chunk to extract metadata
                        try:
                            data = json.loads(chunk)
                            if isinstance(data, list) and len(data) > 0:
                                # Extract run_id from metadata
                                if "run_id" in data[0]:
                                    run_id = data[0]["run_id"]
                                # Store the last complete output
                                final_output = data
                        except json.JSONDecodeError:
                            pass
                
                return {
                    "agent": agent_name,
                    "status_check": final_output or {"messages": chunks},
                    "run_id": run_id or "unknown",
                    "status": "success"
                }
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error checking agent status: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error checking agent status: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def get_thread_state(
    thread_id: str,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    Get the current state of a conversation thread.
    
    Args:
        thread_id: The thread ID to query
        ctx: MCP context for logging
    
    Returns:
        Current thread state
    """
    if ctx:
        await ctx.info(f"Fetching state for thread: {thread_id}")
    
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
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error fetching state: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error fetching state: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.tool()
async def list_threads(
    limit: int = 10,
    ctx: Context = None
) -> Dict[str, Any]:
    """
    List available conversation threads.
    
    Args:
        limit: Maximum number of threads to return (default: 10)
        ctx: MCP context for logging
    
    Returns:
        List of threads
    """
    if ctx:
        await ctx.info(f"Listing threads (limit: {limit})...")
    
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
            
    except httpx.HTTPError as e:
        error_msg = f"HTTP error listing threads: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }
    except Exception as e:
        error_msg = f"Error listing threads: {str(e)}"
        if ctx:
            await ctx.error(error_msg)
        return {
            "error": error_msg,
            "status": "failed"
        }


@mcp.resource("agent://health/basic")
async def basic_health() -> str:
    """
    Basic health check using LangGraph CLI /ok endpoint.
    
    This is the only custom HTTP endpoint available in LangGraph CLI.
    Returns simple uptime status.
    
    Returns:
        Basic health status
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{LANGGRAPH_BASE_URL}/ok")
            response.raise_for_status()
            data = response.json()
            if data.get("ok"):
                return "Agent is online and responding"
            else:
                return "Agent returned unexpected status"
    except Exception as e:
        return f"Agent health check failed: {str(e)}"


@mcp.resource("agent://info")
async def agent_info() -> Dict[str, Any]:
    """
    Get information about the LangGraph agent capabilities.
    
    Returns:
        Agent metadata and capabilities
    """
    return {
        "name": "LangGraph Agent",
        "base_url": LANGGRAPH_BASE_URL,
        "api_version": "LangGraph CLI",
        "endpoints": {
            "basic_health": "/ok",
            "runs": "/runs",
            "stream": "/runs/stream",
            "threads": "/threads",
            "thread_state": "/threads/{thread_id}/state"
        },
        "tools": [
            "invoke_agent: Execute agent via /runs API",
            "stream_agent: Stream agent responses",
            "check_system_health: Comprehensive health via health agent",
            "check_agent_status: Check specific agent status",
            "get_thread_state: Get conversation thread state",
            "list_threads: List available threads"
        ],
        "protocol_version": "2025-06-18",
        "integration": "FastMCP for ChatGPT Enterprise"
    }


@mcp.prompt()
def agent_query_prompt(query: str) -> str:
    """
    Generate a formatted prompt for querying the LangGraph agent.
    
    Args:
        query: The user's query
    
    Returns:
        Formatted prompt
    """
    return f"""Please process the following query using the LangGraph agent:

Query: {query}

Provide a comprehensive response based on the agent's capabilities."""


if __name__ == "__main__":
    import uvicorn
    from starlette.applications import Starlette
    from starlette.responses import JSONResponse
    from starlette.middleware.cors import CORSMiddleware
    from starlette.middleware import Middleware
    from starlette.routing import Route, Mount
    from oauth import (
        OAuthConfig,
        OAuthProvider,
        OktaOAuthProvider,
        APIKeyAuth,
        AuthMiddleware,
        create_auth_routes,
        get_session_middleware
    )
    
    # Initialize OAuth configuration
    oauth_config = OAuthConfig()
    
    # Check if OAuth is enabled and properly configured
    if oauth_config.auth_enabled and not oauth_config.is_valid():
        print("ERROR: OAuth is enabled but not properly configured!")
        provider = oauth_config.oauth_provider
        
        if provider == "google":
            print("Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.")
        elif provider == "okta":
            print("Please set OKTA_DOMAIN, OKTA_CLIENT_ID, and OKTA_CLIENT_SECRET.")
        else:
            print(f"Unknown OAuth provider: {provider}")
            print("Set OAUTH_PROVIDER to 'google' or 'okta'")
        
        print("Or disable OAuth by setting OAUTH_ENABLED=false")
        exit(1)
    
    # Create health check handler
    async def health_check(request):
        """Simple health check endpoint for test UI."""
        return JSONResponse({
            "status": "ok",
            "service": "MCP Server",
            "auth_enabled": oauth_config.auth_enabled,
            "auth_provider": oauth_config.oauth_provider if oauth_config.auth_enabled else None,
            "auth_configured": oauth_config.is_valid()
        })
    
    # REST API endpoints for web UI integration
    async def api_invoke_agent(request):
        """REST endpoint to invoke agent via MCP server."""
        try:
            # Debug: Check session
            user = {}
            if "session" in request.scope:
                user = request.session.get('user', {})
                print(f"[DEBUG] Session user: {user}")
            else:
                print("[DEBUG] No session in request scope")
            
            data = await request.json()
            prompt = data.get("prompt")
            assistant_id = data.get("assistant_id", "agent")
            thread_id = data.get("thread_id")
            
            if not prompt:
                return JSONResponse(
                    {"error": "Missing 'prompt' in request body"},
                    status_code=400
                )
            
            print(f"[API] Invoking agent '{assistant_id}' with prompt: {prompt[:50]}...")
            
            # Call the MCP tool
            result = await invoke_agent(
                prompt=prompt,
                assistant_id=assistant_id,
                thread_id=thread_id,
                ctx=None
            )
            
            print(f"[API] Agent invocation result: {result.get('status')}")
            
            return JSONResponse(result)
        except Exception as e:
            print(f"[API ERROR] {str(e)}")
            return JSONResponse(
                {"error": str(e), "status": "failed"},
                status_code=500
            )
    
    async def api_stream_agent(request):
        """REST endpoint to stream agent responses via MCP server."""
        from starlette.responses import StreamingResponse
        
        try:
            data = await request.json()
            prompt = data.get("prompt")
            assistant_id = data.get("assistant_id", "agent")
            thread_id = data.get("thread_id")
            
            if not prompt:
                return JSONResponse(
                    {"error": "Missing 'prompt' in request body"},
                    status_code=400
                )
            
            # Stream directly from LangGraph via MCP server
            async def stream_generator():
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
                        "stream_mode": ["messages"]
                    }
                    
                    if thread_id:
                        payload["thread_id"] = thread_id
                    
                    async with client.stream(
                        "POST",
                        f"{LANGGRAPH_BASE_URL}/runs/stream",
                        json=payload
                    ) as response:
                        response.raise_for_status()
                        async for chunk in response.aiter_bytes():
                            yield chunk
            
            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream"
            )
        except Exception as e:
            return JSONResponse(
                {"error": str(e), "status": "failed"},
                status_code=500
            )
    
    # Get the HTTP app from FastMCP (modern non-SSE alternative)
    # Use http_app instead of deprecated sse_app (as of FastMCP 2.3.2)
    http_app = mcp.http_app()
    
    # Create routes
    routes = [
        Route("/health", health_check),
        Route("/api/invoke", api_invoke_agent, methods=["POST"]),
        Route("/api/stream", api_stream_agent, methods=["POST"]),
        Mount("/sse", app=http_app),  # Keep /sse path for backward compatibility
    ]
    
    # Add OAuth routes if enabled
    if oauth_config.auth_enabled:
        # Select OAuth provider based on configuration
        if oauth_config.oauth_provider == "okta":
            oauth_provider = OktaOAuthProvider(oauth_config)
        else:  # Default to Google
            oauth_provider = OAuthProvider(oauth_config)
        
        auth_routes = create_auth_routes(oauth_provider)
        routes.extend(auth_routes)
    
    # Build middleware stack
    middleware = []
    
    # Add session middleware if OAuth is enabled
    if oauth_config.auth_enabled:
        middleware.append(get_session_middleware(oauth_config.secret_key))
    
    # Create main app with middleware (without CORS yet)
    app = Starlette(routes=routes, middleware=middleware)
    
    # Wrap with auth middleware if OAuth is enabled
    # Note: Must wrap AFTER session middleware is in the stack
    if oauth_config.auth_enabled:
        api_key_auth = APIKeyAuth(oauth_config)
        app = AuthMiddleware(app, oauth_config, api_key_auth)
    
    # Add CORS middleware as the outermost layer
    # This ensures CORS headers are added to all responses, including auth errors
    final_app = CORSMiddleware(
        app,
        allow_origins=["*"],  # Allow all origins for development
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Run server
    print("=" * 60)
    print("Starting MCP Server")
    print("=" * 60)
    print(f"Server URL: http://0.0.0.0:8000")
    print(f"Health endpoint: http://0.0.0.0:8000/health")
    print(f"SSE endpoint: http://0.0.0.0:8000/sse")
    print(f"Auth enabled: {oauth_config.auth_enabled}")
    
    if oauth_config.auth_enabled:
        print(f"Auth provider: {oauth_config.oauth_provider}")
        print(f"\nAuthentication Endpoints:")
        print(f"  Login: http://0.0.0.0:8000/auth/login")
        print(f"  Callback: http://0.0.0.0:8000/auth/callback")
        print(f"  Logout: http://0.0.0.0:8000/auth/logout")
        print(f"  Status: http://0.0.0.0:8000/auth/status")
        print(f"\nAPI Key Authentication:")
        print(f"  Use header: X-API-Key: <your-api-key>")
        if oauth_config.api_keys:
            print(f"  {len(oauth_config.api_keys)} API key(s) configured")
    
    print("=" * 60)
    
    uvicorn.run(final_app, host="0.0.0.0", port=8000)
