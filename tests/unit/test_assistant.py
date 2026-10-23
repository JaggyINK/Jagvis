import pytest

from jagvis_chess.assistant import TEXT_MODEL, LLMAssistant
from jagvis_chess.errors import ConfigError, ServiceDown
from jagvis_chess.groq_client import make_groq_client
from jagvis_chess.model import Color, Move, Position
from jagvis_chess.results import Evaluation
from tests.fakes import FakeGroqClient

START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
EVALUATION = Evaluation(best_move=Move("e4", Color.WHITE), score=35)


def test_LLM01_one_request_with_the_position_and_the_move():
    client = FakeGroqClient(["The e4 pawn takes the center."])

    LLMAssistant(client=client).explain(Position(START), EVALUATION)

    assert len(client.calls) == 1
    call = client.calls[0]
    assert call["model"] == TEXT_MODEL
    assert call["temperature"] == 0
    assert [message["role"] for message in call["messages"]] == ["system", "user"]
    question = call["messages"][1]["content"]
    assert START in question
    assert "e4" in question
    assert "35" in question
    assert "white" in question


def test_LLM01_the_mate_is_in_the_question():
    client = FakeGroqClient(["Mate!"])
    evaluation = Evaluation(best_move=Move("Ra8#", Color.WHITE), score=9999, mate_in=1)

    LLMAssistant(model="other-model", client=client).explain(Position(START), evaluation)

    assert client.calls[0]["model"] == "other-model"
    assert "Mate in 1" in client.calls[0]["messages"][1]["content"]


def test_LLM02_gives_the_model_text_without_spaces_around():
    client = FakeGroqClient(["  Play e4.\n"])

    assert LLMAssistant(client=client).explain(Position(START), EVALUATION) == "Play e4."


def test_LLM03_groq_is_down():
    client = FakeGroqClient([ConnectionError("timeout")])

    with pytest.raises(ServiceDown, match="The language service is down.") as error:
        LLMAssistant(client=client).explain(Position(START), EVALUATION)
    assert isinstance(error.value.__cause__, ConnectionError)


@pytest.mark.parametrize("answer", [None, "", "   "])
def test_LLM03_empty_answer(answer):
    client = FakeGroqClient([answer])

    with pytest.raises(ServiceDown, match="The language service gave an empty answer."):
        LLMAssistant(client=client).explain(Position(START), EVALUATION)


def test_LLM04_missing_key(monkeypatch):
    monkeypatch.delenv("GROQ_KEY", raising=False)

    with pytest.raises(ConfigError, match="the GROQ_KEY variable is not set."):
        LLMAssistant()


def test_LLM04_the_real_client_gets_the_key(monkeypatch, mocker):
    monkeypatch.setenv("GROQ_KEY", "test-key")
    groq = mocker.patch("jagvis_chess.groq_client.Groq")

    client = make_groq_client()

    groq.assert_called_once_with(api_key="test-key")
    assert client is groq.return_value


@pytest.mark.groq
def test_LLM05_the_real_groq_explains_a_move():
    text = LLMAssistant().explain(Position(START), EVALUATION)

    # On ne vérifie jamais les mots d'un LLM : seulement qu'il a répondu.
    assert isinstance(text, str) and text.strip()
