"""Handing cards out: Share and Save on the finish screen, with and without a share sheet."""
import re
import unittest

from support.data import JO, PAIR, PAT, TAYLORS
from support.fixtures import NO_SHARE_SHEET, SHARE_SHEET_STUB, SealedHouseholdTest


class WithShareSheetTests(SealedHouseholdTest):
    household = TAYLORS
    init_script = SHARE_SHEET_STUB

    def setUp(self):
        self.finish.include_envelopes(True)

    def test_explains_what_share_does(self):
        self.assertTrue(self.page.is_visible("#share-info"))

    def test_share_sends_a_card_with_only_that_persons_envelopes(self):
        jo, pat = self.finish.share_with(JO.name)["names"], self.finish.share_with(PAT.name)["names"]
        self.assertEqual(jo[0], "Tallystick card - Jo Smith.html")
        self.assertEqual(len(jo), 5)
        self.assertTrue(any("Letter to Sam" in n for n in jo))
        self.assertEqual(len(pat), 4)
        self.assertFalse(any("Letter to Sam" in n for n in pat))
        self.assertTrue(any("Start here" in n for n in pat))

    def test_share_message_explains_the_attachments(self):
        shared = self.finish.share_with(JO.name)
        self.assertTrue(shared["text"].startswith("Hi Jo"))
        self.assertIn("copies of my sealed envelopes are attached", shared["text"])

    def test_each_row_says_what_will_be_sent(self):
        self.assertIn("Card and 3 envelopes", self.finish.send_row(PAT.name).inner_text())

    def test_save_menu_lists_each_file_then_save_all(self):
        items = self.finish.menu_items(self.finish.save_menu_for(PAT.name))
        self.assertEqual(items, ["Save – Card", "Save – Affairs", "Save – Contents list", "Save – Start here", "Save all"])

    def test_each_save_menu_item_downloads_one_file(self):
        path = self.finish.save_for(PAT.name, self.folder, item="Affairs")
        self.assertIn("Affairs", path.name)
        self.assertIn("Sealed envelope", path.read_text())

    def test_card_only_when_envelopes_are_left_out(self):
        self.finish.include_envelopes(False)
        shared = self.finish.share_with(JO.name)
        self.assertEqual(shared["names"], ["Tallystick card - Jo Smith.html"])
        self.assertIn("Your card is attached", shared["text"])
        self.assertIn("Card only", self.finish.send_row(PAT.name).inner_text())
        self.assertEqual(self.finish.menu_items(self.finish.save_menu_for(PAT.name)), ["Save – Card"])


class WithoutShareSheetTests(SealedHouseholdTest):
    household = PAIR
    init_script = NO_SHARE_SHEET

    def setUp(self):
        self.finish.include_envelopes(False)

    def test_hides_share_buttons_and_wording(self):
        self.assertFalse(self.page.is_visible("#share-info"))
        self.assertEqual(self.page.locator("#send-list").get_by_role("button", name=re.compile("^Share")).count(), 0)

    def test_still_offers_saving_for_everyone(self):
        self.assertEqual(self.page.locator("#send-list details.menu").count(), 2)

    def test_saving_gives_one_card_file_with_its_creation_time(self):
        card = self.finish.save_for(PAT.name, self.folder).read_text()
        self.assertEqual(card.count('class="card"'), 1)
        self.assertIn("Pat Lee", card)
        self.assertRegex(card, r"Created \d{1,2} \w+ \d{4}")


if __name__ == "__main__":
    unittest.main()
