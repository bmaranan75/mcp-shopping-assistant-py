# MCP Server for LangGraph Agent

FastMCP-based Model Context Protocol server for ChatGPT Enterprise integration with LangGraph agent.

## 🎉 Quick Start

**The fastest way to get started:**

```bash
./start.sh
```

This will:

1. Check if your LangGraph agent is running on port 2024
2. Start the MCP server on port 8000
3. Start the test UI on port 3005
4. Open http://localhost:3005 in your browser

## Overview

This MCP server provides a standardized interface to interact with a LangGraph agent deployed on port 2024, compliant with ChatGPT Enterprise integration requirements.

### ✨ Latest Updates

**January 2025 - LangGraph CLI Integration**

- ✅ Refactored to use LangGraph CLI API architecture
- ✅ Updated to `/runs`, `/runs/stream`, `/ok` endpoints
- ✅ Changed message format to `{"type": "human"}`
- ✅ Added 3 new tools: health check, agent status, thread listing
- ✅ Fixed all async operations (no more blocking calls)
- ✅ Updated web UI to match new API structure

See `REFACTORING_SUMMARY.md` for detailed changes.

## Features

- ✅ **MCP Protocol 2025-06-18** compliant
- ✅ **ChatGPT Enterprise** compatible (SSE transport)
- ✅ **OAuth 2.0 Authentication** - Google OAuth and API key support
- ✅ **FastMCP 2.13.0+** framework for production-ready deployment
- ✅ **LangGraph CLI API** integration
- ✅ **6 Tools**: invoke_agent, stream_agent, check_system_health, check_agent_status, get_thread_state, list_threads
- ✅ **2 Resources**: Agent health check and server info
- ✅ **Prompts**: Formatted agent queries
- ✅ **Web Test UI**: Interactive testing interface on port 3005
- ✅ **Secure by Default**: Optional authentication for production deployments

## Installation

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Configure environment (optional):

```bash
# Copy example configuration
cp .env.example .env

# Edit .env with your settings
# For development without auth:
OAUTH_ENABLED=false

# For production with auth:
OAUTH_ENABLED=true
GOOGLE_CLIENT_ID=your-client-id
GOOGLE_CLIENT_SECRET=your-client-secret
API_KEYS=your-api-key-1,your-api-key-2
```

3. Generate credentials (if using OAuth):

```bash
python generate_credentials.py
```

See [OAUTH_SETUP.md](OAUTH_SETUP.md) for detailed authentication setup.

## Usage

### Option 1: Quick Start Script (Recommended)

```bash
./start.sh
```

### Option 2: Manual Start

**Start MCP Server:**

```bash
python src/agent_mcp/mcp_server.py
```

**Start Test UI (optional):**

```bash
cd web_ui && python server.py
```

### Option 3: Using FastMCP CLI

```bash
python -m agent_mcp.mcp_server
```

Or using FastMCP CLI:

```bash
fastmcp run src/agent_mcp/mcp_server.py
```

**For local development (STDIO):**

```bash
fastmcp dev src/agent_mcp/mcp_server.py
```

**Custom transport:**

```python
from agent_mcp.mcp_server import mcp

# HTTP transport
mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")

# SSE transport (for ChatGPT Enterprise)
mcp.run(transport="sse", host="0.0.0.0", port=8000)
```

### Available Tools

#### 1. `invoke_agent`

Execute a single invocation of the LangGraph agent.

```python
{
    "prompt": "What is the capital of France?",
    "thread_id": "optional-thread-id"
}
```

#### 2. `stream_agent`

Stream responses from the LangGraph agent.

```python
{
    "prompt": "Tell me a story",
    "thread_id": "optional-thread-id"
}
```

#### 3. `get_agent_state`

Retrieve the current state of a conversation thread.

```python
{
    "thread_id": "thread-id-to-query"
}
```

## Authentication

The MCP server supports three authentication methods for production deployments:

### 1. OAuth 2.0 (Google or Okta)

Enable user-based authentication with your preferred identity provider:

**Google OAuth:**

```bash
# .env configuration
OAUTH_ENABLED=true
OAUTH_PROVIDER=google
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
```

**Okta OAuth:**

```bash
# .env configuration
OAUTH_ENABLED=true
OAUTH_PROVIDER=okta
OKTA_DOMAIN=your-domain.okta.com
OKTA_CLIENT_ID=your-okta-client-id
OKTA_CLIENT_SECRET=your-okta-client-secret
```

**OAuth Endpoints:**

- `GET /auth/login` - Initiate OAuth flow
- `GET /auth/callback` - OAuth callback handler
- `GET /auth/logout` - Logout
- `GET /auth/status` - Check authentication status

**Quick Start Guides:**

- [Google OAuth Setup](OAUTH_SETUP.md#setup-google-oauth)
- [Okta OAuth Setup](OKTA_QUICKSTART.md)

### 2. API Key Authentication

Use API keys for service-to-service authentication:

```bash
# Generate API keys
python generate_credentials.py

# Add to .env
API_KEYS=key1,key2,key3
```

**Using API Keys:**

```bash
# cURL
curl -H "X-API-Key: your-api-key" http://localhost:8000/sse

# Python
headers = {"X-API-Key": "your-api-key"}
```

### Testing Authentication

```bash
# Test OAuth setup
python test_oauth.py

# Or test manually
curl http://localhost:8000/health  # Public endpoint
curl -H "X-API-Key: your-key" http://localhost:8000/sse  # Protected
```

**For detailed setup instructions, see [OAUTH_SETUP.md](OAUTH_SETUP.md)**

### Resources

- `agent://health` - Agent health check
- `agent://info` - Agent capabilities and metadata

### Prompts

- `agent_query_prompt` - Format queries for the agent

## ChatGPT Enterprise Integration

This server is designed for ChatGPT Enterprise integration with:

1. **SSE Transport**: Default transport for real-time streaming
2. **MCP Protocol 2025-06-18**: Latest stable protocol version
3. **Proper Tool Schemas**: Auto-generated from Python type hints
4. **Context Support**: Logging and progress reporting
5. **Error Handling**: Comprehensive error responses

### ChatGPT Configuration

Add to your ChatGPT Enterprise MCP configuration:

```json
{
  "mcpServers": {
    "langgraph-agent": {
      "url": "http://your-server:8000/sse",
      "transport": "sse"
    }
  }
}
```

## Testing

### Web UI Test Tool

We provide a beautiful web-based UI to test your MCP server and LangGraph agent:

```bash
# Start the test UI server
cd web_ui
python server.py
```

Then open http://localhost:3005 in your browser to:

- Test MCP server connectivity
- Test LangGraph agent connectivity
- Invoke agent with custom prompts
- Stream responses in real-time
- View activity logs

See `web_ui/README.md` for details.

### Unit Tests

Run tests:

```bash
pytest tests/test_mcp_server.py -v
```

Run all tests:

```bash
pytest
```

## Development

### Project Structure

```
agent-mcp-py/
├── src/
│   └── agent_mcp/
│       ├── __init__.py
│       └── mcp_server.py      # FastMCP server implementation
├── tests/
│   ├── test_mcp_server.py     # MCP server tests
│   └── test_*.py              # Other tests
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
└── README.md
```

### Adding New Tools

```python
from fastmcp import Context

@mcp.tool()
async def my_tool(param: str, ctx: Context = None) -> dict:
    """Tool description for ChatGPT."""
    if ctx:
        await ctx.info(f"Processing: {param}")

    # Your logic here
    return {"result": "success"}
```

### Adding Resources

```python
@mcp.resource("custom://resource")
async def my_resource() -> str:
    """Resource description."""
    return "Resource content"
```

## Architecture

```
┌─────────────────┐
│  ChatGPT        │
│  Enterprise     │
└────────┬────────┘
         │ MCP/SSE
         │
┌────────▼────────┐
│  FastMCP        │
│  Server         │
│  (Port 8000)    │
└────────┬────────┘
         │ HTTP
         │
┌────────▼────────┐
│  LangGraph      │
│  Agent          │
│  (Port 2024)    │
└─────────────────┘
```

## Production Deployment

### With Authentication

```python
from fastmcp.server.auth.providers.google import GoogleProvider

auth = GoogleProvider(
    client_id="your-client-id",
    client_secret="your-client-secret",
    base_url="https://your-domain.com"
)

mcp = FastMCP(
    "LangGraph Agent Server",
    auth=auth
)
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
CMD ["python", "-m", "agent_mcp.mcp_server"]
```

## License

MIT

## References

- [FastMCP Documentation](https://gofastmcp.com/)
- [MCP Specification](https://spec.modelcontextprotocol.io/)
- [ChatGPT Enterprise](https://openai.com/enterprise)
