"""On a plain http:// page the browser switches off Web Crypto. The app must say so up front,
not let someone fill everything in and then fail when sealing."""
import unittest

from support import app
from support.data import PAIR
from support.fixtures import SealedHouseholdTest
from support.pages import CreatorPage

INSECURE_ORIGIN = "http://tallystick.test"  # not localhost, so the browser treats it as insecure


def serve_over_http(context, path, body):
    """Serves `body` at INSECURE_ORIGIN + path, so the page runs in a genuinely insecure context."""
    context.route(INSECURE_ORIGIN + path, lambda route: route.fulfill(
        status=200, content_type="text/html", body=body))
    return INSECURE_ORIGIN + path


class InsecurePageTests(SealedHouseholdTest):
    household = PAIR

    def page_over_http(self, path, body):
        context = self.new_context()
        url = serve_over_http(context, path, body)
        page = self.new_page(context)
        page.goto(url)
        self.assertFalse(page.evaluate("isSecureContext"), "the test page should be insecure")
        return page

    def creator_over_http(self):
        app.ensure_built()
        html = app.SINGLE_FILE.read_text()
        page = self.page_over_http("/", html)
        page.wait_for_selector("html[data-ready]", state="attached")
        return page

    def test_warns_before_anything_is_typed_and_links_to_the_https_version(self):
        page = self.creator_over_http()
        warning = page.locator("#insecure")
        self.assertTrue(warning.is_visible())
        self.assertIn("isn't secure", warning.inner_text())
        self.assertEqual(page.get_attribute("#secure-link", "href"), "https://tallystick.test/")

    def test_cannot_start_on_an_insecure_page(self):
        page = self.creator_over_http()
        page.fill("#owner", "Sam Taylor")
        self.assertFalse(page.is_enabled("#next"))
        self.assertIn("isn't secure", page.inner_text("#foot-msg"))

    def test_the_secure_app_shows_no_warning(self):
        self.assertFalse(CreatorPage(self.new_page(), self.app_url()).page.is_visible("#insecure"))

    def test_an_envelope_on_an_insecure_page_explains_how_to_open_it(self):
        page = self.page_over_http("/affairs.html", self.envelopes["Affairs"].read_text())
        self.assertIn("Save this file to your device", page.inner_text("#error"))
        self.assertFalse(page.is_enabled("#open"))


if __name__ == "__main__":
    unittest.main()
