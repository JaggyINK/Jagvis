"""Glasses: what Jarvis needs from the smart glasses.

Glasses is an interface (an abstract class). When we get the Meta glasses SDK,
we just write a new subclass. Until then, ConsoleGlasses uses the terminal:
the "photo" is an image file on the disk.
"""
from abc import ABC, abstractmethod
from pathlib import Path

from jagvis_chess.errors import InvalidPhoto


class Glasses(ABC):
    @abstractmethod
    def take_photo(self):
        """Give the photo of what the player sees, as bytes (JPEG or PNG)."""

    @abstractmethod
    def listen(self):
        """Give the sentence said by the player."""

    @abstractmethod
    def speak(self, text):
        """Say the text out loud."""

    @abstractmethod
    def show(self, text):
        """Show the text in the glasses."""


class ConsoleGlasses(Glasses):
    """Glasses faked in the terminal. read and write can be swapped in tests."""

    def __init__(self, read=input, write=print):
        self.read = read
        self.write = write

    def take_photo(self):
        path = self.read("Photo path: ").strip().strip("'\"")
        try:
            return Path(path).read_bytes()
        except OSError as error:  # missing file, folder, no rights...
            raise InvalidPhoto(f"Photo not found: {path}") from error

    def listen(self):
        return self.read("> ").strip()

    def speak(self, text):
        self.write(f"[Jarvis] {text}")

    def show(self, text):
        self.write(text)
