import pytest

from jagvis_chess.console import HELP, main, run, run_command
from jagvis_chess.errors import NoGame
from jagvis_chess.model import Color, GameMode


class FakeJarvis:
    """Replaces Jarvis: writes down which method was called, with which arguments."""

    def __init__(self, failure=None):
        self.calls = []
        self.failure = failure

    def _record(self, name, *arguments):
        self.calls.append((name, arguments))
        if self.failure:
            raise self.failure

    def start_game(self, mode, color):
        self._record("start_game", mode, color)

    def suggest_move(self):
        self._record("suggest_move")

    def follow_game(self):
        self._record("follow_game")

    def explain_move(self):
        self._record("explain_move")

    def play_against_me(self):
        self._record("play_against_me")

    def analyze_game(self):
        self._record("analyze_game")

    def import_game(self, lichess_id):
        self._record("import_game", lichess_id)

    def export_pgn(self):
        self._record("export_pgn")


class FakeGlasses:
    def __init__(self, sentences):
        self.sentences = list(sentences)
        self.spoken = []

    def listen(self):
        if not self.sentences:
            raise EOFError  # Ctrl-D in the terminal
        return self.sentences.pop(0)

    def speak(self, text):
        self.spoken.append(text)


@pytest.mark.parametrize(
    "command, call",
    [
        ("new friendly black", ("start_game", (GameMode.FRIENDLY, Color.BLACK))),
        ("NEW official white", ("start_game", (GameMode.OFFICIAL, Color.WHITE))),
        ("advice", ("suggest_move", ())),
        ("follow", ("follow_game", ())),
        ("explain", ("explain_move", ())),
        ("play", ("play_against_me", ())),
        ("analyze", ("analyze_game", ())),
        ("import AbCd1234", ("import_game", ("AbCd1234",))),
        ("pgn", ("export_pgn", ())),
    ],
)
def test_CON01_each_command_calls_jarvis(command, call):
    jarvis = FakeJarvis()

    run_command(jarvis, command)

    assert jarvis.calls == [call]


@pytest.mark.parametrize("command", ["", "dance", "new", "new fast white", "new friendly green", "import"])
def test_CON02_unknown_or_incomplete_command_gives_the_help(command):
    jarvis = FakeJarvis()

    assert run_command(jarvis, command) == HELP
    assert jarvis.calls == []


def test_CON03_an_expected_error_is_said_and_the_loop_goes_on():
    jarvis = FakeJarvis(failure=NoGame("No current game: start or import a game."))
    glasses = FakeGlasses(["advice", "dance", "quit"])

    run(jarvis, glasses)

    assert glasses.spoken == [
        HELP,
        "Error: No current game: start or import a game.",
        HELP,
        "Goodbye!",
    ]


def test_CON03_ctrl_d_quits_cleanly():
    glasses = FakeGlasses([])

    run(FakeJarvis(), glasses)

    assert glasses.spoken[-1] == "Goodbye!"


def test_CON04_without_groq_key_code_2_and_a_clear_message(monkeypatch, mocker, capsys):
    mocker.patch("jagvis_chess.console.load_dotenv")  # do not read the real .env file
    monkeypatch.delenv("GROQ_KEY", raising=False)

    code = main()

    assert code == 2
    output = capsys.readouterr()
    assert output.err == "Error: the GROQ_KEY variable is not set.\n"
    assert "Traceback" not in output.out + output.err


def test_CON04_with_a_key_jarvis_starts_then_quits(monkeypatch, mocker, tmp_path):
    mocker.patch("jagvis_chess.console.load_dotenv")
    monkeypatch.setenv("GROQ_KEY", "test-key")  # building the Groq client does not use the network
    monkeypatch.setenv("JAGVIS_GAMES", str(tmp_path / "games"))
    fake_run = mocker.patch("jagvis_chess.console.run")

    assert main() == 0
    jarvis, glasses = fake_run.call_args.args
    assert glasses is jarvis.glasses
    assert (tmp_path / "games").is_dir()
