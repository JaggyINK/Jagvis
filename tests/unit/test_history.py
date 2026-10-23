from datetime import datetime

import pytest

from jagvis_chess.errors import BrokenSaveFile, GameNotFound, InvalidId
from jagvis_chess.history import History
from jagvis_chess.model import Color, Game, GameMode, Move


def new_game(id="abc123", date=datetime(2026, 10, 23, 14, 5), moves=("e4", "e5")):
    game = Game(GameMode.OFFICIAL, Color.BLACK, id=id, date=date)
    for notation in moves:
        game.play(Move(notation, game.current_position().turn))
    return game


def test_HIS01_a_saved_game_comes_back_the_same(tmp_path):
    game = new_game()
    History(str(tmp_path)).save(game)

    loaded = History(str(tmp_path)).load("abc123")

    assert loaded.id == game.id
    assert loaded.date == game.date
    assert loaded.mode == GameMode.OFFICIAL
    assert loaded.player_color == Color.BLACK
    assert loaded.moves == game.moves


def test_HIS01_saving_twice_replaces_the_old_version(tmp_path):
    history = History(str(tmp_path))
    game = new_game(moves=["e4"])
    history.save(game)
    game.play(Move("e5", Color.BLACK))

    history.save(game)

    assert len(history.load("abc123").moves) == 2
    assert len(history.list_games()) == 1


def test_HIS02_list_an_empty_history(tmp_path):
    assert History(str(tmp_path)).list_games() == []


def test_HIS02_list_from_oldest_to_newest(tmp_path):
    history = History(str(tmp_path))
    history.save(new_game(id="recent", date=datetime(2026, 10, 23)))
    history.save(new_game(id="old", date=datetime(2025, 1, 1)))

    assert [game.id for game in history.list_games()] == ["old", "recent"]


def test_HIS03_load_an_unknown_game(tmp_path):
    with pytest.raises(GameNotFound, match="Game not found: zzz"):
        History(str(tmp_path)).load("zzz")


def test_HIS04_the_folder_is_created_if_missing(tmp_path):
    folder = tmp_path / "sub" / "folder"

    History(str(folder)).save(new_game())

    assert (folder / "abc123.json").exists()


@pytest.mark.parametrize("id", ["../secret", "a/b", "", "x" * 65, "é"])
def test_HIS05_a_dangerous_id_is_refused(tmp_path, id):
    history = History(str(tmp_path))

    with pytest.raises(InvalidId, match="Invalid game id"):
        history.load(id)
    with pytest.raises(InvalidId):
        history.save(new_game(id=id or "?"))


def test_HIS06_a_broken_file_gives_a_clear_error(tmp_path):
    (tmp_path / "abc123.json").write_text("{ not json", encoding="utf-8")

    with pytest.raises(BrokenSaveFile, match="The file of game abc123 cannot be read."):
        History(str(tmp_path)).load("abc123")


def test_HIS06_a_file_with_an_illegal_move_is_broken(tmp_path):
    history = History(str(tmp_path))
    history.save(new_game())
    file = tmp_path / "abc123.json"
    file.write_text(file.read_text(encoding="utf-8").replace('"e4"', '"e7"'), encoding="utf-8")

    with pytest.raises(BrokenSaveFile):
        history.load("abc123")


def test_HIS06_list_skips_broken_files(tmp_path):
    history = History(str(tmp_path))
    history.save(new_game(id="good"))
    (tmp_path / "bad.json").write_text("[]", encoding="utf-8")

    assert [game.id for game in history.list_games()] == ["good"]
