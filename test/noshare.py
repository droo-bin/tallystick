"""Without a share sheet: no Share buttons and no share wording, Save still offered."""
import os, re, sys
from playwright.sync_api import sync_playwright
root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page()
    pg.add_init_script("delete Navigator.prototype.canShare; delete Navigator.prototype.share;")
    pg.goto("file://" + os.path.join(root, "dist", "tallystick.html"))
    pg.fill("#owner", "Sam Taylor"); pg.click("#next"); pg.click("#next")
    n = pg.locator("#people input[type=text]:not(.contact)"); n.nth(0).fill("Jo Smith"); n.nth(1).fill("Pat Lee")
    pg.click("#next"); pg.click("#next"); pg.click("#next")
    pg.locator("#done-h", has_text=re.compile("checked|wrong")).wait_for(timeout=60000)
    assert pg.locator("#share-info").is_hidden(), "share wording shown without sharing"
    assert pg.locator("#send-list").get_by_role("button", name=re.compile("^Share")).count() == 0
    assert pg.locator("#send-list").get_by_role("button", name=re.compile("^Save files")).count() == 2
    assert "Printed cards are safest" in pg.inner_text("#task-give")
    b.close()
print("no-share ok")
