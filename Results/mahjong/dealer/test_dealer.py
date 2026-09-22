import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/mahjong']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from unittest.mock import MagicMock
from mahjong.dealer import MahjongDealer

class MockPlayer:
    def __init__(self):
        self.hand = []

@pytest.fixture
def mock_random():
    return MagicMock()

def test_mahjong_dealer_initialization(mock_random):
    dealer = MahjongDealer(mock_random)
    assert len(dealer.deck) > 0
    assert mock_random.shuffle.called

def test_shuffle_calls_np_random(mock_random):
    dealer = MahjongDealer(mock_random)
    dealer.shuffle()
    assert mock_random.shuffle.called

def test_deal_cards(mock_random):
    dealer = MahjongDealer(mock_random)
    player = MockPlayer()
    initial_deck_size = len(dealer.deck)
    num_cards = 5
    
    dealer.deal_cards(player, num_cards)
    
    assert len(player.hand) == num_cards
    assert len(dealer.deck) == initial_deck_size - num_cards

def test_deal_cards_updates_player_hand(mock_random):
    dealer = MahjongDealer(mock_random)
    player = MockPlayer()
    
    # Pre-verify deck state
    original_last_card = dealer.deck[-1]
    
    dealer.deal_cards(player, 1)
    
    assert player.hand[0] == original_last_card