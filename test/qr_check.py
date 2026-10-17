import json, subprocess, sys, os
import numpy as np, cv2

here = os.path.dirname(__file__)
texts = [
    "TALLY1-0171-2DB3-A504-38A8-CC03-0501-8A11-3E9F-A3B5-918C-5502-AE1D-822A-64E1-978D-D750-9441-7B64-FDA2-64AD-275A-8D73-EA7A-9F67",
    "HELLO WORLD", "A", "TALLY1-FFFF", "Mixed case bytes: café",
    "TALLY1-" + "-".join(["%04X" % (i * 2654435761 % 65536) for i in range(24)]),
]
out = subprocess.check_output(["node", os.path.join(here, "qr_dump.js"), json.dumps(texts)])
mats = json.loads(out)
det = cv2.QRCodeDetector()
ok = True
for t, m in zip(texts, mats):
    a = np.array(m, dtype=np.uint8)
    a = np.pad(a, 4)
    img = ((1 - a) * 255).astype(np.uint8)
    img = cv2.resize(img, (a.shape[1] * 10, a.shape[0] * 10), interpolation=cv2.INTER_NEAREST)
    val, pts, _ = det.detectAndDecode(img)
    good = val == t
    ok &= good
    print(("OK  " if good else "FAIL"), len(m), repr(val[:40]))
sys.exit(0 if ok else 1)
