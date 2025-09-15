#!/usr/bin/env python3
# aMiscreant
import http.server
import socketserver
import threading


class HTTPServer:
    def __init__(self, port=8000):
        self.port = port
        self.handler = http.server.SimpleHTTPRequestHandler
        self.httpd = None
        self.thread = None

    def start(self):
        if self.httpd is not None:
            print("Server already running.")
            return

        self.httpd = socketserver.TCPServer(("", self.port), self.handler)

        # Run in a background thread so it doesn’t block
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

        print(f"Serving at port {self.port}")

    def stop(self):
        if self.httpd is None:
            print("Server not running.")
            return

        self.httpd.shutdown()
        self.httpd.server_close()
        self.httpd = None
        print("Server stopped.")


if __name__ == "__main__":
    server = HTTPServer(8000)
    server.start()

    input("Press Enter to stop server...\n")
    server.stop()
