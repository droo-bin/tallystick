"""Keyboard and screen reader support: names, headings, focus, live announcements."""
import unittest

from support import app
from support.a11y import HEADING_JUMPS, UNNAMED_CONTROLS, focused
from support.data import JO, PAIR, PAT, SAM
from support.fixtures import BrowserTest, SealedHouseholdTest
from support.pages import CreatorPage

STEPS = ["Leave things in order for the people you trust", "Your affairs", "Who should hold the cards?",
         "Anything more private?", "Where will you keep copies?"]


class EveryScreenTests(BrowserTest):
    """Walks each step once and checks it for screen reader basics."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page = cls.context.new_page()
        creator = CreatorPage(cls.page, app.single_file_url())
        cls.screens = {}
        cls.screens[STEPS[0]] = cls.snapshot()
        creator.start("Sam Taylor")
        creator.section("Money")
        cls.screens[STEPS[1]] = cls.snapshot()
        creator.next()
        arrived = focused(cls.page)
        creator.set_people([JO, PAT])
        cls.screens[STEPS[2]] = {**cls.snapshot(), "focus": arrived}
        creator.next()
        cls.screens[STEPS[3]] = cls.snapshot()
        creator.next()
        cls.screens[STEPS[4]] = cls.snapshot()

    @classmethod
    def snapshot(cls):
        return {"unnamed": cls.page.evaluate(UNNAMED_CONTROLS), "jumps": cls.page.evaluate(HEADING_JUMPS),
                "focus": focused(cls.page), "title": cls.page.title()}

    def test_every_control_has_a_name(self):
        for screen, found in self.screens.items():
            with self.subTest(screen=screen):
                self.assertEqual(found["unnamed"], [])

    def test_headings_never_skip_a_level(self):
        for screen, found in self.screens.items():
            with self.subTest(screen=screen):
                self.assertEqual(found["jumps"], [])

    def test_each_step_moves_focus_to_its_heading(self):
        for screen in STEPS[1:]:
            with self.subTest(screen=screen):
                self.assertEqual(self.screens[screen]["focus"]["tag"], "H1")
                self.assertEqual(self.screens[screen]["focus"]["text"], screen)

    def test_page_title_names_the_step(self):
        self.assertEqual(self.screens[STEPS[2]]["title"], "Card holders – Tallystick")


class KeyboardTests(BrowserTest):
    def creator(self):
        return CreatorPage(self.new_page(self.new_context()), app.single_file_url())

    def test_skip_link_is_the_first_stop_and_jumps_to_content(self):
        page = self.creator().page
        page.keyboard.press("Tab")
        self.assertEqual(focused(page)["text"], "Skip to content")
        page.keyboard.press("Enter")
        self.assertEqual(focused(page)["id"], "main")

    def test_the_first_step_can_be_done_with_the_keyboard(self):
        creator = self.creator()
        creator.page.focus("#owner")
        creator.page.keyboard.type("Sam Taylor")
        creator.page.focus("#next")
        creator.page.keyboard.press("Enter")
        self.assertEqual(creator.step_title, "Your affairs")

    def test_adding_a_suggestion_moves_focus_into_the_new_entry(self):
        creator = self.creator().start("Sam Taylor")
        creator.section("Money").get_by_role("button", name="Add ISA").press("Enter")
        self.assertEqual(focused(creator.page)["tag"], "INPUT")

    def test_show_more_moves_focus_to_the_first_new_suggestion(self):
        creator = self.creator().start("Sam Taylor")
        creator.section("Money").get_by_role("button", name="Show 6 more suggestions").press("Enter")
        self.assertEqual(focused(creator.page)["text"], "Add Santander")

    def test_choosing_cards_needed_keeps_focus_on_the_chosen_stick(self):
        creator = self.creator().start("Sam Taylor").next()
        creator.set_people([JO, PAT, SAM])
        creator.page.get_by_role("button", name="Need 3 of 3 cards").press("Enter")
        self.assertEqual(focused(creator.page)["pressed"], "true")
        self.assertEqual(creator.cards_needed, "3 of 3")

    def test_adding_a_card_holder_focuses_their_name(self):
        creator = self.creator().start("Sam Taylor").next()
        creator.page.get_by_role("button", name="Add a person").press("Enter")
        self.assertEqual(focused(creator.page)["text"], "Card holder 4 name")

    def test_removing_a_card_holder_keeps_focus_in_the_list(self):
        creator = self.creator().start("Sam Taylor").next()
        creator.set_people([JO, PAT, SAM])
        creator.page.get_by_role("button", name="Remove Pat Lee").press("Enter")
        self.assertEqual(focused(creator.page)["text"], "Card holder 2 name")

    def test_changes_are_announced(self):
        page = self.creator().page
        for region in ("#foot-msg", "#k-explain", "#people-hints"):
            with self.subTest(region=region):
                self.assertEqual(page.get_attribute(region, "aria-live"), "polite")

    def test_protection_is_explained_in_plain_terms(self):
        page = self.creator().page
        page.locator("#how-safe summary").press("Enter")
        text = page.inner_text("#how-safe")
        self.assertIn("any three pieces show the way, but two pieces show nothing", text)
        self.assertIn("Nothing leaves your device", text)

    def test_terms_link_opens_the_disclaimer_and_moves_focus_to_it(self):
        page = self.creator().page
        self.assertIn("Not a will or legal advice", page.inner_text(".legal-line"))
        page.get_by_role("link", name="Read the terms").press("Enter")
        self.assertTrue(page.locator("#terms").evaluate("d => d.open"))
        self.assertEqual(focused(page)["text"], "Terms and disclaimer")
        text = page.inner_text("#terms")
        self.assertIn('provided "as is", without any warranty', text)
        self.assertIn("It is not a will", text)
        self.assertIn("As far as the law allows", text)


class SealedKeyboardTests(SealedHouseholdTest):
    household = PAIR

    def test_save_menu_opens_and_moves_with_arrow_keys(self):
        summary = self.finish.envelope_menu.locator("summary")
        summary.focus()
        self.page.keyboard.press("ArrowDown")
        self.assertEqual(focused(self.page)["text"], "Save Affairs")
        self.page.keyboard.press("ArrowDown")
        self.assertEqual(focused(self.page)["text"], "Save Contents list")
        self.page.keyboard.press("End")
        self.assertIn("Save all", focused(self.page)["text"])
        self.page.keyboard.press("Escape")
        self.assertFalse(self.finish.envelope_menu.evaluate("d => d.open"))
        self.assertEqual(focused(self.page)["tag"], "SUMMARY")

    def test_finish_screen_has_named_controls_and_ordered_headings(self):
        self.assertEqual(self.page.evaluate(UNNAMED_CONTROLS), [])
        self.assertEqual(self.page.evaluate(HEADING_JUMPS), [])

    def test_opening_an_envelope_moves_focus_to_its_contents(self):
        envelope = self.open_envelope(self.envelopes["Affairs"])
        self.assertEqual(envelope.page.evaluate(UNNAMED_CONTROLS), [])
        envelope.open_with(self.card(JO).code("Affairs"), self.card(PAT).code("Affairs"))
        self.assertTrue(envelope.page.evaluate("!!document.activeElement.closest('#opened')"))
        self.assertEqual(envelope.page.evaluate(HEADING_JUMPS), [])


if __name__ == "__main__":
    unittest.main()
