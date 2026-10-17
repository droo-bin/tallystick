"""Builds the app once, starts one browser, and serves the installable build over HTTP.

Everything here is created lazily and shared by every test in the run, then closed at exit.
"""
import atexit
import functools
import http.server
import socketserver
import subprocess
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
DIST = ROOT / "dist"
SINGLE_FILE = DIST / "tallystick.html"
PWA_DIR = DIST / "pwa"

_state = {}


def ensure_built():
    if "built" not in _state:
        subprocess.run(["node", str(ROOT / "build.js")], check=True, capture_output=True)
        _state["built"] = True


def browser():
    """One headless Chromium for the whole test run."""
    if "browser" not in _state:
        ensure_built()
        pw = sync_playwright().start()
        _state["pw"], _state["browser"] = pw, pw.chromium.launch()
        atexit.register(_close_browser)
    return _state["browser"]


def device(name):
    """Browser settings for a phone or tablet, e.g. device("iPhone 13")."""
    browser()
    return {k: v for k, v in _state["pw"].devices[name].items() if k != "default_browser_type"}


def _close_browser():
    _state.pop("browser").close()
    _state.pop("pw").stop()


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {**http.server.SimpleHTTPRequestHandler.extensions_map,
                      ".webmanifest": "application/manifest+json"}

    def log_message(self, *args):
        pass


def pwa_url():
    """The installable build, served from a local web server like a real host would."""
    if "server" not in _state:
        ensure_built()
        handler = functools.partial(_QuietHandler, directory=str(PWA_DIR))
        server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        _state["server"] = server
        atexit.register(server.shutdown)
    return f"http://127.0.0.1:{_state['server'].server_address[1]}/"


def single_file_url():
    """The one-file build, opened straight from disk."""
    ensure_built()
    return SINGLE_FILE.as_uri()


BUILDS = {"single file": single_file_url, "installable app": pwa_url}
