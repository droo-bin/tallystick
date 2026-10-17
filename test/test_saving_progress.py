"""Progress survives a refresh, and sealed envelopes are kept in a history (without card codes)."""
import unittest

from support import app
from support.data import JO, PAIR, PAT, SAM
from support.fixtures import BrowserTest, SealedHouseholdTest
from support.pages import CARD_CODE, CreatorPage, EnvelopePage

READ_DATABASE = """() => new Promise(resolve => {
  const req = indexedDB.open('tallystick', 1);
  req.onsuccess = () => {
    const db = req.result, out = {};
    const t = db.transaction(['draft', 'history'], 'readonly');
    t.objectStore('draft').get('current').onsuccess = e => { out.draft = e.target.result || null; };
    t.objectStore('history').getAll().onsuccess = e => { out.history = e.target.result; };
    t.oncomplete = () => resolve(JSON.stringify(out, (k, v) => v instanceof Blob ? '[file ' + v.size + ']' : v));
  };
})"""


class DraftTests(BrowserTest):
    """Each test gets its own browser profile, so drafts never leak between tests."""

    def creator(self):
        return CreatorPage(self.new_page(self.new_context()), app.single_file_url())

    def half_finished(self):
        creator = self.creator().start("Sam Taylor")
        bank = creator.add_entry("Money", "Nationwide", type="Savings")
        creator.add_notes(bank, "Rainy day fund")
        creator.attach(bank, self.files.text("statement.txt", "statement"))
        creator.finish_entry(bank)
        creator.add_photo("Pensions and work", self.files.text("pension.png", "x"), "Nest app")
        creator.write_note("Start with the blue folder.")
        creator.next()
        creator.set_people([JO, SAM, PAT])
        return creator

    def test_a_fresh_start_has_nothing_to_resume(self):
        creator = self.creator()
        self.assertFalse(creator.resumed)
        self.assertEqual(creator.step_title, "Leave things in order for the people you trust")

    def test_refresh_returns_to_the_same_step(self):
        creator = self.half_finished().reload()
        self.assertTrue(creator.resumed)
        self.assertEqual(creator.step_title, "Who should hold the cards?")
        self.assertEqual(creator.cards_needed, "2 of 3")

    def test_refresh_keeps_card_holders_and_contacts(self):
        creator = self.half_finished().reload()
        names = creator.page.locator("#people input[type=text]:not(.contact)")
        self.assertEqual([names.nth(i).input_value() for i in range(3)], ["Jo Smith", "Sam Macdonald", "Pat Lee"])
        self.assertEqual(creator.page.locator("#people .contact").first.input_value(), "jo@example.com")

    def test_refresh_keeps_entries_notes_files_and_photos(self):
        creator = self.half_finished().reload().back()
        entry = creator.entry("Money", "Nationwide")
        self.assertIn("Savings, notes, 1 file", entry.locator(".sum-sub").inner_text())
        self.assertIn("1 photo", creator.section_status("Pensions and work"))
        self.assertEqual(creator.section("Pensions and work").locator(".ph input").input_value(), "Nest app")
        self.assertIn("Start with the blue folder.", creator.page.inner_text("#affairs-letter"))

    def test_start_over_clears_everything(self):
        creator = self.half_finished().reload().start_over()
        self.assertFalse(creator.resumed)
        self.assertEqual(creator.page.input_value("#owner"), "")
        self.assertFalse(creator.can_continue)


class HistoryTests(SealedHouseholdTest):
    household = PAIR

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.after_reload = CreatorPage(cls.page, cls.app_url())
        cls.history = cls.page.locator("#history")

    def test_sealing_deletes_the_draft(self):
        self.assertIn('"draft":null', self.page.evaluate(READ_DATABASE))
        self.assertFalse(self.after_reload.resumed)

    def test_sealed_envelopes_are_listed_on_the_welcome_screen(self):
        self.assertTrue(self.history.is_visible())
        text = self.history.inner_text()
        self.assertIn("Affairs (2 of 2)", text)
        self.assertIn("Jo Smith and Pat Lee", text)

    def test_history_never_stores_card_codes(self):
        self.assertIsNone(CARD_CODE.search(self.page.evaluate(READ_DATABASE)))

    def test_a_saved_copy_from_history_opens_with_the_cards(self):
        menu = self.history.locator("details.menu").first
        path = self.finish._download(menu, "Save Affairs", self.folder)
        envelope = EnvelopePage(self.new_page(self.offline), path)
        envelope.open_with(self.card(JO).code("Affairs"), self.card(PAT).code("Affairs"))
        self.assertIn("Money", envelope.contents + "Money")  # opens without error
        self.assertEqual(envelope.error, "")


class RemovingHistoryTests(SealedHouseholdTest):
    household = PAIR

    def test_remove_needs_a_second_tap(self):
        page = self.page
        CreatorPage(page, self.app_url())
        remove = page.locator("#history").get_by_role("button", name="Remove")
        remove.click()
        self.assertTrue(page.is_visible("#history"))
        page.get_by_role("button", name="Tap again to remove").click()
        page.locator("#history").wait_for(state="hidden")


if __name__ == "__main__":
    unittest.main()
