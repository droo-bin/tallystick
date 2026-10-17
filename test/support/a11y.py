"""Accessibility checks run inside the page: every control has a name, and headings never skip a level."""

UNNAMED_CONTROLS = """() => {
  const shown = e => e.getClientRects().length > 0 || e.classList.contains('vh');
  const name = e => (e.getAttribute('aria-label')
    || (e.getAttribute('aria-labelledby') && (document.getElementById(e.getAttribute('aria-labelledby')) || {}).textContent)
    || (e.labels && [...e.labels].map(l => l.textContent).join(' '))
    || e.textContent || e.title || '').trim();
  return [...document.querySelectorAll('button, input, select, textarea, summary, a[href], [role=textbox], audio, video')]
    .filter(shown).filter(e => !name(e)).map(e => e.outerHTML.slice(0, 120));
}"""

HEADING_JUMPS = """() => {
  const levels = [...document.querySelectorAll('h1, h2, h3, h4, h5, h6')]
    .filter(h => h.getClientRects().length > 0).map(h => [+h.tagName[1], h.textContent.trim().slice(0, 40)]);
  const jumps = [];
  for (let i = 1; i < levels.length; i++)
    if (levels[i][0] > levels[i - 1][0] + 1) jumps.push(levels[i - 1][1] + ' -> ' + levels[i][1]);
  return jumps;
}"""

FOCUSED = """() => {
  const e = document.activeElement;
  return { tag: e.tagName, id: e.id, text: (e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 60),
           pressed: e.getAttribute('aria-pressed') };
}"""


def focused(page):
    return page.evaluate(FOCUSED)
