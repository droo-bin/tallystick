"""Voice notes and videos play in the app while drafting and in the opened envelope, using the browser's own players."""
import unittest

from support.data import Household, JO, PAT
from support.fixtures import SealedHouseholdTest

LOAD_FIRST_AUDIO = """sel => new Promise(resolve => {
  const a = document.querySelector(sel);
  if (!a) return resolve(-2);
  if (a.readyState >= 1) return resolve(a.duration);
  a.onloadedmetadata = () => resolve(a.duration);
  a.onerror = () => resolve(-1);
  a.load();
})"""


class MediaTests(SealedHouseholdTest):
    household = Household(owner="Sam Taylor", people=[JO, PAT])
    blocked = []

    @classmethod
    def fill_affairs(cls, creator):
        creator.page.on("console", lambda m: "Content Security Policy" in m.text and cls.blocked.append(m.text))
        entry = creator.add_entry("People and pets", "Add a person", name="Mum")
        creator.attach(entry, cls.files.wav())
        cls.drafting_audio = creator.page.evaluate(LOAD_FIRST_AUDIO, ".entry audio.player")
        creator.finish_entry(entry)
        creator.add_photo("Wishes", cls.files.text("goodbye.mp4", "not really a video"), "A message for everyone")
        cls.drafting_video = creator.section("Wishes").locator(".ph video.player").count()

    def open_affairs(self):
        return self.open_envelope(self.envelopes["Affairs"]).open_with(self.card(JO).code("Affairs"), self.card(PAT).code("Affairs"))

    def test_voice_note_plays_while_drafting(self):
        self.assertAlmostEqual(self.drafting_audio, 1.0, places=1)

    def test_video_gets_a_player_while_drafting(self):
        self.assertEqual(self.drafting_video, 1)

    def test_voice_note_plays_in_the_opened_envelope(self):
        envelope = self.open_affairs()
        self.assertAlmostEqual(envelope.page.evaluate(LOAD_FIRST_AUDIO, "#opened audio.player"), 1.0, places=1)

    def test_video_gets_a_player_and_caption_in_the_opened_envelope(self):
        envelope = self.open_affairs()
        self.assertEqual(envelope.count(".gallery video.player"), 1)
        self.assertIn("A message for everyone", envelope.contents)

    def test_security_policy_allows_the_players(self):
        self.assertEqual(self.blocked, [])


if __name__ == "__main__":
    unittest.main()
