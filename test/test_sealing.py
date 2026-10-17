"""Sealing a household and opening its envelopes, on both builds."""
import itertools
import re
import unittest

from support import app
from support.data import ALEX, JO, PAT, SAM, TAYLORS
from support.fixtures import SealedHouseholdTest

STAMP = re.compile(r"\d{1,2} \w+ \d{4}(?:,| at) \d{2}:\d{2} (?:BST|GMT|UTC|GMT[+-]\d+)")
CARD_HOLDER_NAMES = [p.name for p in TAYLORS.people]
INJECTION = ('<img src=x onerror="window.pwned=1"><script>window.pwned=2</script>'
             '<a href="javascript:alert(1)">link</a>')


class SealingTests(SealedHouseholdTest):
    household = TAYLORS

    @classmethod
    def fill_affairs(cls, creator):
        bank = creator.add_entry("Money", "Nationwide", type="Current")
        notes = creator.add_notes(bank, "Salary goes in here. ", bold="Close last")
        notes.evaluate("(e, html) => { e.innerHTML += html; e.dispatchEvent(new Event('input')); }", INJECTION)
        creator.attach(bank, cls.files.text("statement.txt", "Nationwide statement"))
        creator.finish_entry(bank)
        for provider in ("Vanguard", "Hargreaves Lansdown"):
            creator.finish_entry(creator.add_entry("Money", "ISA", held_with=provider))
        creator.attach_to_section("Money", cls.files.text("deeds.txt", "Deeds scan"))
        creator.add_photo("Pensions and work", cls.files.big_png(), "Nest pension app")
        creator.pick("Wishes", "With my solicitor")
        creator.pick("Wishes", "Cremation")
        creator.write_note("Don't panic. It's all here.")

    def open_affairs(self, *people):
        return self.open_envelope(self.envelopes["Affairs"]).open_with(*(self.card(p).code("Affairs") for p in people))

    # The finish screen
    def test_reports_sealed_and_checked(self):
        self.assertEqual(self.finish.heading, "Sealed and checked")
        self.assertIn("3 envelopes, a Start here file and 4 cards", self.finish.summary)

    def test_every_envelope_passes_its_self_check(self):
        self.assertEqual(set(self.checks), {"Affairs", "Letter to Sam", "Contents list", "Start here"})
        for name, result in self.checks.items():
            with self.subTest(envelope=name):
                self.assertIn("Contents match exactly", result)

    def test_envelope_menu_saves_each_envelope_or_all_of_them(self):
        self.assertEqual(self.finish.menu_items(self.finish.envelope_menu),
                         ["Save – Affairs", "Save – Letter to Sam", "Save – Contents list", "Save – Start here", "Save all"])

    # Cards
    def test_each_card_holds_codes_only_for_its_envelopes(self):
        self.assertEqual(set(self.card(JO).codes), {"Affairs", "Letter to Sam", "Contents list", "Start here"})
        self.assertEqual(set(self.card(PAT).codes), {"Affairs", "Contents list", "Start here"})

    def test_cards_name_the_other_holders(self):
        self.assertIn("The other cards are held by Sam Macdonald, Pat Lee and Alex Macdonald", self.card(JO).text)
        self.assertIn("The other cards are held by Sam Macdonald.", self.card(JO).text)

    def test_cards_show_how_to_reach_the_others(self):
        self.assertIn("Pat Lee · Friend · 07700 900123", self.card(JO).text)
        self.assertNotIn("Jo Smith · Executor", self.card(JO).text)

    def test_cards_and_envelopes_carry_the_same_creation_time(self):
        stamp = STAMP.search(self.card(JO).text)
        self.assertIsNotNone(stamp)
        self.assertIn(stamp.group(0), self.open_envelope(self.envelopes["Affairs"]).locked_text)

    # Opening the Affairs envelope
    def test_any_three_of_four_cards_open_affairs(self):
        for trio in itertools.combinations(TAYLORS.people, 3):
            with self.subTest(cards=[p.name for p in trio]):
                self.assertIn("Nationwide", self.open_affairs(*trio).contents)

    def test_affairs_keeps_everything_written(self):
        contents = self.open_affairs(SAM, ALEX, PAT).contents
        for expected in ["Type: Current", "Salary goes in here", "statement.txt", "deeds.txt",
                         "With my solicitor", "Cremation", "Don't panic", "Nest pension app"]:
            with self.subTest(expected=expected):
                self.assertIn(expected, contents)

    def test_repeated_entries_are_all_kept(self):
        contents = self.open_affairs(SAM, ALEX, PAT).contents
        self.assertIn("Vanguard", contents)
        self.assertIn("Hargreaves Lansdown", contents)

    def test_rich_text_keeps_formatting_but_not_scripts(self):
        envelope = self.open_affairs(SAM, ALEX, PAT)
        self.assertEqual(envelope.count(".rich strong:has-text('Close last')"), 1)
        self.assertEqual(envelope.count(".rich img, .rich script, .rich a"), 0)
        self.assertIsNone(envelope.js("window.pwned"))

    def test_large_photos_are_shrunk_to_jpeg(self):
        envelope = self.open_affairs(SAM, ALEX, PAT)
        self.assertEqual(envelope.count(".gallery img"), 1)
        self.assertTrue(envelope.page.locator("#opened .gallery a").get_attribute("download").endswith(".jpg"))

    def test_too_few_cards_are_refused(self):
        self.assertIn("Enter 3 card codes. 2 entered so far.", self.open_affairs(SAM, ALEX).error)

    def test_the_same_card_twice_does_not_count(self):
        code = self.card(SAM).code("Affairs")
        envelope = self.open_envelope(self.envelopes["Affairs"]).open_with(code, code, self.card(PAT).code("Affairs"))
        self.assertIn("needs 3 different cards", envelope.error)

    def test_a_card_for_another_envelope_is_refused(self):
        envelope = self.open_envelope(self.envelopes["Affairs"])
        envelope.open_with(self.card(JO).code("Letter to Sam"), self.card(SAM).code("Affairs"), self.card(PAT).code("Affairs"))
        self.assertIn("belongs to a different envelope", envelope.error)

    def test_a_mistyped_code_is_caught(self):
        code = self.card(JO).code("Affairs")
        typo = code[:20] + ("B" if code[20] == "A" else "A") + code[21:]
        envelope = self.open_envelope(self.envelopes["Affairs"]).open_with(typo, self.card(SAM).code("Affairs"), self.card(PAT).code("Affairs"))
        self.assertIn("typo", envelope.error)

    def test_codes_can_be_typed_in_lowercase_with_spaces(self):
        codes = [self.card(p).code("Affairs").lower().replace("-", " ") for p in (JO, SAM, PAT)]
        self.assertIn("Nationwide", self.open_envelope(self.envelopes["Affairs"]).open_with(*codes).contents)

    # Other envelopes
    def test_private_letter_opens_for_its_two_holders(self):
        envelope = self.open_envelope(self.envelopes["Letter to Sam"])
        envelope.open_with(self.card(SAM).code("Letter to Sam"), self.card(JO).code("Letter to Sam"))
        self.assertIn("Dear Sam", envelope.contents)

    def test_contents_list_says_where_copies_are_but_names_no_one(self):
        envelope = self.open_envelope(self.envelopes["Contents list"])
        contents = envelope.open_with(self.card(PAT).code("Contents list"), self.card(ALEX).code("Contents list")).contents
        self.assertIn("Grey filing cabinet", contents)
        self.assertIn("any 3 of its 4 cards", contents)
        for name in CARD_HOLDER_NAMES:
            self.assertNotIn(name, contents)

    def test_start_here_opens_with_one_card_and_lists_everyone(self):
        envelope = self.open_envelope(self.envelopes["Start here"])
        self.assertIn("Open with your card", envelope.heading)
        contents = envelope.open_with(self.card(PAT).code("Start here")).contents
        self.assertIn("Your card works", contents)
        for expected in CARD_HOLDER_NAMES + ["Executor", "07700 900123", "needs 3 cards", "Grey filing cabinet"]:
            self.assertIn(expected, contents)

    def test_start_here_refuses_a_real_envelope_code(self):
        envelope = self.open_envelope(self.envelopes["Start here"]).open_with(self.card(PAT).code("Affairs"))
        self.assertIn("different envelope", envelope.error)

    # Privacy of the files themselves
    def test_envelope_files_store_no_names(self):
        for name, path in self.envelopes.items():
            with self.subTest(envelope=name):
                text = path.read_text()
                for person in CARD_HOLDER_NAMES:
                    self.assertNotIn(person, text)


class SealingInstallableAppTests(SealingTests):
    """The same behaviour from the installable build, served over HTTP."""
    app_url = staticmethod(app.pwa_url)


if __name__ == "__main__":
    unittest.main()
