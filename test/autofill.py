"""Autofill: a value filled without an input event (as Chrome's suggestion list can do) must still count."""
import os, re, sys
from playwright.sync_api import sync_playwright
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.goto("file://" + os.path.join(root, "dist", "tallystick.html"))
    # set the value silently, then send only a change event
    pg.eval_on_selector("#owner", "e => { e.value = 'Sam Taylor'; e.dispatchEvent(new Event('change', { bubbles: true })); }")
    assert pg.is_enabled("#next"), "Start stayed disabled after an autofill-style fill"
    pg.click("#next"); pg.click("#next")
    names = pg.locator("#people input[type=text]:not(.contact)")
    for i, n in enumerate(["Jo Smith", "Pat Lee"]):
        names.nth(i).evaluate("(e, v) => { e.value = v; e.dispatchEvent(new Event('change', { bubbles: true })); }", n)
    assert "2 of 2" in pg.inner_text("#k-big"), pg.inner_text("#k-big")
    b.close()
print("autofill ok")
