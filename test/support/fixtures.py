"""Base test classes. Each sets up its browser state once per class, so tests stay short and independent."""
import tempfile
import unittest
from pathlib import Path

from . import app
from .data import Files
from .pages import CreatorPage, EnvelopePage

# Replaces the browser's share sheet so tests can see what would have been shared.
SHARE_SHEET_STUB = """
navigator.canShare = () => true;
navigator.share = (d) => { window.__shared = { names: d.files.map(f => f.name), text: d.text, title: d.title }; return Promise.resolve(); };
"""
NO_SHARE_SHEET = "delete Navigator.prototype.canShare; delete Navigator.prototype.share;"


class BrowserTest(unittest.TestCase):
    """A fresh browser context per test class, plus an offline one for opening envelopes."""

    viewport = {"width": 420, "height": 900}
    init_script = None

    @classmethod
    def new_context(cls, **options):
        options.setdefault("viewport", cls.viewport)
        context = app.browser().new_context(accept_downloads=True, **options)
        if cls.init_script:
            context.add_init_script(cls.init_script)
        cls.addClassCleanup(context.close)
        return context

    @classmethod
    def setUpClass(cls):
        cls.context = cls.new_context()
        cls.offline = cls.new_context(offline=True)
        tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(tmp.cleanup)
        cls.folder = Path(tmp.name)
        cls.files = Files()
        cls.addClassCleanup(cls.files.cleanup)

    def new_page(self, context=None):
        page = (context or self.context).new_page()
        self.addCleanup(page.close)
        return page

    def open_envelope(self, path):
        """Opens an envelope file with the network switched off."""
        return EnvelopePage(self.new_page(self.offline), path)


class SealedHouseholdTest(BrowserTest):
    """Seals `household` once for the class, then exposes the finish screen, cards and envelope files.

    Subclasses set `household`, optionally `fill_affairs`, and `app_url` to test the other build.
    """

    household = None
    app_url = staticmethod(app.single_file_url)

    @classmethod
    def fill_affairs(cls, creator):
        pass

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page = cls.context.new_page()
        creator = CreatorPage(cls.page, cls.app_url())
        creator.fill_household(cls.household, affairs=cls.fill_affairs)
        cls.finish = creator.seal()
        cls.checks = cls.finish.check_results()
        cls.cards = cls.finish.cards()
        cls.envelopes = {name: cls.finish.save_envelope(name, cls.folder) for name in cls.checks}

    def card(self, person):
        return self.cards[person.name]
