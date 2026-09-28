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

import gin_rummy.dealer as target
from unittest.mock import MagicMock


def test_dealer_initialization():
    mock_np_random = MagicMock()
    dealer = target.GinRummyDealer(mock_np_random)

    mock_np_random.shuffle.assert_called_once_with(dealer.shuffled_deck)
    assert dealer.discard_pile == []
    assert isinstance(dealer.shuffled_deck, list)
    assert len(dealer.shuffled_deck) > 0
    assert dealer.stock_pile == dealer.shuffled_deck
    assert dealer.stock_pile is not dealer.shuffled_deck


def test_deal_cards():
    mock_np_random = MagicMock()
    dealer = target.GinRummyDealer(mock_np_random)

    mock_player = MagicMock()
    mock_player.hand = []

    initial_stock_len = len(dealer.stock_pile)
    num_cards_to_deal = 5

    dealer.deal_cards(mock_player, num_cards_to_deal)

    assert len(mock_player.hand) == num_cards_to_deal
    assert len(dealer.stock_pile) == initial_stock_len - num_cards_to_deal
    mock_player.did_populate_hand.assert_called_once()
