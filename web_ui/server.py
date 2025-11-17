"""
Simple HTTP server to serve the test UI and proxy requests.
This helps avoid CORS issues when testing.
"""

import http.server
import socketserver
import json
from urllib.parse import urlparse, parse_qs
import os

PORT = 3006

class TestUIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.dirname(__file__), **kwargs)
    
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            
            with open(os.path.join(os.path.dirname(__file__), 'index.html'), 'rb') as f:
                self.wfile.write(f.read())
        else:
            super().do_GET()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()


if __name__ == "__main__":
    with socketserver.TCPServer(("", PORT), TestUIHandler) as httpd:
        print(f"🌐 Test UI Server running at http://localhost:{PORT}")
        print(f"📂 Serving files from: {os.path.dirname(__file__)}")
        print(f"\n🚀 Open http://localhost:{PORT} in your browser to test the MCP server")
        print(f"\nPress Ctrl+C to stop the server\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n✋ Server stopped")
