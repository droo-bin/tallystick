"""Behaviour while filling things in, before anything is sealed."""
import unittest

from support import app
from support.data import ALEX, JO, PAT, SAM
from support.fixtures import BrowserTest
from support.pages import CreatorPage


class CreatingTests(BrowserTest):
    def creator(self):
        """A fresh browser profile each time, so no saved draft carries over between tests."""
        return CreatorPage(self.new_page(self.new_context()), app.single_file_url())

    def test_cannot_start_without_a_name(self):
        creator = self.creator()
        self.assertFalse(creator.can_continue)
        creator.page.fill("#owner", "Sam Taylor")
        self.assertTrue(creator.can_continue)

    def test_browser_autofill_counts_as_typing(self):
        """Chrome's suggestion list can fill a box without a normal input event."""
        creator = self.creator()
        creator.page.eval_on_selector("#owner", "e => { e.value = 'Sam Taylor'; e.dispatchEvent(new Event('change', { bubbles: true })); }")
        self.assertTrue(creator.can_continue)

    def test_suggestions_can_be_added_more_than_once(self):
        creator = self.creator().start("Sam Taylor")
        for provider in ("Vanguard", "Hargreaves Lansdown"):
            creator.finish_entry(creator.add_entry("Money", "ISA", held_with=provider))
        self.assertEqual(creator.section("Money").locator(".entry .sum-title", has_text="ISA").count(), 2)

    def test_section_shows_photo_count_in_photo_mode(self):
        creator = self.creator().start("Sam Taylor")
        creator.add_photo("Pensions and work", self.files.text("pension.png", "x"), "Nest app")
        self.assertIn("1 photo", creator.section_status("Pensions and work"))

    def test_recommends_a_majority_of_card_holders(self):
        creator = self.creator().start("Sam Taylor").next()
        creator.set_people([JO, PAT])
        self.assertEqual(creator.cards_needed, "2 of 2")
        creator.set_people([JO, PAT, SAM, ALEX])
        self.assertEqual(creator.cards_needed, "3 of 4")

    def test_tapping_a_stick_changes_how_many_cards_are_needed(self):
        creator = self.creator().start("Sam Taylor").next()
        creator.set_people([JO, PAT, SAM])
        creator.page.get_by_role("button", name="Need 3 of 3 cards").click()
        self.assertEqual(creator.cards_needed, "3 of 3")
        self.assertIn("if one is lost it can never be opened", creator.page.inner_text("#k-explain"))

    def test_needs_two_card_holders_to_continue(self):
        creator = self.creator().start("Sam Taylor").next()
        creator.set_people([JO])
        self.assertFalse(creator.can_continue)


if __name__ == "__main__":
    unittest.main()
