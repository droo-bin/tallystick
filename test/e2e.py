import os, re, sys
from playwright.sync_api import sync_playwright

root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
app = os.environ.get("APP_URL") or "file://" + os.path.join(root, "dist", "tallystick.html")
print("testing", app)
shots = os.path.join(root, "test", "shots"); os.makedirs(shots, exist_ok=True)
dl = os.path.join(root, "test", "downloads"); os.makedirs(dl, exist_ok=True)
attach = os.path.join(dl, "statement.txt"); open(attach, "w").write("Nationwide statement")
attach2 = os.path.join(dl, "deeds.txt"); open(attach2, "w").write("Deeds scan")
from PIL import Image
import random
bigpng = os.path.join(dl, "pension.png")
Image.frombytes("RGB", (2600, 1800), os.urandom(2600*1800*3)).save(bigpng)
print("big png bytes", os.path.getsize(bigpng))
CODE = r"TALLY1(?:-[0-9A-F]{4}){24}"

errors = []
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 420, "height": 900}, accept_downloads=True)
    ctx.add_init_script("""navigator.canShare = () => true;
      navigator.share = (d) => { window.__shared = { names: d.files.map(f => f.name), text: d.text, title: d.title }; return Promise.resolve(); };""")
    pg = ctx.new_page()
    pg.on("pageerror", lambda e: errors.append("creator: " + str(e)))
    pg.goto(app)
    assert pg.is_disabled("#next")
    pg.fill("#owner", "Sam Taylor")
    pg.click("#next")

    # Money: tap a bank, tap its type, add rich notes and a file
    money = pg.locator("details.sec").nth(0)
    pg.get_by_role("button", name="+ Nationwide").click()
    money.locator(".entry.open").get_by_role("button", name="Current", exact=True).click()
    money.locator(".entry.open").get_by_role("button", name="+ Notes").click()
    ed = money.locator(".entry.open .rt")
    ed.type("Salary goes in here. ")
    money.locator(".entry.open .rt-bar").get_by_role("button", name="Bold").click()
    ed.type("Close last")
    money.locator(".entry.open input[type=file]").set_input_files(attach)
    pg.evaluate("""() => { const e = document.querySelector('details.sec .entry.open .rt');
      e.innerHTML += '<img src=x onerror="window.pwned=1"><script>window.pwned=2<\\/script><a href="javascript:alert(1)">link</a>';
      e.dispatchEvent(new Event('input')); }""")
    money.locator(".entry.open").get_by_role("button", name="Done").click()
    # Two ISAs: chips stay available for repeats
    for provider in ["Vanguard", "Hargreaves Lansdown"]:
        pg.get_by_role("button", name="+ ISA").click()
        money.locator(".entry.open").get_by_label("Held with").fill(provider)
    assert money.locator(".entry .sum-title", has_text="ISA").count() == 2
    # Money section other documents
    pg.locator("details.sec").nth(0).locator(".form > .item").last.locator("input[type=file]").set_input_files(attach2)
    # Pensions: switch to photos and add a big screenshot
    pg.locator("details.sec summary").nth(2).click()
    pens = pg.locator("details.sec").nth(2)
    pens.get_by_role("button", name="Photos & screenshots").click()
    pens.locator(".photos input[type=file]").set_input_files(bigpng)
    pens.locator(".ph input[type=text]").wait_for()
    pens.locator(".ph input[type=text]").fill("Nest pension app")
    assert "1 photo" in pens.locator("summary .count").inner_text()
    # Wishes: chips on single items
    pg.locator("details.sec summary").nth(5).click()
    pg.get_by_role("button", name="With my solicitor").click()
    pg.get_by_role("button", name="Cremation").click()
    pg.locator("#affairs-letter .rt").click(); pg.keyboard.type("Don't panic. It's all here.")
    pg.screenshot(path=shots + "/1.png", full_page=True)
    pg.click("#next")

    names = pg.locator("#people input[type=text]:not(.contact)")
    names.nth(0).fill("Jo Smith"); names.nth(1).fill("Sam Macdonald"); names.nth(2).fill("Pat Lee")
    pg.click("#add-person"); pg.locator("#people input[type=text]:not(.contact)").nth(3).fill("Alex Macdonald")
    pg.locator("#people select").nth(3).select_option("Family")
    pg.locator("#people .contact").nth(2).fill("07700 900123")
    pg.locator("#people .contact").nth(0).fill("jo@example.com")
    assert "3 of 4" in pg.inner_text("#k-big"), pg.inner_text("#k-big")
    pg.click("#next")
    pg.click("#add-extra")
    pg.locator("#extras input[type=text]").first.fill("Letter to Sam")
    pg.locator("#extras .rt").first.click(); pg.keyboard.type("Dear Sam, you were the best thing.")
    boxes = pg.locator("#extras input[type=checkbox]")
    boxes.nth(2).uncheck(); boxes.nth(3).uncheck()
    pg.click("#next")
    pg.fill("#copies-other", "Grey filing cabinet")
    pg.click("#next")
    pg.locator("#done-h", has_text=re.compile("checked|wrong")).wait_for(timeout=60000)
    print("HEADING:", pg.inner_text("#done-h"), "|", pg.inner_text("#done-sub"))
    assert "checked" in pg.inner_text("#done-h")
    pg.screenshot(path=shots + "/5.png", full_page=True)
    pg.locator("#checks-wrap summary").click()
    print(pg.inner_text("#checks"))

    assert pg.is_visible("#share-info"), "share info should show when sharing works"
    sends = pg.locator("#send-list .send")
    assert sends.count() == 4
    assert sends.nth(0).get_by_role("link").count() == 0, "email/text links should be gone"
    assert "jo@example.com" in sends.nth(0).inner_text()
    sends.nth(0).get_by_role("button", name="Share with Jo Smith").click()
    shared = pg.evaluate("window.__shared")
    print("Jo gets:", shared["names"])
    assert shared["names"][0] == "Tallystick card - Jo Smith.html" and len(shared["names"]) == 5, shared["names"]
    assert any("Letter to Sam" in n for n in shared["names"]) and any("Start here" in n for n in shared["names"])
    assert "copies of my sealed envelopes are attached" in shared["text"], shared["text"]
    sends.nth(2).get_by_role("button", name="Share with Pat Lee").click()
    pat_names = pg.evaluate("window.__shared")["names"]
    print("Pat gets:", pat_names)
    assert not any("Letter to Sam" in n for n in pat_names) and len(pat_names) == 4, pat_names
    assert "Card and 3 envelopes" in sends.nth(2).inner_text()
    pg.get_by_label("Include their envelopes").uncheck()
    assert "Card only" in sends.nth(2).inner_text()
    sends.nth(0).get_by_role("button", name="Share with Jo Smith").click()
    only = pg.evaluate("window.__shared")
    assert only["names"] == ["Tallystick card - Jo Smith.html"] and "Your card is attached" in only["text"], only
    with pg.expect_download() as d:
        sends.nth(2).get_by_role("button", name="Save files for Pat Lee").click()
    one = d.value.path(); onecard = open(one).read()
    assert onecard.count('class="card"') == 1 and "Pat Lee" in onecard, "single card file wrong"
    assert re.search(r"Created \d{1,2} \w+ \d{4}", onecard), "saved card has no created stamp"
    print("send ok:", d.value.suggested_filename)
    pg.get_by_label("Include their envelopes").check()
    pg.get_by_text("Save one at a time").click()
    files = {}
    for label in ["Affairs", "Letter to Sam", "Contents list", "Start here"]:
        with pg.expect_download() as d:
            pg.click(f"button[aria-label='Save {label} envelope']")
        path = os.path.join(dl, d.value.suggested_filename); d.value.save_as(path); files[label] = path
    blocks = pg.locator("#cards .card")
    def card_codes(i): return re.findall(CODE, blocks.nth(i).text_content())
    jo, sam, pat, alex = (card_codes(i) for i in range(4))
    assert len(jo) == 4 and len(sam) == 4 and len(pat) == 3 and len(alex) == 3, (len(jo), len(sam), len(pat), len(alex))
    jo_card = blocks.nth(0).text_content()
    assert "The other cards are held by Sam Macdonald, Pat Lee and Alex Macdonald" in jo_card, jo_card
    assert "The other cards are held by Sam Macdonald." in jo_card
    assert "Pat Lee · Friend · 07700 900123" in jo_card, jo_card
    stamp = re.search(r"Created (\d{1,2} \w+ \d{4}(?:,| at) \d{2}:\d{2} (?:BST|GMT|UTC|GMT[+-]\d+))", jo_card)
    assert stamp, jo_card
    print("card stamp:", stamp.group(1))

    ctx.set_offline(True)
    env = ctx.new_page(); env.on("pageerror", lambda e: errors.append("envelope: " + str(e)))
    env.goto("file://" + files["Affairs"])
    env.screenshot(path=shots + "/env-locked.png", full_page=True)
    locked = env.inner_text("body")
    assert stamp.group(1) in locked, ("envelope stamp differs from card", locked[:300])
    assert not any(n in locked for n in ["Jo Smith", "Pat Lee", "Alex Macdonald"]), "locked envelope shows names"
    assert "Jo Smith" not in open(files["Affairs"]).read(), "names stored in plain text in the file"
    env.fill("#card0", sam[0]); env.fill("#card1", alex[0]); env.fill("#card2", pat[0])
    env.click("#open"); env.wait_for_selector("#opened:not([hidden])")
    txt = env.inner_text("#opened")
    for want in ["Vanguard", "Hargreaves Lansdown", "Nest pension app", "Nationwide", "Type: Current", "Salary goes in here", "statement.txt", "deeds.txt", "With my solicitor", "Cremation", "Don't panic"]:
        assert want in txt, (want, txt)
    assert env.locator("#opened .rich strong", has_text="Close last").count() == 1, "bold lost"
    assert env.locator("#opened .gallery img").count() == 1, "photo missing"
    print("photo saved as", env.locator("#opened .gallery a").get_attribute("download"))
    assert env.locator("#opened .gallery a").get_attribute("download").endswith(".jpg")
    env.wait_for_timeout(300)
    assert env.evaluate("window.pwned") is None, "script ran!"
    assert env.locator("#opened .rich img, #opened .rich script, #opened .rich a").count() == 0, "unsafe tags kept"
    env.screenshot(path=shots + "/env-open.png", full_page=True)

    env2 = ctx.new_page(); env2.goto("file://" + files["Letter to Sam"])
    env2.fill("#card0", sam[1]); env2.fill("#card1", jo[1]); env2.click("#open"); env2.wait_for_selector("#opened:not([hidden])")
    assert "Dear Sam" in env2.inner_text("#opened")
    env3 = ctx.new_page(); env3.goto("file://" + files["Contents list"])
    env3.fill("#card0", pat[-2]); env3.fill("#card1", alex[-2]); env3.click("#open"); env3.wait_for_selector("#opened:not([hidden])")
    ctxt = env3.inner_text("#opened")
    assert "Grey filing cabinet" in ctxt and "any 3 of its 4 cards" in ctxt, ctxt
    assert not any(n in ctxt for n in ["Jo Smith", "Pat Lee", "Alex Macdonald"]), "contents list names card holders"
    # Practice: Pat's practice code (last on the card) opens it alone; a real code is refused
    env4 = ctx.new_page(); env4.goto("file://" + files["Start here"])
    assert "Open with your card" in env4.inner_text("#locked-h")
    env4.fill("#card0", pat[0]); env4.click("#open"); env4.wait_for_selector("#error:not([hidden])")
    env4.fill("#card0", pat[-1]); env4.click("#open"); env4.wait_for_selector("#opened:not([hidden])")
    ptxt = env4.inner_text("#opened")
    assert "Your card works" in ptxt and "needs 3 cards" in ptxt and "Grey filing cabinet" in ptxt, ptxt
    assert all(n in ptxt for n in ["Jo Smith", "Pat Lee", "Alex Macdonald", "Executor", "07700 900123"]), ptxt
    env4.screenshot(path=shots + "/practice.png", full_page=True)
    b.close()
print("errors:", errors)
sys.exit(1 if errors else 0)
