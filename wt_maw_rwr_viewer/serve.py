#!/usr/bin/env python3
"""Serve the WT RWR/MAW coverage viewer. Run extract.py first to build static/data.json."""
import http.server, socketserver, os

PORT = 8010
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"))

class Handler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a): pass
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

with socketserver.TCPServer(("127.0.0.1", PORT), Handler) as httpd:
    print(f"WT RWR/MAW viewer -> http://127.0.0.1:{PORT}/")
    httpd.serve_forever()
