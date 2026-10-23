from abc import ABC, abstractmethod
from pathlib import Path

from jagvis_chess.errors import InvalidPhoto


class Glasses(ABC):
    # Quand on aura le SDK des lunettes Meta, il suffira d'écrire une sous-classe.

    @abstractmethod
    def take_photo(self):
        """Renvoie la photo de l'échiquier (octets JPEG ou PNG)."""

    @abstractmethod
    def listen(self):
        """Renvoie la phrase dite par le joueur."""

    @abstractmethod
    def speak(self, text):
        """Dit le texte à voix haute."""

    @abstractmethod
    def show(self, text):
        """Affiche le texte dans les lunettes."""


class ConsoleGlasses(Glasses):
    # Lunettes simulées dans le terminal : la « photo » est un fichier image.

    def __init__(self, read=input, write=print):
        self.read = read
        self.write = write

    def take_photo(self):
        path = self.read("Photo path: ").strip().strip("'\"")
        try:
            return Path(path).read_bytes()
        except OSError as error:
            raise InvalidPhoto(f"Photo not found: {path}") from error

    def listen(self):
        return self.read("> ").strip()

    def speak(self, text):
        self.write(f"[Jarvis] {text}")

    def show(self, text):
        self.write(text)
