"""Serves dist/pwa locally, then checks it installs, works offline and looks right on a phone."""
import os, sys, json, threading, http.server, functools, socketserver
from playwright.sync_api import sync_playwright

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pwa = os.path.join(root, "dist", "pwa")
shots = os.path.join(root, "test", "shots"); os.makedirs(shots, exist_ok=True)
Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=pwa)
Handler.log_message = lambda *a: None
http.server.SimpleHTTPRequestHandler.extensions_map[".webmanifest"] = "application/manifest+json"
srv = socketserver.TCPServer(("127.0.0.1", 0), Handler); port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{port}/"

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    phone = p.devices["iPhone 13"]
    ctx = b.new_context(**{k: v for k, v in phone.items() if k != "default_browser_type"})
    pg = ctx.new_page()
    pg.on("console", lambda m: m.type == "error" and errors.append(m.text))
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(url)
    pg.evaluate("navigator.serviceWorker.ready.then(() => true)")
    pg.reload(); pg.wait_for_function("navigator.serviceWorker.controller !== null")
    man = pg.evaluate("fetch('manifest.webmanifest').then(r => r.json())")
    assert man["display"] == "standalone" and any(i["purpose"] == "maskable" for i in man["icons"]), man
    for i in man["icons"]:
        assert pg.evaluate(f"fetch('{i['src']}').then(r => r.ok)"), i
    cached = pg.evaluate("caches.keys().then(k => caches.open(k[0])).then(c => c.keys()).then(r => r.map(x => new URL(x.url).pathname))")
    print("cached:", sorted(cached))
    # iOS install hint shows on an iPhone in the browser
    assert pg.is_visible("#install") and "Add to Home Screen" in pg.inner_text("#install-text")
    pg.screenshot(path=shots + "/m0.png", full_page=True)
    # offline: reload still works
    ctx.set_offline(True)
    pg.reload(); pg.wait_for_selector("#owner")
    pg.fill("#owner", "Sam Taylor"); pg.click("#next")
    pg.screenshot(path=shots + "/m1.png")
    # no horizontal scrolling on a phone
    assert pg.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"), "page scrolls sideways"
    # inputs are at least 16px so iOS doesn't zoom
    small = pg.evaluate("[...document.querySelectorAll('input:not([type=file]):not([type=checkbox]):not([type=radio]),select,textarea,[contenteditable]')].filter(e => parseFloat(getComputedStyle(e).fontSize) < 16).map(e => e.className || e.id)")
    assert not small, ("inputs under 16px", small)
    # touch targets
    tiny = pg.evaluate("""[...document.querySelectorAll('#screen-1 button, #screen-1 label.small')].filter(e => e.offsetParent && e.getBoundingClientRect().height < 44).map(e => e.textContent.trim()).slice(0, 5)""")
    assert not tiny, ("targets under 44px", tiny)
    pg.click("#next"); pg.screenshot(path=shots + "/m2.png", full_page=True)
    b.close()
srv.shutdown()
print("errors:", errors)
sys.exit(1 if errors else 0)
