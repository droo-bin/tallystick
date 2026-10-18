"""Voice notes and videos can be recorded in the browser and end up in the sealed envelopes, ready to play.

The test browser runs with a fake camera and microphone, so recording works without real hardware."""
import unittest

from support import app
from support.data import JO, PAT, Envelope, Household
from support.fixtures import BrowserTest
from support.pages import CreatorPage, FinishScreen

DURATION = """sel => new Promise(resolve => {
  const m = document.querySelector(sel);
  if (!m) return resolve(-2);
  const done = () => resolve(isFinite(m.duration) ? m.duration : -3);
  if (m.readyState >= 1 && isFinite(m.duration)) return done();
  m.addEventListener('durationchange', () => isFinite(m.duration) && done());
  m.onerror = () => resolve(-1);
  setTimeout(done, 5000);
  m.load();
})"""


class RecordingTests(BrowserTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page = cls.context.new_page()
        creator = CreatorPage(cls.page, app.single_file_url())
        creator.start("Sam Taylor")
        funeral = creator.section("Wishes").locator(".entry", has=cls.page.locator(".sum-title", has_text="Funeral"))
        if "open" not in funeral.get_attribute("class"):
            funeral.locator("button.sum").click()
        creator.record("Record a voice note for Funeral")
        cls.funeral_files = funeral.locator(".files audio.player").count()
        creator.record("Record a voice note for whoever opens this")
        creator.next()
        creator.set_people([JO, PAT])
        creator.next()
        creator.add_envelope(Envelope("Letter to Jo", "Dear Jo.", (JO, PAT)), [JO, PAT])
        creator.record("Record a video for this envelope", seconds=2)
        cls.extra_videos = cls.page.locator("#extras video.player").count()
        cls.page.wait_for_timeout(700)  # autosave
        cls.restored = CreatorPage(cls.page, app.single_file_url())
        cls.restored_videos = cls.page.locator("#extras video.player").count()
        cls.restored.next()
        cls.finish = cls.restored.seal()
        cls.cards = cls.finish.cards()
        cls.envelopes = {n: cls.finish.save_envelope(n, cls.folder) for n in ("Affairs", "Letter to Jo")}

    def opened(self, name):
        codes = [self.cards[p.name].code(name) for p in (JO, PAT)]
        return self.open_envelope(self.envelopes[name]).open_with(*codes)

    def test_record_buttons_only_where_they_make_sense(self):
        money = CreatorPage(self.new_page(self.new_context()), app.single_file_url()).start("Sam Taylor")
        bank = money.add_entry("Money", "Nationwide")
        self.assertEqual(bank.get_by_role("button", name="Record a voice note for Nationwide").count(), 0)
        self.assertEqual(money.page.get_by_role("button", name="Record a voice note for whoever opens this").count(), 1)

    def test_recording_is_added_to_the_entry_and_plays(self):
        self.assertEqual(self.funeral_files, 1)

    def test_video_is_added_to_the_extra_envelope(self):
        self.assertEqual(self.extra_videos, 1)

    def test_recordings_survive_a_refresh(self):
        self.assertEqual(self.restored_videos, 1)

    def test_voice_notes_play_in_the_opened_affairs_envelope(self):
        env = self.opened("Affairs")
        self.assertEqual(env.count("audio.player"), 2)
        self.assertGreater(env.page.evaluate(DURATION, "#opened audio.player"), 0.5)

    def test_video_plays_in_the_opened_extra_envelope(self):
        env = self.opened("Letter to Jo")
        self.assertEqual(env.count("video.player"), 1)
        self.assertGreater(env.page.evaluate(DURATION, "#opened video.player"), 1.0)


class RecorderDialogTests(BrowserTest):
    def test_cancel_keeps_nothing_and_returns_focus(self):
        creator = CreatorPage(self.new_page(self.new_context()), app.single_file_url()).start("Sam Taylor")
        btn = creator.page.get_by_role("button", name="Record a voice note for whoever opens this")
        btn.click()
        dialog = creator.page.locator("#recorder")
        dialog.get_by_role("button", name="Start recording").wait_for()
        self.assertIn("stays on this device", dialog.inner_text())
        dialog.get_by_role("button", name="Cancel").click()
        dialog.wait_for(state="hidden")
        self.assertEqual(creator.page.evaluate("document.activeElement.getAttribute('aria-label')"), "Record a voice note for whoever opens this")
        self.assertEqual(creator.page.locator("#affairs-filelist audio").count(), 0)

    def test_escape_closes_the_recorder(self):
        creator = CreatorPage(self.new_page(self.new_context()), app.single_file_url()).start("Sam Taylor")
        creator.page.get_by_role("button", name="Record a video for whoever opens this").click()
        creator.page.locator("#recorder").get_by_role("button", name="Start recording").wait_for()
        creator.page.keyboard.press("Escape")
        creator.page.locator("#recorder").wait_for(state="hidden")


if __name__ == "__main__":
    unittest.main()
