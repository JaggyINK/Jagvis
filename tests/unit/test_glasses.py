import pytest

from jagvis_chess.errors import InvalidPhoto
from jagvis_chess.glasses import ConsoleGlasses, Glasses


class FakeTerminal:
    # Remplace input() et print().

    def __init__(self, answers=()):
        self.answers = list(answers)
        self.questions = []
        self.outputs = []

    def read(self, question):
        self.questions.append(question)
        return self.answers.pop(0)

    def write(self, text):
        self.outputs.append(text)


def console_glasses(*answers):
    terminal = FakeTerminal(answers)
    return ConsoleGlasses(read=terminal.read, write=terminal.write), terminal


def test_GLS01_glasses_is_an_interface():
    with pytest.raises(TypeError):
        Glasses()

    class HalfGlasses(Glasses):
        def speak(self, text):
            pass

    with pytest.raises(TypeError):
        HalfGlasses()


def test_GLS02_speak_show_listen():
    glasses, terminal = console_glasses("  advice  ")

    glasses.speak("Play e4.")
    glasses.show("1. e4")
    heard = glasses.listen()

    assert terminal.outputs == ["[Jarvis] Play e4.", "1. e4"]
    assert heard == "advice"


def test_GLS03_take_photo_reads_the_given_file(tmp_path):
    photo = tmp_path / "my board.jpg"
    photo.write_bytes(b"\xff\xd8 bytes")
    # Glisser un fichier dans le terminal macOS ajoute parfois des guillemets.
    glasses, terminal = console_glasses(f"'{photo}' ")

    assert glasses.take_photo() == b"\xff\xd8 bytes"
    assert terminal.questions == ["Photo path: "]


@pytest.mark.parametrize("path", ["/does/not/exist.jpg", "{folder}"])
def test_GLS03_photo_not_found(tmp_path, path):
    glasses, _ = console_glasses(path.format(folder=tmp_path))

    with pytest.raises(InvalidPhoto, match="Photo not found"):
        glasses.take_photo()
