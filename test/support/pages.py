"""Page objects: the creator app, the finish screen with its cards, and a sealed envelope file.

Tests talk to these in the user's terms ("add an entry", "seal", "open with these cards")
rather than in selectors, so a markup change only needs fixing here.
"""
import re
from dataclasses import dataclass
from pathlib import Path

CARD_CODE = re.compile(r"TALLY1(?:-[0-9A-F]{4}){24}")
SEALED_HEADING = re.compile("checked|wrong")


class CreatorPage:
    def __init__(self, page, url):
        self.page = page
        page.goto(url)
        self.wait_until_ready()

    def wait_until_ready(self):
        """The app restores any saved draft before it accepts input."""
        self.page.wait_for_selector("html[data-ready]", state="attached")
        return self

    def reload(self):
        self.page.wait_for_timeout(600)  # let the debounced autosave land
        self.page.reload()
        return self.wait_until_ready()

    @property
    def step_title(self):
        return self.page.locator(".screen:not([hidden]) h1").inner_text()

    @property
    def resumed(self):
        return self.page.is_visible("#resumed")

    def start_over(self):
        """Start over asks for a second tap, clears the draft, then reloads the page."""
        self.page.click("#start-over")
        with self.page.expect_navigation():
            self.page.click("#start-over")
        return self.wait_until_ready()

    def back(self):
        self.page.click("#back")
        return self

    # Navigation
    def next(self):
        self.page.click("#next")
        return self

    @property
    def can_continue(self):
        return self.page.is_enabled("#next")

    def start(self, owner):
        self.page.fill("#owner", owner)
        return self.next()

    # Affairs
    def section(self, heading):
        sec = self.page.locator("details.sec", has=self.page.locator("summary", has_text=heading))
        if not sec.evaluate("d => d.open"):
            sec.locator("summary").click()
        return sec

    def add_entry(self, heading, suggestion, **fields):
        """Taps a suggestion such as '+ ISA', then fills the entry's fields by label or chip."""
        sec = self.section(heading)
        spoken = suggestion if suggestion.startswith("Add ") else f"Add {suggestion}"
        sec.get_by_role("button", name=spoken, exact=True).click()
        entry = sec.locator(".entry.open")
        for label, value in fields.items():
            label = label.replace("_", " ").capitalize()
            box = entry.get_by_role("textbox", name=label, exact=True)
            if box.count():
                box.fill(value)
            else:
                entry.get_by_role("button", name=value, exact=True).click()
        return entry

    def add_notes(self, entry, text, bold=""):
        entry.get_by_role("button", name="+ Notes").click()
        editor = entry.locator(".rt")
        editor.type(text)
        if bold:
            entry.get_by_role("button", name="Bold").click()
            editor.type(bold)
        return editor

    def attach(self, entry, path):
        entry.locator("input[type=file]").set_input_files(str(path))

    def entry(self, heading, title):
        return self.section(heading).locator(".entry", has=self.page.locator(".sum-title", has_text=title))

    def finish_entry(self, entry):
        entry.get_by_role("button", name="Done").click()

    def attach_to_section(self, heading, path):
        self.section(heading).locator(".form > .item").last.locator("input[type=file]").set_input_files(str(path))

    def pick(self, heading, answer):
        self.section(heading).get_by_role("button", name=answer, exact=True).click()

    def add_photo(self, heading, path, caption):
        sec = self.section(heading)
        sec.get_by_role("button", name="Photos & screenshots").click()
        sec.locator(".photos input[type=file]").set_input_files(str(path))
        sec.locator(".ph input[type=text]").last.fill(caption)

    def section_status(self, heading):
        return self.section(heading).locator("summary .count").inner_text()

    def record(self, button_name, seconds=1.5):
        """Presses a Voice note or Video button, records for a moment with the browser's fake camera and mic, and keeps it."""
        self.page.get_by_role("button", name=button_name).click()
        dialog = self.page.locator("#recorder")
        dialog.get_by_role("button", name="Start recording").click()
        self.page.wait_for_timeout(int(seconds * 1000))
        dialog.get_by_role("button", name="Stop").click()
        dialog.get_by_role("button", name="Keep it").click()
        dialog.wait_for(state="hidden")

    def write_note(self, text):
        self.page.locator("#affairs-letter .rt").click()
        self.page.keyboard.type(text)

    # Card holders
    def set_people(self, people):
        while self.page.locator("#people .person").count() < len(people):
            self.page.click("#add-person")
        rows = self.page.locator("#people .person")
        for i, person in enumerate(people):
            row = rows.nth(i)
            row.locator("input[type=text]:not(.contact)").fill(person.name)
            row.locator("select").select_option(person.role)
            if person.contact:
                row.locator(".contact").fill(person.contact)

    @property
    def cards_needed(self):
        return self.page.inner_text("#k-big")

    # Extra envelopes
    def add_envelope(self, envelope, everyone):
        self.page.click("#add-extra")
        box = self.page.locator("#extras .panel").last
        box.locator("input[type=text]").first.fill(envelope.name)
        box.locator(".rt").click()
        self.page.keyboard.type(envelope.text)
        for person in everyone:
            if person not in envelope.holders:
                box.get_by_label(re.compile("^" + re.escape(person.name))).uncheck()

    # Whole flow
    def fill_household(self, household, affairs=None):
        """Walks every step for a household. `affairs` is a callback that fills the affairs screen."""
        self.start(household.owner)
        if affairs:
            affairs(self)
        self.next()
        self.set_people(household.people)
        self.next()
        for envelope in household.extra_envelopes:
            self.add_envelope(envelope, household.people)
        self.next()
        if household.other_place:
            self.page.fill("#copies-other", household.other_place)
        return self

    def seal(self):
        self.next()
        self.page.locator("#done-h", has_text=SEALED_HEADING).wait_for(timeout=60000)
        self.page.wait_for_selector("html[data-history-saved]", state="attached")
        return FinishScreen(self.page)


@dataclass
class Card:
    holder: str
    text: str
    codes: dict  # envelope name -> code

    def code(self, envelope):
        return self.codes[envelope]


class FinishScreen:
    def __init__(self, page):
        self.page = page
        page.locator("#checks-wrap summary").click()

    @property
    def heading(self):
        return self.page.inner_text("#done-h")

    @property
    def summary(self):
        return self.page.inner_text("#done-sub")

    def check_results(self):
        """Envelope name -> the self-check sentence shown for it."""
        rows = self.page.locator("#checks .result")
        return {rows.nth(i).locator("strong").inner_text(): rows.nth(i).locator(".hint").inner_text()
                for i in range(rows.count())}

    def cards(self):
        """Holder name -> Card, read from the printable card previews."""
        found = {}
        cards = self.page.locator("#cards .card")
        for i in range(cards.count()):
            card = cards.nth(i)
            holder = card.locator("p strong").first.text_content()
            shares = card.locator(".share")
            codes = {shares.nth(j).locator("strong").text_content(): shares.nth(j).locator("code").text_content()
                     for j in range(shares.count())}
            found[holder] = Card(holder, card.text_content(), codes)
        return found

    # Save menus
    @staticmethod
    def open_menu(menu):
        if not menu.evaluate("d => d.open"):
            menu.locator("summary").click()
        return menu

    def menu_items(self, menu):
        """The labels in a save menu, e.g. ['Save – Card', 'Save – Affairs', 'Save all']."""
        items = self.open_menu(menu).get_by_role("menuitem")
        labels = [items.nth(i).locator("span").first.inner_text() for i in range(items.count())]
        menu.locator("summary").click()
        return labels

    def _download(self, menu, item, folder):
        self.open_menu(menu)
        with self.page.expect_download() as download:
            menu.get_by_role("menuitem", name=item, exact=True).click()
        path = Path(folder) / download.value.suggested_filename
        download.value.save_as(path)
        return path

    @property
    def envelope_menu(self):
        return self.page.locator("#save-envelopes details.menu")

    def save_envelope(self, name, folder):
        return self._download(self.envelope_menu, f"Save {name}", folder)

    # Handing out
    def send_row(self, holder):
        return self.page.locator("#send-list .send", has_text=holder)

    def include_envelopes(self, on=True):
        box = self.page.get_by_label("Include their envelopes")
        if on:
            box.check()
        else:
            box.uncheck()

    def share_with(self, holder):
        """Presses Share for a holder; returns what the (stubbed) share sheet received."""
        self.send_row(holder).get_by_role("button", name=f"Share with {holder}").click()
        return self.page.evaluate("window.__shared")

    def save_menu_for(self, holder):
        return self.send_row(holder).locator("details.menu")

    def save_for(self, holder, folder, item="Card"):
        return self._download(self.save_menu_for(holder), f"Save {item}", folder)


class EnvelopePage:
    """A sealed envelope file opened in the browser."""

    def __init__(self, page, path):
        self.page = page
        self.path = Path(path)
        page.goto(self.path.as_uri())

    @property
    def locked_text(self):
        return self.page.inner_text("body")

    @property
    def heading(self):
        return self.page.inner_text("#locked-h")

    def open_with(self, *codes):
        for i, code in enumerate(codes):
            self.page.fill(f"#card{i}", code)
        self.page.click("#open")
        self.page.wait_for_selector("#opened:not([hidden]), #error:not([hidden])")
        return self

    @property
    def error(self):
        return self.page.inner_text("#error") if self.page.is_visible("#error") else ""

    @property
    def contents(self):
        return self.page.inner_text("#opened") if self.page.is_visible("#opened") else ""

    def count(self, selector):
        return self.page.locator("#opened " + selector).count()

    def js(self, expression):
        return self.page.evaluate(expression)
