<p align="center">
  <img src="docs/logo.svg" width="112" height="112" alt="Tallystick logo: two halves of a split tally stick">
</p>

<h1 align="center">Tallystick</h1>

<p align="center">Leave your affairs in order, sealed for the people you trust.<br>Free, private, offline.</p>

<p align="center"><strong><a href="https://droo-bin.github.io/tallystick/">Open Tallystick</a></strong> · <a href="https://droo-bin.github.io/tallystick/tallystick.html">Download the offline file</a></p>

Medieval tally sticks were split in two, and only the matching halves could prove a record. Tallystick does the
same with a key: it's split between the people you choose, and only enough of them together can open what you leave.

## Two ways to use it

- **Online, installable:** [droo-bin.github.io/tallystick](https://droo-bin.github.io/tallystick/). Open it on your phone or computer and add it to your home screen. After the first visit it works with no connection, and nothing you type is ever sent anywhere.
- **One offline file:** [tallystick.html](https://droo-bin.github.io/tallystick/tallystick.html), also attached to each [release](https://github.com/droo-bin/tallystick/releases) with a checksum. Save it and open it in any browser. It blocks all network access.

Both are built from this repo: `dist/pwa/` and `dist/tallystick.html`.

## Hosting the PWA (free)

The folder must be served over HTTPS (any real host does this).

- **GitHub Pages:** handled automatically by the GitHub Actions workflow below.
- **Cloudflare Pages / Netlify:** drag the `dist/pwa` folder into a new project.

Nothing is ever sent to the host: the service worker only serves the app's own files.

## Publishing with GitHub Actions

`.github/workflows/publish.yml` builds the app and runs every test on each push and pull request.

- **Pushes to `main`** publish the installable app to GitHub Pages, with the single offline file at `/tallystick.html`.
  One-time setup: in the repo, go to Settings › Pages and set Source to **GitHub Actions**.
- **Tags like `v1.0.0`** also create a GitHub release with `tallystick.html` and its SHA-256 checksum attached:
  `git tag v1.0.0 && git push origin v1.0.0`

## Building and testing

```
node build.js                                        # builds dist/tallystick.html and dist/pwa/
node --test test/crypto.test.js                      # crypto core (no installs needed)
python3 -m unittest discover -s test -p "test_*.py"  # browser tests
SLOW_STORAGE=1 python3 -m unittest discover -s test -p "test_*.py"  # again, with slow browser storage
```

The browser tests need `pip install playwright pillow numpy opencv-python-headless` and
`python3 -m playwright install chromium`. They build the app, serve the installable version locally and
drive both builds in a headless browser.

| File | What it covers |
| --- | --- |
| `test/crypto.test.js` | Key splitting, card codes, sealing and opening, typo and damage detection |
| `test/test_creating.py` | Filling things in: suggestions, photos, autofill, choosing how many cards |
| `test/test_sealing.py` | Sealing a household and opening every envelope, on both builds |
| `test/test_handing_out.py` | Share and Save menus, with and without a share sheet |
| `test/test_saving_progress.py` | Surviving a refresh, Start over, and the history of sealed envelopes |
| `test/test_media.py` | Voice notes and videos play while drafting and in opened envelopes |
| `test/test_accessibility.py` | Keyboard use, focus, headings, names and announcements |
| `test/test_installable_app.py` | Install metadata, offline use and phone layout |
| `test/test_qr.py` | QR codes decode with an independent reader |

Shared helpers live in `test/support/`: `app.py` (builds, browser, local server), `pages.py`
(page objects for the app, finish screen and envelopes), `data.py` (test households and files),
`fixtures.py` (base test classes) and `a11y.py` (accessibility checks).

## Not a will

Tallystick records information and wishes. It does not replace a legally valid will.
