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

import mahjong.dealer as target
from unittest.mock import MagicMock


def test_mahjong_dealer_initialization():
    mock_np_random = MagicMock()
    dealer = target.MahjongDealer(mock_np_random)
    
    assert dealer.np_random == mock_np_random
    assert isinstance(dealer.deck, list)
    assert isinstance(dealer.table, list)
    assert dealer.table == []
    mock_np_random.shuffle.assert_called_once_with(dealer.deck)


def test_shuffle():
    mock_np_random = MagicMock()
    dealer = target.MahjongDealer(mock_np_random)
    
    mock_np_random.shuffle.reset_mock()
    dealer.shuffle()
    
    mock_np_random.shuffle.assert_called_once_with(dealer.deck)


def test_deal_cards():
    mock_np_random = MagicMock()
    dealer = target.MahjongDealer(mock_np_random)
    
    initial_deck_len = len(dealer.deck)
    num_cards_to_deal = 3
    
    mock_player = MagicMock()
    mock_player.hand = []
    
    dealer.deal_cards(mock_player, num_cards_to_deal)
    
    assert len(mock_player.hand) == num_cards_to_deal
    assert len(dealer.deck) == initial_deck_len - num_cards_to_deal
