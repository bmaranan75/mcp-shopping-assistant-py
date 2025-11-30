"""
HTML Formatter for MCP Server Responses

This module provides utilities to format agent responses as HTML
for iframe display in ChatGPT.
"""

def format_response_as_html(content: str, title: str = "Agent Response") -> str:
    """
    Format text content as styled HTML suitable for iframe display.
    
    Args:
        content: The text content to format
        title: The page title
        
    Returns:
        Formatted HTML string
    """
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
                'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #333;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 20px;
            min-height: 100vh;
        }}
        
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        
        .header h1 {{
            font-size: 28px;
            font-weight: 600;
            margin-bottom: 10px;
        }}
        
        .header p {{
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 40px;
        }}
        
        .response-box {{
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }}
        
        .response-box pre {{
            white-space: pre-wrap;
            word-wrap: break-word;
            font-family: 'Courier New', Courier, monospace;
            font-size: 14px;
            line-height: 1.5;
        }}
        
        .badge {{
            display: inline-block;
            padding: 4px 12px;
            background: #667eea;
            color: white;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            margin-bottom: 15px;
        }}
        
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            font-size: 12px;
            color: #666;
            border-top: 1px solid #e0e0e0;
        }}
        
        /* Markdown-like formatting */
        h2 {{
            color: #667eea;
            margin-top: 30px;
            margin-bottom: 15px;
            font-size: 22px;
        }}
        
        h3 {{
            color: #764ba2;
            margin-top: 20px;
            margin-bottom: 10px;
            font-size: 18px;
        }}
        
        ul, ol {{
            margin-left: 25px;
            margin-bottom: 15px;
        }}
        
        li {{
            margin-bottom: 8px;
        }}
        
        code {{
            background: #f4f4f4;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Courier New', Courier, monospace;
            font-size: 13px;
        }}
        
        .timestamp {{
            color: #999;
            font-size: 11px;
            margin-top: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🤖 {title}</h1>
            <p>MCP Server Response</p>
        </div>
        
        <div class="content">
            <span class="badge">AI Agent</span>
            
            <div class="response-box">
                <pre>{content}</pre>
            </div>
            
            <div class="timestamp">
                Generated at: {get_timestamp()}
            </div>
        </div>
        
        <div class="footer">
            Powered by LangGraph Agent MCP Server
        </div>
    </div>
</body>
</html>
"""
    return html


def get_timestamp() -> str:
    """Get current timestamp as formatted string."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def format_json_as_html(data: dict, title: str = "JSON Response") -> str:
    """
    Format JSON data as styled HTML.
    
    Args:
        data: Dictionary to format
        title: Page title
        
    Returns:
        Formatted HTML string
    """
    import json
    json_str = json.dumps(data, indent=2, ensure_ascii=False)
    
    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            margin: 0;
        }}
        
        .json-container {{
            background: #252526;
            border-radius: 8px;
            padding: 20px;
            overflow-x: auto;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
        }}
        
        pre {{
            margin: 0;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        
        .string {{ color: #ce9178; }}
        .number {{ color: #b5cea8; }}
        .boolean {{ color: #569cd6; }}
        .null {{ color: #569cd6; }}
        .key {{ color: #9cdcfe; }}
    </style>
</head>
<body>
    <div class="json-container">
        <pre>{json_str}</pre>
    </div>
</body>
</html>
"""
    return html
