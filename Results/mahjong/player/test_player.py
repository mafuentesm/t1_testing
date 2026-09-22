import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/mahjong']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from unittest.mock import MagicMock
from mahjong.player import MahjongPlayer

class MockCard:
    def __init__(self, name):
        self.name = name
    def get_str(self):
        return self.name
    def __eq__(self, other):
        return self.name == other.name

@pytest.fixture
def player():
    return MahjongPlayer(player_id=1, np_random=None)

def test_get_player_id(player):
    assert player.get_player_id() == 1

def test_play_card(player):
    dealer = MagicMock()
    dealer.table = []
    card = MockCard("1m")
    player.hand = [card]
    
    player.play_card(dealer, card)
    
    assert len(player.hand) == 0
    assert dealer.table == [card]

def test_chow(player):
    dealer = MagicMock()
    dealer.table = [MockCard("2m")]
    c1 = MockCard("1m")
    c2 = MockCard("3m")
    player.hand = [c1, c2, MockCard("5s")]
    
    cards_to_chow = [c1, c2, MockCard("2m")]
    player.chow(dealer, cards_to_chow)
    
    assert len(player.pile) == 1
    assert len(player.hand) == 1
    assert player.hand[0].name == "5s"
    assert len(dealer.table) == 0

def test_pong(player):
    dealer = MagicMock()
    c1 = MockCard("1m")
    c2 = MockCard("1m")
    c3 = MockCard("1m")
    player.hand = [c1, c2, c3, MockCard("5s")]
    
    cards_to_pong = [c1, c2, c3]
    player.pong(dealer, cards_to_pong)
    
    assert len(player.pile) == 1
    assert len(player.hand) == 1
    assert player.hand[0].name == "5s"

def test_gong(player):
    dealer = MagicMock()
    cards = [MockCard("1m") for _ in range(4)]
    player.hand = cards + [MockCard("5s")]
    
    player.gong(dealer, cards)
    
    assert len(player.pile) == 1
    assert len(player.hand) == 1
    assert player.hand[0].name == "5s"

def test_print_methods(player, capsys):
    card = MockCard("1m")
    player.hand = [card]
    player.pile = [[card]]
    
    player.print_hand()
    captured = capsys.readouterr()
    assert "['1m']" in captured.out
    
    player.print_pile()
    captured = capsys.readouterr()
    assert "[['1m']]" in captured.out