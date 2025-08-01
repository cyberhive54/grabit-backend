#!/usr/bin/env python3
"""
Simple HTTP server to serve GRABIT frontend files
Run this to avoid CORS issues when testing the frontend
"""

import http.server
import socketserver
import os
import sys

# Change to the directory containing the HTML files
os.chdir(os.path.dirname(os.path.abspath(__file__)))

PORT = 3000

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

if __name__ == "__main__":
    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            print(f"🚀 GRABIT Frontend Server running at:")
            print(f"   ➜ Local:   http://localhost:{PORT}")
            print(f"   ➜ Network: http://127.0.0.1:{PORT}")
            print(f"\n📝 Instructions:")
            print(f"   1. Make sure GRABIT backend is running on port 8000")
            print(f"   2. Open http://localhost:{PORT} in your browser")
            print(f"   3. Press Ctrl+C to stop the server")
            print(f"\n🔧 Backend should be running at: http://localhost:8000")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print(f"\n✅ Frontend server stopped")
        sys.exit(0)
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)