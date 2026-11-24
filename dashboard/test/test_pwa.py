import json
import struct
import sys
import threading
import unittest
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashboard_server import DashboardHandler, ThreadingHTTPServer


class PwaTest(unittest.TestCase):
    def test_installable_assets_are_served(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), DashboardHandler)
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"

        def fetch(path):
            with urllib.request.urlopen(f"{base}{path}", timeout=5) as response:
                self.assertEqual(response.status, 200)
                return response.headers.get_content_type(), response.read()

        try:
            _, page = fetch("/")
            self.assertIn(b'<link rel="manifest" href="manifest.webmanifest">', page)
            content_type, body = fetch("/manifest.webmanifest")
            self.assertEqual(content_type, "application/manifest+json")
            manifest = json.loads(body)
            self.assertEqual(manifest["display"], "standalone")
            self.assertEqual(manifest["start_url"], "/")
            self.assertEqual(manifest["scope"], "/")

            for icon in manifest["icons"]:
                content_type, data = fetch(icon["src"])
                self.assertEqual(content_type, "image/png")
                self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n")
                size = int(icon["sizes"].split("x")[0])
                self.assertEqual(struct.unpack(">II", data[16:24]), (size, size))
            self.assertEqual({icon["sizes"] for icon in manifest["icons"]}, {"192x192", "512x512"})

            content_type, body = fetch("/service-worker.js")
            self.assertEqual(content_type, "text/javascript")
            self.assertIn(b'event.request.mode === "navigate"', body)
            _, body = fetch("/js/main.js")
            self.assertIn(b'navigator.serviceWorker.register("/service-worker.js")', body)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
