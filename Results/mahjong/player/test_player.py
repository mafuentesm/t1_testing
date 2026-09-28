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
import mahjong.player as target

class DummyCard:
    def __init__(self, name):
        self.name = name

    def get_str(self):
        return self.name

class DummyDealer:
    def __init__(self, table=None):
        self.table = table if table is not None else []

def test_init_and_get_player_id():
    np_random = "random_obj"
    player = target.MahjongPlayer(player_id=1, np_random=np_random)
    assert player.get_player_id() == 1
    assert player.np_random == "random_obj"
    assert player.hand == []
    assert player.pile == []

def test_print_hand(capsys):
    np_random = None
    player = target.MahjongPlayer(player_id=2, np_random=np_random)
    card = DummyCard("Card1")
    player.hand.append(card)
    player.print_hand()
    captured = capsys.readouterr()
    assert "['Card1']" in captured.out

def test_print_pile(capsys):
    np_random = None
    player = target.MahjongPlayer(player_id=3, np_random=np_random)
    card1 = DummyCard("CardA")
    card2 = DummyCard("CardB")
    player.pile.append([card1, card2])
    player.print_pile()
    captured = capsys.readouterr()
    assert "[['CardA', 'CardB']]" in captured.out

def test_play_card():
    np_random = None
    player = target.MahjongPlayer(player_id=4, np_random=np_random)
    dealer = DummyDealer(table=[])
    card1 = DummyCard("C1")
    card2 = DummyCard("C2")
    player.hand = [card1, card2]
    
    player.play_card(dealer, card2)
    
    assert player.hand == [card1]
    assert dealer.table == [card2]

def test_chow():
    np_random = None
    player = target.MahjongPlayer(player_id=5, np_random=np_random)
    last_card = DummyCard("Last")
    dealer = DummyDealer(table=[last_card])
    
    card1 = DummyCard("C1")
    card2 = DummyCard("C2")
    player.hand = [card1, card2, last_card]
    
    cards_to_chow = [card1, card2, last_card]
    player.chow(dealer, cards_to_chow)
    
    assert dealer.table == []
    assert card1 not in player.hand
    assert card2 not in player.hand
    assert player.pile == [cards_to_chow]

def test_gong():
    np_random = None
    player = target.MahjongPlayer(player_id=6, np_random=np_random)
    dealer = DummyDealer(table=[])
    
    card1 = DummyCard("G1")
    card2 = DummyCard("G2")
    player.hand = [card1, card2]
    
    cards_to_gong = [card1, card2]
    player.gong(dealer, cards_to_gong)
    
    assert player.hand == []
    assert player.pile == [cards_to_gong]

def test_pong():
    np_random = None
    player = target.MahjongPlayer(player_id=7, np_random=np_random)
    dealer = DummyDealer(table=[])
    
    card1 = DummyCard("P1")
    card2 = DummyCard("P2")
    card3 = DummyCard("P3")
    player.hand = [card1, card2, card3]
    
    cards_to_pong = [card1, card2, card3]
    player.pong(dealer, cards_to_pong)
    
    assert player.hand == []
    assert player.pile == [cards_to_pong]
