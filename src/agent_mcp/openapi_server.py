"""
OpenAPI-compliant REST API server for ChatGPT Enterprise integration.

This server wraps the MCP functionality in a standard REST API with OpenAPI
specification, making it compatible with ChatGPT Actions.
"""

import json
import os
import httpx
import secrets
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from fastapi import FastAPI, HTTPException, Header, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse, HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# LangGraph agent base URL
LANGGRAPH_BASE_URL = os.getenv("LANGGRAPH_BASE_URL", "http://localhost:2024")

# OAuth Configuration
OAUTH_ENABLED = os.getenv("OAUTH_ENABLED", "true").lower() == "true"
OAUTH_PROVIDER = os.getenv("OAUTH_PROVIDER", "okta")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
API_KEYS = os.getenv("API_KEYS", "").split(",") if os.getenv("API_KEYS") else []

# Server base URL (for OAuth callbacks)
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8001")

# Create FastAPI app with metadata for OpenAPI
app = FastAPI(
    title="LangGraph Agent API",
    description="ChatGPT-compatible API for interacting with LangGraph agents via MCP",
    version="1.0.0",
    servers=[
        {
            "url": "http://localhost:8001",
            "description": "Development server"
        },
        {
            "url": "https://your-domain.com",
            "description": "Production server"
        }
    ],
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response Models
class InvokeRequest(BaseModel):
    """Request model for invoking the agent."""
    prompt: str = Field(
        ...,
        description="The user prompt/query to send to the agent",
        example="What is the weather like today?"
    )
    assistant_id: str = Field(
        default="agent",
        description="The assistant/agent ID to invoke",
        example="agent"
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID for conversation continuity",
        example="thread-abc-123"
    )


class InvokeResponse(BaseModel):
    """Response model for agent invocation."""
    run_id: str = Field(..., description="The run ID for this invocation")
    thread_id: str = Field(..., description="The thread ID for conversation tracking")
    output: Dict[str, Any] = Field(..., description="The agent's response output")
    status: str = Field(..., description="Status of the invocation", example="success")


class StreamRequest(BaseModel):
    """Request model for streaming agent responses."""
    prompt: str = Field(
        ...,
        description="The user prompt/query to send to the agent",
        example="Explain quantum computing in simple terms"
    )
    assistant_id: str = Field(
        default="agent",
        description="The assistant/agent ID to invoke",
        example="agent"
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Optional thread ID for conversation continuity",
        example="thread-xyz-789"
    )


class StreamResponse(BaseModel):
    """Response model for streaming."""
    output: str = Field(..., description="The streamed content")
    chunks_received: int = Field(..., description="Number of chunks received")
    status: str = Field(..., description="Status of the stream", example="success")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., example="healthy")
    service: str = Field(..., example="LangGraph Agent API")
    version: str = Field(..., example="1.0.0")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error message")
    status: str = Field(default="failed", example="failed")
    details: Optional[str] = Field(None, description="Additional error details")


# Authentication (optional)
async def verify_api_key(x_api_key: Optional[str] = Header(None)):
    """Verify API key if configured."""
    api_keys = os.getenv("API_KEYS", "").split(",")
    
    # If no API keys configured, skip verification
    if not api_keys or api_keys == [""]:
        return True
    
    if not x_api_key or x_api_key not in api_keys:
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key"
        )
    
    return True


# API Endpoints
@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Check if the API is running and healthy",
    tags=["System"]
)
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "LangGraph Agent API",
        "version": "1.0.0"
    }


@app.post(
    "/invoke",
    response_model=InvokeResponse,
    summary="Invoke Agent",
    description="Invoke the LangGraph agent with a prompt and wait for completion",
    responses={
        200: {"description": "Agent invocation successful"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    tags=["Agent"]
)
async def invoke_agent(
    request: InvokeRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Invoke the LangGraph agent with a prompt.
    
    This endpoint sends a prompt to the agent, waits for completion,
    and returns the full response.
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            # Create run using LangGraph API with streaming
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
                "stream_mode": ["values"]
            }
            
            if request.thread_id:
                payload["thread_id"] = request.thread_id
            
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
                
                return {
                    "run_id": run_id or "unknown",
                    "thread_id": thread_id_result or "unknown",
                    "output": final_output or {"messages": chunks},
                    "status": "success"
                }
            
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=500,
            detail=f"HTTP error invoking agent: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error invoking agent: {str(e)}"
        )


@app.post(
    "/stream",
    response_model=StreamResponse,
    summary="Stream Agent Response",
    description="Stream responses from the LangGraph agent in real-time",
    responses={
        200: {"description": "Streaming successful"},
        400: {"description": "Invalid request"},
        500: {"description": "Internal server error"},
    },
    tags=["Agent"]
)
async def stream_agent(
    request: StreamRequest,
    authenticated: bool = Depends(verify_api_key)
):
    """
    Stream responses from the LangGraph agent.
    
    This endpoint streams the agent's response as it's generated,
    useful for long-running queries.
    """
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
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
            
            if request.thread_id:
                payload["thread_id"] = request.thread_id
            
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
        raise HTTPException(
            status_code=500,
            detail=f"HTTP error streaming from agent: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error streaming from agent: {str(e)}"
        )


# Optional: List available agents
@app.get(
    "/agents",
    summary="List Agents",
    description="Get a list of available agents",
    tags=["System"]
)
async def list_agents(authenticated: bool = Depends(verify_api_key)):
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
    
    print("=" * 60)
    print("Starting OpenAPI-compliant Server for ChatGPT Integration")
    print("=" * 60)
    print(f"Server URL: http://0.0.0.0:8001")
    print(f"OpenAPI Spec: http://0.0.0.0:8001/openapi.json")
    print(f"API Docs: http://0.0.0.0:8001/docs")
    print(f"ReDoc: http://0.0.0.0:8001/redoc")
    print("=" * 60)
    
    uvicorn.run(app, host="0.0.0.0", port=8001)
