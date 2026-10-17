"""The hand-written QR encoder, checked against an independent decoder (OpenCV)."""
import json
import subprocess
import unittest
from pathlib import Path

try:
    import cv2
    import numpy as np
except ImportError:  # pragma: no cover
    cv2 = None

MATRIX_SCRIPT = Path(__file__).parent / "support" / "qr_matrix.js"
CARD_CODE = ("TALLY1-0171-2DB3-A504-38A8-CC03-0501-8A11-3E9F-A3B5-918C-5502-AE1D-822A-"
             "64E1-978D-D750-9441-7B64-FDA2-64AD-275A-8D73-EA7A-9F67")
CASES = {
    "a real card code": CARD_CODE,
    "the smallest symbol": "A",
    "short alphanumeric": "HELLO WORLD",
    "byte mode with accents": "Mixed case bytes: café",
    "another full-length code": "TALLY1-" + "-".join("%04X" % (i * 2654435761 % 65536) for i in range(24)),
}


def encode(texts):
    out = subprocess.run(["node", str(MATRIX_SCRIPT), json.dumps(texts)], check=True, capture_output=True, text=True)
    return json.loads(out.stdout)


def decode(matrix):
    modules = np.pad(np.array(matrix, dtype=np.uint8), 4)
    image = cv2.resize(((1 - modules) * 255).astype(np.uint8), (modules.shape[1] * 10, modules.shape[0] * 10),
                       interpolation=cv2.INTER_NEAREST)
    value, _, _ = cv2.QRCodeDetector().detectAndDecode(image)
    return value


@unittest.skipIf(cv2 is None, "needs opencv-python-headless and numpy")
class QrCodeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matrices = dict(zip(CASES, encode(list(CASES.values()))))

    def test_every_code_decodes_to_its_text(self):
        for name, text in CASES.items():
            with self.subTest(name):
                self.assertEqual(decode(self.matrices[name]), text)

    def test_card_codes_fit_a_version_6_symbol(self):
        self.assertEqual(len(self.matrices["a real card code"]), 41)


if __name__ == "__main__":
    unittest.main()
