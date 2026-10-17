<p align="center">
  <img src="docs/logo.svg" width="112" height="112" alt="Tallystick logo: two halves of a split tally stick">
</p>

<h1 align="center">Tallystick</h1>

<p align="center">Leave your affairs in order, sealed for the people you trust.<br>Free, private, offline.</p>

<p align="center"><strong><a href="https://tallystick.org.uk/">Open Tallystick</a></strong> · <a href="https://tallystick.org.uk/tallystick.html">Download the offline file</a></p>

Medieval tally sticks were split in two, and only the matching halves could prove a record. Tallystick does the
same with a key: it's split between the people you choose, and only enough of them together can open what you leave.

## Everything stays on your device

Tallystick runs entirely in your browser and works offline. There's no account, no server and no tracking:
what you write, the files you add and your sealed envelopes are never uploaded. The single offline file's
security rules block every network connection, and the installable app's rules only let it load its own files.
You can check this yourself by switching on airplane mode before you start: everything works the same.

## Two ways to use it

- **Online, installable:** [tallystick.org.uk](https://tallystick.org.uk/). Open it on your phone or computer and add it to your home screen. After the first visit it works with no connection, and nothing you type is ever sent anywhere.
- **One offline file:** [tallystick.html](https://tallystick.org.uk/tallystick.html), also attached to each [release](https://github.com/droo-bin/tallystick/releases) with a checksum. Save it and open it in any browser. It blocks all network access.

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
| `test/test_insecure_page.py` | A plain http:// page warns up front instead of failing at sealing |
| `test/test_qr.py` | QR codes decode with an independent reader |

Shared helpers live in `test/support/`: `app.py` (builds, browser, local server), `pages.py`
(page objects for the app, finish screen and envelopes), `data.py` (test households and files),
`fixtures.py` (base test classes) and `a11y.py` (accessibility checks).

## Disclaimer

**Tallystick is free software, provided "as is", without warranty of any kind**, express or implied, including any
warranty of fitness for a particular purpose, freedom from errors, or that envelopes will always open. You use it at
your own risk.

- **Not a will, and not advice.** Tallystick records information and wishes. It is not a will and doesn't make
  anything legally binding. Nothing in it is legal, financial, tax or medical advice. For a will, power of attorney
  or estate planning, speak to a solicitor or other qualified adviser.
- **You're responsible for your envelopes:** what you put in them, who holds the cards, keeping cards and copies
  safe, and testing them. If too many cards are lost, nobody can open the envelope, and the people who make
  Tallystick can't recover it.
- **Share lawfully.** Some services forbid sharing login details. Write where things are and who to contact, not
  passwords. People who open an envelope are responsible for acting lawfully with what they find.
- **Security has limits.** Tallystick uses standard, well-tested encryption, but its code hasn't been independently
  audited and no software is perfectly secure. Don't rely on it as the only record of anything important.
- **Privacy.** There are no accounts, analytics or tracking, and nothing you type is sent anywhere. The website is
  hosted on GitHub Pages, which may log basic technical details such as IP addresses. The offline file makes no
  connections at all.
- **Limit of liability.** As far as the law allows, the people who make and contribute to Tallystick aren't liable
  for any loss or damage arising from using it or being unable to use it. That includes lost data, money, access or
  opportunity, and any loss caused by an envelope that can't be opened or is opened by the wrong people. Nothing here
  limits liability that can't be limited by law, such as for death or personal injury caused by negligence, or for fraud.

These terms are governed by the law of England and Wales. The same terms appear in the app under
**Terms and disclaimer**.

## Licence

Tallystick is licensed under the [Apache License, Version 2.0](LICENSE). Sections 7 and 8 of the licence set out
the same "as is" and limitation of liability terms for anyone who uses, copies or changes the code.
