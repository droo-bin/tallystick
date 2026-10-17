"""Draws the Tallystick app icons: two tally-stick halves on the brand teal.
Run once; the PNGs are committed in src/icons/ and copied by build.js."""
import os
from PIL import Image, ImageDraw

TEAL, LIGHT = (31, 94, 87), (243, 245, 242)
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icons")
os.makedirs(out, exist_ok=True)

def draw(size, safe, rounded):
    s = size * 4  # supersample for smooth edges
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if rounded:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=TEAL)
    else:
        d.rectangle([0, 0, s, s], fill=TEAL)
    box = s * safe                      # the area the mark may use
    x0 = (s - box) / 2; y0 = (s - box) / 2
    w = box * 0.30; gap = box * 0.08; h = box * 0.86
    top = y0 + (box - h) / 2; r = w * 0.22
    left = x0 + (box - (2 * w + gap)) / 2
    right = left + w + gap
    d.rounded_rectangle([left, top, left + w, top + h], radius=r, fill=LIGHT)
    lw = max(4, int(w * 0.16))
    d.rounded_rectangle([right, top, right + w, top + h], radius=r, outline=LIGHT, width=lw)
    for f in (0.34, 0.58):            # the matching notches cut across both halves
        y = top + h * f
        d.rectangle([left - 1, y, right + w + 1, y + lw * 0.9], fill=TEAL)
        d.rectangle([right + lw, y, right + w - lw, y + lw * 0.9], fill=TEAL)
    return img.resize((size, size), Image.LANCZOS)

draw(192, 0.62, True).save(os.path.join(out, "icon-192.png"))
draw(512, 0.62, True).save(os.path.join(out, "icon-512.png"))
draw(512, 0.52, False).save(os.path.join(out, "maskable-512.png"))   # full bleed, mark inside the safe circle
draw(180, 0.60, False).convert("RGB").save(os.path.join(out, "apple-touch-icon.png"))
draw(32, 0.80, True).save(os.path.join(out, "favicon-32.png"))
print("icons written to", out)
