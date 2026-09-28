# >>> PREAMBULO AGENTE (autogenerado, no editar) >>>
import sys
import os
import ast
import types
import importlib

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_TEST_DIR, '../../..'))
_PUBLIC_ROOT = os.path.join(_PROJECT_ROOT, "Public_Proyects")
_SOURCE_DIR = os.path.normpath(os.path.join(_TEST_DIR, '../../../Public_Proyects/mahjong'))

# 1. Configuración de sys.path
for _p in [_PUBLIC_ROOT, _PROJECT_ROOT, _SOURCE_DIR]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

_curr_pkg_name = 'mahjong'
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
from unittest.mock import MagicMock
import numpy as np
import mahjong.game as target

def test_mahjong_game_init():
    game = target.MahjongGame(allow_step_back=True)
    assert game.allow_step_back is True
    assert isinstance(game.np_random, np.random.RandomState)
    assert game.num_players == 4

def test_mahjong_game_init_default():
    game = target.MahjongGame()
    assert game.allow_step_back is False

def test_init_game(monkeypatch):
    mock_dealer_instance = MagicMock()
    mock_player_instance = MagicMock()
    mock_judger_instance = MagicMock()
    mock_round_instance = MagicMock()
    mock_round_instance.current_player = 0
    mock_round_instance.get_state.return_value = {'valid_act': ['play'], 'action_cards': ['card1']}
    monkeypatch.setattr(target, 'Dealer', lambda rng: mock_dealer_instance)
    monkeypatch.setattr(target, 'Player', lambda i, rng: mock_player_instance)
    monkeypatch.setattr(target, 'Judger', lambda rng: mock_judger_instance)
    monkeypatch.setattr(target, 'Round', lambda judger, dealer, num_players, rng: mock_round_instance)
    game = target.MahjongGame()
    state, player_id = game.init_game()
    assert player_id == 0
    assert mock_dealer_instance.deal_cards.call_count == 5
    assert game.history == []
    assert game.cur_state == state

def test_get_state():
    game = target.MahjongGame()
    game.round = MagicMock()
    game.players = [MagicMock()]
    game.round.get_state.return_value = {'status': 'active'}
    state = game.get_state(0)
    game.round.get_state.assert_called_once_with(game.players, 0)
    assert state == {'status': 'active'}

def test_get_legal_actions_play():
    state = {'valid_act': ['play'], 'action_cards': ['act1', 'act2']}
    actions = target.MahjongGame.get_legal_actions(state)
    assert actions == ['act1', 'act2']
    assert state['valid_act'] == ['act1', 'act2']

def test_get_legal_actions_other():
    state = {'valid_act': ['call', 'raise']}
    actions = target.MahjongGame.get_legal_actions(state)
    assert actions == ['call', 'raise']

def test_get_num_actions():
    assert target.MahjongGame.get_num_actions() == 38

def test_get_num_players():
    game = target.MahjongGame()
    assert game.get_num_players() == 4

def test_get_player_id():
    game = target.MahjongGame()
    game.round = MagicMock()
    game.round.current_player = 3
    assert game.get_player_id() == 3

def test_is_over():
    game = target.MahjongGame()
    game.judger = MagicMock()
    game.judger.judge_game.return_value = (True, 2, None)
    over = game.is_over()
    assert over is True
    assert game.winner == 2
    game.judger.judge_game.assert_called_once_with(game)

def test_step_without_step_back():
    game = target.MahjongGame(allow_step_back=False)
    game.history = []
    game.round = MagicMock()
    game.round.current_player = 1
    game.round.get_state.return_value = {'valid_act': ['check']}
    game.players = []

    state, player_id = game.step('check')

    game.round.proceed_round.assert_called_once_with([], 'check')
    assert player_id == 1
    assert state == {'valid_act': ['check']}
    assert game.history == []

def test_step_with_step_back():
    game = target.MahjongGame(allow_step_back=True)
    game.history = []
    game.dealer = MagicMock()
    game.round = MagicMock()
    game.players = []
    game.round.current_player = 2
    game.round.get_state.return_value = {'valid_act': ['fold']}

    state, player_id = game.step('fold')

    assert player_id == 2
    assert state == {'valid_act': ['fold']}
    assert len(game.history) == 1

def test_step_back_empty_history():
    game = target.MahjongGame(allow_step_back=True)
    game.history = []
    assert game.step_back() is False

def test_step_back_success():
    game = target.MahjongGame(allow_step_back=True)
    old_dealer = MagicMock()
    old_players = [MagicMock()]
    old_round = MagicMock()
    game.history = [(old_dealer, old_players, old_round)]

    success = game.step_back()
    assert success is True
    assert game.dealer == old_dealer
    assert game.players == old_players
    assert game.round == old_round
    assert game.history == []
