"""Lunettes : ce que Jarvis attend des lunettes connectées.

Lunettes est une interface (classe abstraite) : le jour où on aura le SDK des
lunettes Meta, il suffira d'écrire une nouvelle sous-classe. En attendant,
LunettesConsole utilise le terminal : la « photo » est un fichier image.
"""
from abc import ABC, abstractmethod
from pathlib import Path

from jagvis_echecs.erreurs import PhotoInvalide


class Lunettes(ABC):
    @abstractmethod
    def prendre_photo(self):
        """Renvoie la photo de ce que voit le joueur, en octets (JPEG ou PNG)."""

    @abstractmethod
    def ecouter(self):
        """Renvoie la phrase prononcée par le joueur."""

    @abstractmethod
    def parler(self, texte):
        """Dit le texte à voix haute."""

    @abstractmethod
    def afficher(self, texte):
        """Affiche le texte dans le verre des lunettes."""


class LunettesConsole(Lunettes):
    """Lunettes simulées dans le terminal. lire et ecrire sont injectables."""

    def __init__(self, lire=input, ecrire=print):
        self.lire = lire
        self.ecrire = ecrire

    def prendre_photo(self):
        chemin = self.lire("Chemin de la photo : ").strip().strip("'\"")
        try:
            return Path(chemin).read_bytes()
        except OSError as erreur:  # fichier absent, dossier, droits...
            raise PhotoInvalide(f"Photo introuvable : {chemin}") from erreur

    def ecouter(self):
        return self.lire("> ").strip()

    def parler(self, texte):
        self.ecrire(f"[Jarvis] {texte}")

    def afficher(self, texte):
        self.ecrire(texte)
