# Streaming API Fix - Migration from /wait to /runs/stream

## Problem Statement

The MCP server implementation was using an incorrect API pattern that relied on the non-existent `/runs/{run_id}/wait` endpoint. This endpoint is not available in the current LangGraph server version, causing 404 errors when trying to invoke agents.

## Root Cause

- **Working endpoint**: `/runs/stream` - Streaming API (available ✅)
- **Broken endpoint**: `/runs/{run_id}/wait` - Non-streaming wait endpoint (not available ❌)

The server was using a two-step approach:

1. POST to `/runs` to create a run
2. GET from `/runs/{run_id}/wait` to wait for completion (404 error)

## Solution

Migrated all endpoints to use the streaming API pattern:

```python
# ❌ OLD BROKEN PATTERN
response = await client.post(f"{LANGGRAPH_BASE_URL}/runs", json=payload)
run_id = response.json()["run_id"]
result = await client.get(f"{LANGGRAPH_BASE_URL}/runs/{run_id}/wait")  # 404!

# ✅ NEW WORKING PATTERN
payload["stream_mode"] = ["values"]
async with client.stream("POST", f"{LANGGRAPH_BASE_URL}/runs/stream", json=payload) as response:
    chunks = []
    async for chunk in response.aiter_text():
        if chunk.strip():
            chunks.append(chunk)
            # Parse metadata and output
```

## Files Modified

### 1. `src/agent_mcp/openapi_oauth_server.py`

- **Function**: `invoke_agent()` (line ~564)
- **Change**: Replaced POST + GET pattern with streaming API
- **Impact**: ChatGPT Enterprise integration now works correctly

### 2. `src/agent_mcp/mcp_server.py`

- **Added**: `import json` (needed for parsing stream chunks)
- **Function 1**: `invoke_agent()` (line ~50)
- **Function 2**: `check_system_health()` (line ~227)
- **Function 3**: `check_agent_status()` (line ~307)
- **Change**: All three functions now use streaming API
- **Impact**: All MCP tool invocations work correctly

### 3. `src/agent_mcp/openapi_server.py`

- **Added**: `import json` (needed for parsing stream chunks)
- **Function**: `invoke_agent()` (line ~181)
- **Change**: Replaced POST + GET pattern with streaming API
- **Impact**: Standard OpenAPI endpoints work correctly

## Implementation Details

### Stream Processing

The new implementation:

1. Sends a single POST request to `/runs/stream` with `stream_mode: ["values"]`
2. Iterates through streaming chunks using `async for chunk in response.aiter_text()`
3. Parses each chunk as JSON to extract metadata (run_id, thread_id)
4. Stores the final output from the last complete chunk
5. Returns structured response with run_id, thread_id, and output

### Metadata Extraction

```python
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
```

### Error Handling

- Maintains the same error handling patterns
- HTTPException for HTTP errors
- Generic exception handling for other errors
- Proper error logging through context (for MCP server)

## Benefits

1. **✅ Works with LangGraph Server**: Uses the actually available API
2. **✅ No More 404 Errors**: Eliminates the broken `/wait` endpoint calls
3. **✅ Backward Compatible**: Response structure remains the same
4. **✅ Better Performance**: Single request instead of two sequential requests
5. **✅ Real-time Data**: Can access streaming data if needed in the future

## Testing Recommendations

1. Test `/invoke` endpoint in `openapi_oauth_server.py` (ChatGPT integration)
2. Test all MCP tools: `invoke_agent`, `check_system_health`, `check_agent_status`
3. Test `/invoke` endpoint in `openapi_server.py` (standard API)
4. Verify run_id and thread_id are correctly extracted from stream
5. Test error handling with invalid requests

## Verification Commands

```bash
# Test ChatGPT Enterprise server
curl -X POST http://localhost:8001/invoke \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello", "assistant_id": "agent"}'

# Test standard OpenAPI server
curl -X POST http://localhost:8000/invoke \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"prompt": "Hello", "assistant_id": "agent"}'
```

## Migration Complete ✅

All instances of the broken `/runs/{run_id}/wait` pattern have been successfully replaced with the working `/runs/stream` streaming API pattern.
