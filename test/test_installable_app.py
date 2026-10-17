"""The installable build: install metadata, offline use, and phone layout."""
import unittest

from support import app
from support.fixtures import BrowserTest

IPHONE = "iPhone 13"


def controlled(page):
    """Waits until the service worker is installed and controlling the page.
    (The app's security policy forbids eval, so this avoids wait_for_function.)"""
    page.evaluate("navigator.serviceWorker.ready.then(() => true)")
    page.reload()
    page.evaluate("navigator.serviceWorker.ready.then(() => true)")
    assert page.evaluate("navigator.serviceWorker.controller !== null"), "service worker did not take control"


class PhoneTest(BrowserTest):
    """Every context in these tests behaves like an iPhone."""

    @classmethod
    def new_context(cls, **options):
        return super().new_context(**{**app.device(IPHONE), **options})


class InstallableAppTests(PhoneTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page = cls.context.new_page()
        cls.page.goto(app.pwa_url())
        controlled(cls.page)

    def test_manifest_describes_an_installable_app(self):
        manifest = self.page.evaluate("fetch('manifest.webmanifest').then(r => r.json())")
        self.assertEqual(manifest["display"], "standalone")
        self.assertTrue(any(icon["purpose"] == "maskable" for icon in manifest["icons"]))
        for icon in manifest["icons"]:
            with self.subTest(icon=icon["src"]):
                self.assertTrue(self.page.evaluate(f"fetch('{icon['src']}').then(r => r.ok)"))

    def test_caches_everything_it_needs(self):
        cached = self.page.evaluate("caches.keys().then(k => caches.open(k[0])).then(c => c.keys()).then(r => r.map(x => new URL(x.url).pathname))")
        for path in ["/", "/index.html", "/manifest.webmanifest", "/icons/icon-192.png"]:
            self.assertIn(path, cached)

    def test_iphone_users_see_how_to_install(self):
        self.assertTrue(self.page.is_visible("#install"))
        self.assertIn("Add to Home Screen", self.page.inner_text("#install-text"))

    def test_opens_with_no_connection(self):
        context = self.new_context()
        page = self.new_page(context)
        page.goto(app.pwa_url())
        controlled(page)
        context.set_offline(True)
        page.reload()
        page.wait_for_selector("html[data-ready]", state="attached")
        page.fill("#owner", "Sam Taylor")
        self.assertTrue(page.is_enabled("#next"))


class PhoneLayoutTests(PhoneTest):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.page = cls.context.new_page()
        cls.page.goto(app.single_file_url())
        cls.page.fill("#owner", "Sam Taylor")
        cls.page.click("#next")

    def test_never_scrolls_sideways(self):
        self.assertTrue(self.page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1"))

    def test_text_boxes_are_big_enough_that_iphones_do_not_zoom(self):
        small = self.page.evaluate("""[...document.querySelectorAll(
            'input:not([type=file]):not([type=checkbox]):not([type=radio]),select,textarea,[contenteditable]')]
            .filter(e => parseFloat(getComputedStyle(e).fontSize) < 16).map(e => e.id || e.className)""")
        self.assertEqual(small, [])

    def test_buttons_are_comfortable_to_tap(self):
        tiny = self.page.evaluate("""[...document.querySelectorAll('#screen-1 button, #screen-1 label.small')]
            .filter(e => e.offsetParent && e.getBoundingClientRect().height < 44).map(e => e.textContent.trim())""")
        self.assertEqual(tiny, [])


if __name__ == "__main__":
    unittest.main()
