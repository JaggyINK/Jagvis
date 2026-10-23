import pytest

from jagvis_echecs.assistant_llm import MODELE_TEXTE, AssistantLLM
from jagvis_echecs.client_groq import creer_client_groq
from jagvis_echecs.erreurs import ConfigurationInvalide, ServiceIndisponible
from jagvis_echecs.modele import Coup, Couleur, Position
from jagvis_echecs.resultats import Evaluation
from tests.doubles import FauxClientGroq

DEPART = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
EVALUATION = Evaluation(meilleur_coup=Coup("e4", Couleur.BLANC), score=35)


def test_LLM01_une_seule_requete_avec_la_position_et_le_coup():
    client = FauxClientGroq(["Le pion e4 prend le centre."])

    AssistantLLM(client=client).expliquer(Position(DEPART), EVALUATION)

    assert len(client.appels) == 1
    appel = client.appels[0]
    assert appel["model"] == MODELE_TEXTE
    assert appel["temperature"] == 0
    assert [message["role"] for message in appel["messages"]] == ["system", "user"]
    question = appel["messages"][1]["content"]
    assert DEPART in question
    assert "e4" in question
    assert "35" in question
    assert "blanc" in question


def test_LLM01_le_mat_est_mentionne_dans_la_question():
    client = FauxClientGroq(["Mat !"])
    evaluation = Evaluation(meilleur_coup=Coup("Ra8#", Couleur.BLANC), score=9999, mat_en=1)

    AssistantLLM(modele="autre-modele", client=client).expliquer(Position(DEPART), evaluation)

    assert client.appels[0]["model"] == "autre-modele"
    assert "Mat en 1" in client.appels[0]["messages"][1]["content"]


def test_LLM02_renvoie_le_texte_du_modele_sans_espaces_autour():
    client = FauxClientGroq(["  Joue e4.\n"])

    assert AssistantLLM(client=client).expliquer(Position(DEPART), EVALUATION) == "Joue e4."


def test_LLM03_groq_en_panne():
    client = FauxClientGroq([ConnectionError("timeout")])

    with pytest.raises(ServiceIndisponible, match="Le service de langage est indisponible.") as erreur:
        AssistantLLM(client=client).expliquer(Position(DEPART), EVALUATION)
    assert isinstance(erreur.value.__cause__, ConnectionError)


@pytest.mark.parametrize("reponse", [None, "", "   "])
def test_LLM03_reponse_vide(reponse):
    client = FauxClientGroq([reponse])

    with pytest.raises(ServiceIndisponible, match="Le service de langage n'a rien répondu."):
        AssistantLLM(client=client).expliquer(Position(DEPART), EVALUATION)


def test_LLM04_cle_absente(monkeypatch):
    monkeypatch.delenv("GROQ_KEY", raising=False)

    with pytest.raises(ConfigurationInvalide, match="la variable GROQ_KEY n'est pas définie."):
        AssistantLLM()


def test_LLM04_le_vrai_client_est_construit_avec_la_cle(monkeypatch, mocker):
    monkeypatch.setenv("GROQ_KEY", "cle-de-test")
    groq = mocker.patch("jagvis_echecs.client_groq.Groq")

    client = creer_client_groq()

    groq.assert_called_once_with(api_key="cle-de-test")
    assert client is groq.return_value


@pytest.mark.groq
def test_LLM05_le_vrai_groq_explique_un_coup():
    texte = AssistantLLM().expliquer(Position(DEPART), EVALUATION)

    # On ne vérifie jamais la formulation d'un LLM : seulement qu'il a répondu.
    assert isinstance(texte, str) and texte.strip()
