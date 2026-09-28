# >>> PREAMBULO AGENTE (autogenerado, no editar) >>>
import sys
import os
import ast
import types
import importlib

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_TEST_DIR, '../../..'))
_PUBLIC_ROOT = os.path.join(_PROJECT_ROOT, "Public_Proyects")
_SOURCE_DIR = os.path.normpath(os.path.join(_TEST_DIR, '../../../Public_Proyects/blackjack'))

# 1. Configuración de sys.path
for _p in [_PUBLIC_ROOT, _PROJECT_ROOT, _SOURCE_DIR]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

_curr_pkg_name = 'blackjack'
_curr_pkg_dir = os.path.join(_PUBLIC_ROOT, _curr_pkg_name) if _curr_pkg_name else ""

if _curr_pkg_name and os.path.isdir(_curr_pkg_dir):
    class _DynamicPackage(types.ModuleType):
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            # A. Intento como submódulo hermano (ej: blackjack.dealer)
            sub_py = os.path.join(_curr_pkg_dir, f"{name}.py")
            if os.path.exists(sub_py):
                try:
                    mod = importlib.import_module(f"{self.__name__}.{name}")
                    setattr(self, name, mod)
                    return mod
                except Exception:
                    pass

            for f in sorted(os.listdir(_curr_pkg_dir)):
                if f.endswith(".py") and not f.startswith("__"):
                    mod_name = f[:-3]
                    f_full = os.path.join(_curr_pkg_dir, f)
                    try:
                        with open(f_full, "r", encoding="utf-8") as _src:
                            tree = ast.parse(_src.read(), filename=f_full)
                        for node in tree.body:
                            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                                if node.name == name or node.name.lower().endswith(name.lower()):
                                    mod = importlib.import_module(f"{self.__name__}.{mod_name}")
                                    val = getattr(mod, node.name)
                                    setattr(self, name, val)
                                    return val
                    except Exception:
                        pass

            raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")

    pkg_mod = _DynamicPackage(_curr_pkg_name)
    pkg_mod.__path__ = [_curr_pkg_dir]
    pkg_mod.__file__ = os.path.join(_curr_pkg_dir, "__init__.py")
    sys.modules[_curr_pkg_name] = pkg_mod
# <<< PREAMBULO AGENTE <<<

import pytest
import blackjack.judger as target

class DummyCard:
    def __init__(self, rank):
        self.rank = rank

class DummyPlayer:
    def __init__(self, hand):
        self.hand = hand

class DummyGamePlayer:
    def __init__(self, status, score):
        self.status = status
        self.score = score

class DummyGameDealer:
    def __init__(self, status, score):
        self.status = status
        self.score = score

class DummyGame:
    def __init__(self, player_status, player_score, dealer_status, dealer_score):
        self.players = {0: DummyGamePlayer(player_status, player_score)}
        self.dealer = DummyGameDealer(dealer_status, dealer_score)
        self.winner = {}

def test_judge_score_basic():
    judger = target.BlackjackJudger(None)
    cards = [DummyCard("2"), DummyCard("5")]
    assert judger.judge_score(cards) == 7

def test_judge_score_face_cards():
    judger = target.BlackjackJudger(None)
    cards = [DummyCard("K"), DummyCard("T")]
    assert judger.judge_score(cards) == 20

def test_judge_score_ace_adjustment():
    judger = target.BlackjackJudger(None)
    cards = [DummyCard("A"), DummyCard("9")]
    assert judger.judge_score(cards) == 20

def test_judge_score_ace_adjustment_multiple():
    judger = target.BlackjackJudger(None)
    cards = [DummyCard("A"), DummyCard("A"), DummyCard("9")]
    assert judger.judge_score(cards) == 21

def test_judge_round_alive():
    judger = target.BlackjackJudger(None)
    player = DummyPlayer([DummyCard("5"), DummyCard("5")])
    status, score = judger.judge_round(player)
    assert status == "alive"
    assert score == 10

def test_judge_round_bust():
    judger = target.BlackjackJudger(None)
    player = DummyPlayer([DummyCard("K"), DummyCard("K"), DummyCard("5")])
    status, score = judger.judge_round(player)
    assert status == "bust"
    assert score == 25

def test_judge_game_player_bust():
    judger = target.BlackjackJudger(None)
    game = DummyGame(player_status='bust', player_score=25, dealer_status='alive', dealer_score=18)
    judger.judge_game(game, 0)
    assert game.winner['player0'] == -1

def test_judge_game_dealer_bust():
    judger = target.BlackjackJudger(None)
    game = DummyGame(player_status='alive', player_score=20, dealer_status='bust', dealer_score=22)
    judger.judge_game(game, 0)
    assert game.winner['player0'] == 2

def test_judge_game_player_higher_score():
    judger = target.BlackjackJudger(None)
    game = DummyGame(player_status='alive', player_score=20, dealer_status='alive', dealer_score=18)
    judger.judge_game(game, 0)
    assert game.winner['player0'] == 2

def test_judge_game_dealer_higher_score():
    judger = target.BlackjackJudger(None)
    game = DummyGame(player_status='alive', player_score=17, dealer_status='alive', dealer_score=19)
    judger.judge_game(game, 0)
    assert game.winner['player0'] == -1

def test_judge_game_tie():
    judger = target.BlackjackJudger(None)
    game = DummyGame(player_status='alive', player_score=19, dealer_status='alive', dealer_score=19)
    judger.judge_game(game, 0)
    assert game.winner['player0'] == 1
