# >>> PREAMBULO AGENTE (autogenerado, no editar) >>>
import sys
import os
import ast
import types
import importlib

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_TEST_DIR, '../../..'))
_PUBLIC_ROOT = os.path.join(_PROJECT_ROOT, "Public_Proyects")
_SOURCE_DIR = os.path.normpath(os.path.join(_TEST_DIR, '../../../Public_Proyects/gin_rummy'))

# 1. Configuración de sys.path
for _p in [_PUBLIC_ROOT, _PROJECT_ROOT, _SOURCE_DIR]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

_curr_pkg_name = 'gin_rummy'
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
from unittest.mock import patch
import gin_rummy.action_event as target

def test_action_event_equality():
    event1 = target.ActionEvent(action_id=target.score_player_0_action_id)
    event2 = target.ActionEvent(action_id=target.score_player_0_action_id)
    event3 = target.ActionEvent(action_id=target.score_player_1_action_id)
    assert event1 == event2
    assert event1 != event3
    assert event1 != 'not_an_action_event'

def test_action_event_get_num_actions():
    expected = target.knock_action_id + 52
    assert target.ActionEvent.get_num_actions() == expected

def test_decode_action_score_player_0():
    action = target.ActionEvent.decode_action(target.score_player_0_action_id)
    assert isinstance(action, target.ScoreNorthPlayerAction)
    assert action.action_id == target.score_player_0_action_id
    assert str(action) == 'score N'

def test_decode_action_score_player_1():
    action = target.ActionEvent.decode_action(target.score_player_1_action_id)
    assert isinstance(action, target.ScoreSouthPlayerAction)
    assert action.action_id == target.score_player_1_action_id
    assert str(action) == 'score S'

def test_decode_action_draw_card():
    action = target.ActionEvent.decode_action(target.draw_card_action_id)
    assert isinstance(action, target.DrawCardAction)
    assert action.action_id == target.draw_card_action_id
    assert str(action) == 'draw_card'

def test_decode_action_pick_up_discard():
    action = target.ActionEvent.decode_action(target.pick_up_discard_action_id)
    assert isinstance(action, target.PickUpDiscardAction)
    assert action.action_id == target.pick_up_discard_action_id
    assert str(action) == 'pick_up_discard'

def test_decode_action_declare_dead_hand():
    action = target.ActionEvent.decode_action(target.declare_dead_hand_action_id)
    assert isinstance(action, target.DeclareDeadHandAction)
    assert action.action_id == target.declare_dead_hand_action_id
    assert str(action) == 'declare_dead_hand'

def test_decode_action_gin():
    action = target.ActionEvent.decode_action(target.gin_action_id)
    assert isinstance(action, target.GinAction)
    assert action.action_id == target.gin_action_id
    assert str(action) == 'gin'

def test_decode_action_unknown():
    invalid_action_id = target.knock_action_id + 100
    with pytest.raises(Exception) as excinfo:
        target.ActionEvent.decode_action(invalid_action_id)
    assert f'decode_action: unknown action_id={invalid_action_id}' in str(excinfo.value)

@patch('utils.get_card_id')
def test_discard_action_init_and_str(mock_get_card_id):
    mock_card_id = 3
    mock_get_card_id.return_value = mock_card_id
    mock_card = 'DummyCard'
    action = target.DiscardAction(card=mock_card)
    mock_get_card_id.assert_called_once_with(mock_card)
    assert action.card == mock_card
    assert action.action_id == target.discard_action_id + mock_card_id
    assert str(action) == 'discard DummyCard'

@patch('utils.get_card_id')
def test_knock_action_init_and_str(mock_get_card_id):
    mock_card_id = 7
    mock_get_card_id.return_value = mock_card_id
    mock_card = 'DummyCard'
    action = target.KnockAction(card=mock_card)
    mock_get_card_id.assert_called_once_with(mock_card)
    assert action.card == mock_card
    assert action.action_id == target.knock_action_id + mock_card_id
    assert str(action) == 'knock DummyCard'
