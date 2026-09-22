import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/gin_rummy']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from unittest.mock import MagicMock
from gin_rummy.dealer import GinRummyDealer

class MockPlayer:
    def __init__(self):
        self.hand = []
        self.did_populate_hand_called = False

    def did_populate_hand(self):
        self.did_populate_hand_called = True

@pytest.fixture
def mock_random():
    return MagicMock()

def test_dealer_initialization(mock_random):
    dealer = GinRummyDealer(mock_random)
    assert len(dealer.stock_pile) == 52
    assert len(dealer.discard_pile) == 0
    mock_random.shuffle.assert_called_once()

def test_deal_cards(mock_random):
    dealer = GinRummyDealer(mock_random)
    player = MockPlayer()
    num_cards = 7
    
    dealer.deal_cards(player, num_cards)
    
    assert len(player.hand) == num_cards
    assert len(dealer.stock_pile) == 52 - num_cards
    assert player.did_populate_hand_called is True

def test_deal_cards_removes_from_stock(mock_random):
    dealer = GinRummyDealer(mock_random)
    initial_stock_size = len(dealer.stock_pile)
    player = MockPlayer()
    
    dealer.deal_cards(player, 10)
    
    assert len(dealer.stock_pile) == initial_stock_size - 10

def test_deal_multiple_times(mock_random):
    dealer = GinRummyDealer(mock_random)
    player1 = MockPlayer()
    player2 = MockPlayer()
    
    dealer.deal_cards(player1, 5)
    dealer.deal_cards(player2, 5)
    
    assert len(player1.hand) == 5
    assert len(player2.hand) == 5
    assert len(dealer.stock_pile) == 52 - 10