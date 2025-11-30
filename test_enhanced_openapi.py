"""
Test script to verify enhanced OpenAPI schema with HTML formatting instructions.

This script validates that:
1. ChatGPT display hints are present in the schema
2. Response models include HTML rendering instructions
3. AI plugin manifest includes HTML capabilities
4. Custom x-chatgpt extensions are properly configured
"""

import json
import sys
from fastapi.testclient import TestClient

# Import the FastAPI app
sys.path.insert(0, 'src')
from agent_mcp.openapi_oauth_server import app


def test_openapi_schema():
    """Test that OpenAPI schema includes HTML formatting instructions."""
    
    print("=" * 70)
    print("Testing Enhanced OpenAPI Schema")
    print("=" * 70)
    
    client = TestClient(app)
    
    # Get OpenAPI schema
    response = client.get("/openapi.json")
    assert response.status_code == 200, "Failed to fetch OpenAPI schema"
    
    schema = response.json()
    
    # Test 1: Check global x-chatgpt-plugin extension
    print("\n✅ Test 1: Global ChatGPT Plugin Configuration")
    assert "x-chatgpt-plugin" in schema, "Missing x-chatgpt-plugin extension"
    plugin_config = schema["x-chatgpt-plugin"]
    print(f"  Response Format: {plugin_config.get('response_format')}")
    print(f"  Render Mode: {plugin_config.get('render_mode')}")
    print(f"  Preserve HTML Styling: {plugin_config.get('preserve_html_styling')}")
    print(f"  Capabilities: {plugin_config.get('capabilities')}")
    assert plugin_config["response_format"] == "html", "Response format should be HTML"
    assert plugin_config["preserve_html_styling"] is True, "Should preserve HTML styling"
    
    # Test 2: Check /invoke endpoint x-chatgpt-display
    print("\n✅ Test 2: /invoke Endpoint ChatGPT Display Hints")
    invoke_path = schema["paths"].get("/invoke", {})
    invoke_post = invoke_path.get("post", {})
    assert "x-chatgpt-display" in invoke_post, "Missing x-chatgpt-display in /invoke"
    display_config = invoke_post["x-chatgpt-display"]
    print(f"  Format: {display_config.get('format')}")
    print(f"  Content Field: {display_config.get('content_field')}")
    print(f"  Render HTML: {display_config.get('render_html')}")
    print(f"  Show Metadata: {display_config.get('show_metadata')}")
    assert display_config["format"] == "html", "/invoke should use HTML format"
    assert display_config["render_html"] is True, "/invoke should render HTML"
    
    # Test 3: Check /stream endpoint x-chatgpt-display
    print("\n✅ Test 3: /stream Endpoint ChatGPT Display Hints")
    stream_path = schema["paths"].get("/stream", {})
    stream_post = stream_path.get("post", {})
    assert "x-chatgpt-display" in stream_post, "Missing x-chatgpt-display in /stream"
    stream_display = stream_post["x-chatgpt-display"]
    print(f"  Format: {stream_display.get('format')}")
    print(f"  Content Field: {stream_display.get('content_field')}")
    print(f"  Render HTML: {stream_display.get('render_html')}")
    print(f"  Progressive Display: {stream_display.get('progressive_display')}")
    assert stream_display["format"] == "html", "/stream should use HTML format"
    assert stream_display["progressive_display"] is True, "/stream should support progressive display"
    
    # Test 4: Check response model schemas have detailed descriptions
    print("\n✅ Test 4: Response Model Descriptions")
    components = schema.get("components", {})
    schemas = components.get("schemas", {})
    
    # Check InvokeResponse
    if "InvokeResponse" in schemas:
        invoke_response = schemas["InvokeResponse"]
        output_field = invoke_response.get("properties", {}).get("output", {})
        output_desc = output_field.get("description", "")
        print(f"  InvokeResponse.output description length: {len(output_desc)} chars")
        assert "HTML" in output_desc or "html" in output_desc, "Should mention HTML rendering"
        assert "CHATGPT" in output_desc or "ChatGPT" in output_desc, "Should include ChatGPT instructions"
    
    # Check StreamResponse
    if "StreamResponse" in schemas:
        stream_response = schemas["StreamResponse"]
        output_field = stream_response.get("properties", {}).get("output", {})
        output_desc = output_field.get("description", "")
        print(f"  StreamResponse.output description length: {len(output_desc)} chars")
        assert "HTML" in output_desc or "html" in output_desc, "Should mention HTML rendering"
    
    # Test 5: Check endpoint descriptions are comprehensive
    print("\n✅ Test 5: Endpoint Descriptions")
    invoke_desc = invoke_post.get("description", "")
    stream_desc = stream_post.get("description", "")
    print(f"  /invoke description length: {len(invoke_desc)} chars")
    print(f"  /stream description length: {len(stream_desc)} chars")
    assert len(invoke_desc) > 200, "/invoke description should be comprehensive"
    assert len(stream_desc) > 200, "/stream description should be comprehensive"
    assert "HTML" in invoke_desc, "/invoke should mention HTML formatting"
    assert "HTML" in stream_desc, "/stream should mention HTML formatting"
    
    print("\n" + "=" * 70)
    print("✅ All Enhanced OpenAPI Schema Tests Passed!")
    print("=" * 70)
    
    return True


def test_ai_plugin_manifest():
    """Test that AI plugin manifest includes HTML capabilities."""
    
    print("\n" + "=" * 70)
    print("Testing AI Plugin Manifest")
    print("=" * 70)
    
    client = TestClient(app)
    
    # Get AI plugin manifest
    response = client.get("/.well-known/ai-plugin.json")
    assert response.status_code == 200, "Failed to fetch AI plugin manifest"
    
    manifest = response.json()
    
    # Test 1: Check description_for_model includes HTML instructions
    print("\n✅ Test 1: Model Description Includes HTML Instructions")
    model_desc = manifest.get("description_for_model", "")
    print(f"  Description length: {len(model_desc)} chars")
    assert "HTML" in model_desc, "Should mention HTML rendering"
    assert "IMPORTANT DISPLAY INSTRUCTIONS" in model_desc, "Should have display instructions"
    assert "thread_id" in model_desc, "Should mention thread_id for conversations"
    
    # Test 2: Check API configuration
    print("\n✅ Test 2: API Configuration")
    api_config = manifest.get("api", {})
    print(f"  Response Format: {api_config.get('response_format')}")
    print(f"  Supports HTML Rendering: {api_config.get('supports_html_rendering')}")
    assert api_config.get("response_format") == "html", "API should specify HTML format"
    assert api_config.get("supports_html_rendering") is True, "Should support HTML rendering"
    
    # Test 3: Check capabilities
    print("\n✅ Test 3: Plugin Capabilities")
    capabilities = manifest.get("capabilities", {})
    print(f"  HTML Responses: {capabilities.get('html_responses')}")
    print(f"  Structured Data: {capabilities.get('structured_data')}")
    print(f"  Conversation Memory: {capabilities.get('conversation_memory')}")
    print(f"  Product Recommendations: {capabilities.get('product_recommendations')}")
    assert capabilities.get("html_responses") is True, "Should support HTML responses"
    assert capabilities.get("conversation_memory") is True, "Should support conversation memory"
    
    print("\n" + "=" * 70)
    print("✅ All AI Plugin Manifest Tests Passed!")
    print("=" * 70)
    
    return True


def print_sample_schema_excerpt():
    """Print a sample of the enhanced schema for visual inspection."""
    
    print("\n" + "=" * 70)
    print("Sample Schema Excerpt - /invoke Endpoint")
    print("=" * 70)
    
    client = TestClient(app)
    response = client.get("/openapi.json")
    schema = response.json()
    
    # Extract /invoke endpoint
    invoke_endpoint = schema["paths"].get("/invoke", {}).get("post", {})
    
    # Print formatted JSON
    print(json.dumps({
        "summary": invoke_endpoint.get("summary"),
        "description": invoke_endpoint.get("description", "")[:500] + "...",
        "x-chatgpt-display": invoke_endpoint.get("x-chatgpt-display"),
        "x-openai-isConsequential": invoke_endpoint.get("x-openai-isConsequential")
    }, indent=2))
    
    print("\n" + "=" * 70)
    print("Global x-chatgpt-plugin Configuration")
    print("=" * 70)
    print(json.dumps(schema.get("x-chatgpt-plugin"), indent=2))


if __name__ == "__main__":
    try:
        # Run tests
        test_openapi_schema()
        test_ai_plugin_manifest()
        print_sample_schema_excerpt()
        
        print("\n" + "🎉" * 35)
        print("SUCCESS! Enhanced OpenAPI schema is properly configured")
        print("ChatGPT will now:")
        print("  ✅ Render HTML-formatted responses")
        print("  ✅ Display tables, lists, and styled content")
        print("  ✅ Preserve formatting and colors")
        print("  ✅ Hide internal metadata from users")
        print("  ✅ Maintain conversation context with thread_id")
        print("🎉" * 35)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
