import io
import urllib.error
from datetime import datetime

import pytest

from jagvis_echecs.erreurs import IdentifiantInvalide, PartieIntrouvable, PgnInvalide, ServiceIndisponible
from jagvis_echecs.import_lichess import ImportLichess, telecharger_http
from jagvis_echecs.modele import Coup, Couleur, ModeJeu

PGN_CLASSE = """[Event "Rated Blitz game"]
[Site "https://lichess.org/AbCd1234"]
[UTCDate "2026.10.20"]
[UTCTime "18:30:05"]
[White "alice"]
[Black "bob"]
[Result "0-1"]
[Variant "Standard"]

1. f3 e5 2. g4 Qh4# 0-1
"""


class FauxTelechargement:
    """Remplace l'appel HTTP : renvoie un texte préparé et note les requêtes."""

    def __init__(self, texte=PGN_CLASSE):
        self.texte = texte
        self.requetes = []

    def __call__(self, url, entetes):
        self.requetes.append((url, entetes))
        return self.texte


def test_LIC01_url_et_entetes_de_l_api_publique():
    telecharger = FauxTelechargement()

    ImportLichess(telecharger=telecharger).recuperer_partie("AbCd1234")

    url, entetes = telecharger.requetes[0]
    assert url == "https://lichess.org/game/export/AbCd1234"
    assert entetes["Accept"] == "application/x-chess-pgn"
    assert "Authorization" not in entetes


def test_LIC01_le_token_est_envoye_s_il_existe():
    telecharger = FauxTelechargement()

    ImportLichess(token="secret", telecharger=telecharger).recuperer_partie("AbCd1234")

    assert telecharger.requetes[0][1]["Authorization"] == "Bearer secret"


def test_LIC01_un_identifiant_de_12_caracteres_garde_les_8_premiers():
    telecharger = FauxTelechargement()

    partie = ImportLichess(telecharger=telecharger).recuperer_partie("AbCd1234wxyz")

    assert telecharger.requetes[0][0].endswith("/AbCd1234")
    assert partie.id == "AbCd1234"


def test_LIC02_le_pgn_devient_une_partie():
    partie = ImportLichess(telecharger=FauxTelechargement()).recuperer_partie("AbCd1234")

    assert partie.id == "AbCd1234"
    assert partie.date == datetime(2026, 10, 20, 18, 30, 5)
    assert partie.couleur_joueur == Couleur.BLANC
    assert [coup.notation for coup in partie.coups] == ["f3", "e5", "g4", "Qh4#"]
    assert partie.coups[1] == Coup("e5", Couleur.NOIR)


@pytest.mark.parametrize(
    "evenement, mode",
    [("Rated Blitz game", ModeJeu.OFFICIEL), ("Casual Rapid game", ModeJeu.AMICAL)],
)
def test_LIC03_mode_selon_partie_classee_ou_non(evenement, mode):
    pgn = PGN_CLASSE.replace("Rated Blitz game", evenement)

    partie = ImportLichess(telecharger=FauxTelechargement(pgn)).recuperer_partie("AbCd1234")

    assert partie.mode == mode


@pytest.mark.parametrize("id", ["", "abc", "../../etc", "AbCd123!", "AbCd12345"])
def test_LIC04_identifiant_invalide_sans_appel_reseau(id):
    telecharger = FauxTelechargement()

    with pytest.raises(IdentifiantInvalide, match="Identifiant Lichess invalide"):
        ImportLichess(telecharger=telecharger).recuperer_partie(id)
    assert telecharger.requetes == []


def test_LIC04_date_illisible_remplacee_par_maintenant():
    pgn = PGN_CLASSE.replace("2026.10.20", "????.??.??")

    partie = ImportLichess(telecharger=FauxTelechargement(pgn)).recuperer_partie("AbCd1234")

    assert isinstance(partie.date, datetime)


@pytest.mark.parametrize(
    "pgn, message",
    [
        ("", "La partie Lichess n'a pas pu être lue."),
        ("[Event \"Casual\"]\n\n*\n", "La partie Lichess ne contient aucun coup."),
        ("[Event \"Casual\"]\n\n1. e4 e4 *\n", "La partie Lichess n'a pas pu être lue."),
        (PGN_CLASSE.replace("Standard", "Chess960"), "Variante non prise en charge : Chess960"),
    ],
)
def test_LIC05_pgn_inutilisable(pgn, message):
    with pytest.raises(PgnInvalide, match=message):
        ImportLichess(telecharger=FauxTelechargement(pgn)).recuperer_partie("AbCd1234")


class FausseReponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *erreur):
        return False


def erreur_http(code):
    return urllib.error.HTTPError("https://lichess.org", code, "erreur", {}, None)


def test_LIC06_telechargement_reussi(mocker):
    urlopen = mocker.patch("urllib.request.urlopen", return_value=FausseReponse(PGN_CLASSE.encode()))

    texte = telecharger_http("https://lichess.org/game/export/AbCd1234", {"Accept": "application/x-chess-pgn"})

    assert texte == PGN_CLASSE
    requete = urlopen.call_args.args[0]
    assert requete.full_url == "https://lichess.org/game/export/AbCd1234"
    assert urlopen.call_args.kwargs["timeout"] == 10


@pytest.mark.parametrize(
    "panne, erreur_attendue, message",
    [
        (erreur_http(404), PartieIntrouvable, "Partie Lichess introuvable"),
        (erreur_http(429), ServiceIndisponible, "Lichess limite les requêtes"),
        (erreur_http(500), ServiceIndisponible, "Lichess a répondu une erreur 500"),
        (urllib.error.URLError("pas de réseau"), ServiceIndisponible, "Lichess est injoignable"),
        (TimeoutError(), ServiceIndisponible, "Lichess est injoignable"),
    ],
)
def test_LIC06_pannes_reseau(mocker, panne, erreur_attendue, message):
    mocker.patch("urllib.request.urlopen", side_effect=panne)

    with pytest.raises(erreur_attendue, match=message):
        telecharger_http("https://lichess.org/game/export/AbCd1234", {})
