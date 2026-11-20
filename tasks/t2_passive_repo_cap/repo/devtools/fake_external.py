"""In-memory stand-in for a third-party HTTP API, used by tests."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class FakeExternal:
    def __init__(self):
        self.calls = []
        self._routes = {}
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def _serve(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b""
                body = json.loads(raw) if raw else None
                fake.calls.append(
                    {"method": self.command, "path": self.path, "body": body}
                )
                route = fake._routes.get((self.command, self.path.split("?")[0]))
                status, payload = route(body) if route else (404, {"error": "no route"})
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = _serve

            def log_message(self, *args):
                pass

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        self.base_url = f"http://127.0.0.1:{self._server.server_address[1]}"

    def route(self, method, path, handler):
        self._routes[(method, path)] = handler

    def stop(self):
        self._server.shutdown()
        self._server.server_close()
