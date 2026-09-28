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
import numpy as np
from blackjack import Card
import blackjack.dealer as target

class DummyPlayer:
    def __init__(self):
        self.hand = []

def test_init_standard_deck():
    deck = target.init_standard_deck()
    assert isinstance(deck, list)
    assert len(deck) == 52
    assert all(isinstance(card, Card) for card in deck)
    
    suits = {'S', 'H', 'D', 'C'}
    ranks = {'A', '2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K'}
    
    first_card = deck[0]
    assert first_card.suit in suits
    assert first_card.rank in ranks

def test_blackjack_dealer_init_default():
    rng = np.random.default_rng(42)
    dealer = target.BlackjackDealer(rng)
    assert dealer.np_random is rng
    assert dealer.num_decks == 1
    assert len(dealer.deck) == 52
    assert dealer.hand == []
    assert dealer.status == 'alive'
    assert dealer.score == 0

def test_blackjack_dealer_init_multiple_decks():
    rng = np.random.default_rng(42)
    dealer = target.BlackjackDealer(rng, num_decks=3)
    assert dealer.num_decks == 3
    assert len(dealer.deck) == 52 * 3

def test_blackjack_dealer_init_infinite_decks():
    rng = np.random.default_rng(42)
    dealer = target.BlackjackDealer(rng, num_decks=0)
    assert dealer.num_decks == 0
    assert len(dealer.deck) == 52

def test_shuffle():
    rng = np.random.default_rng(42)
    dealer = target.BlackjackDealer(rng, num_decks=1)
    deck_before = list(dealer.deck)
    dealer.shuffle()
    deck_after = dealer.deck
    assert len(deck_after) == len(deck_before)
    assert set(deck_after) == set(deck_before)

def test_deal_card_finite_deck():
    rng = np.random.default_rng(42)
    dealer = target.BlackjackDealer(rng, num_decks=1)
    player = DummyPlayer()
    initial_len = len(dealer.deck)
    
    dealer.deal_card(player)
    
    assert len(player.hand) == 1
    assert isinstance(player.hand[0], Card)
    assert len(dealer.deck) == initial_len - 1

def test_deal_card_infinite_deck():
    rng = np.random.default_rng(42)
    dealer = target.BlackjackDealer(rng, num_decks=0)
    player = DummyPlayer()
    initial_len = len(dealer.deck)
    
    dealer.deal_card(player)
    
    assert len(player.hand) == 1
    assert isinstance(player.hand[0], Card)
    assert len(dealer.deck) == initial_len
