"""Test data: the people, files and household used across the browser tests."""
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Person:
    name: str
    role: str
    contact: str = ""


@dataclass(frozen=True)
class Envelope:
    name: str
    text: str
    holders: tuple


@dataclass
class Household:
    owner: str
    people: list
    extra_envelopes: list = field(default_factory=list)
    other_place: str = ""


JO = Person("Jo Smith", "Executor", "jo@example.com")
SAM = Person("Sam Macdonald", "Family")
PAT = Person("Pat Lee", "Friend", "07700 900123")
ALEX = Person("Alex Macdonald", "Family")

# The household most tests seal: four card holders, Affairs needs 3 of 4, a private letter for two of them.
TAYLORS = Household(
    owner="Sam Taylor",
    people=[JO, SAM, PAT, ALEX],
    extra_envelopes=[Envelope("Letter to Sam", "Dear Sam, you were the best thing.", (JO, SAM))],
    other_place="Grey filing cabinet",
)

# The smallest household that can be sealed.
PAIR = Household(owner="Sam Taylor", people=[JO, PAT])


class Files:
    """Throwaway files to attach, made once per test class."""

    def __init__(self):
        self._dir = tempfile.TemporaryDirectory()
        self.root = Path(self._dir.name)

    def text(self, name, body):
        path = self.root / name
        path.write_text(body)
        return path

    def big_png(self, name="pension.png", size=(2600, 1800)):
        """A photo-sized PNG (about 14 MB) that the app should shrink before sealing."""
        from PIL import Image
        path = self.root / name
        Image.frombytes("RGB", size, os.urandom(size[0] * size[1] * 3)).save(path)
        return path

    def wav(self, name="voice-note.wav", seconds=1):
        """A short, valid WAV recording (a quiet tone)."""
        import math, struct, wave
        path = self.root / name
        with wave.open(str(path), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(8000)
            w.writeframes(b"".join(struct.pack("<h", int(3000 * math.sin(i / 8))) for i in range(8000 * seconds)))
        return path

    def cleanup(self):
        self._dir.cleanup()
