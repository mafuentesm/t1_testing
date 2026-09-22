import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/blackjack']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
import numpy as np
from unittest.mock import MagicMock
from blackjack.dealer import init_standard_deck, BlackjackDealer

def test_init_standard_deck():
    deck = init_standard_deck()
    assert len(deck) == 52
    # Verificamos que contenga objetos Card (asumiendo que Card tiene atributos suit y rank)
    assert hasattr(deck[0], 'suit')
    assert hasattr(deck[0], 'rank')

def test_blackjack_dealer_initialization():
    rng = np.random.default_rng(42)
    dealer = BlackjackDealer(rng, num_decks=1)
    assert len(dealer.deck) == 52
    assert dealer.status == 'alive'
    assert dealer.score == 0

def test_blackjack_dealer_multiple_decks():
    rng = np.random.default_rng(42)
    num_decks = 2
    dealer = BlackjackDealer(rng, num_decks=num_decks)
    assert len(dealer.deck) == 52 * num_decks

def test_shuffle():
    rng = np.random.default_rng(42)
    dealer = BlackjackDealer(rng, num_decks=1)
    deck_before = list(dealer.deck)
    dealer.shuffle()
    assert dealer.deck != deck_before
    assert len(dealer.deck) == 52

def test_deal_card():
    rng = np.random.default_rng(42)
    dealer = BlackjackDealer(rng, num_decks=1)
    
    # Mock de un player
    player = MagicMock()
    player.hand = []
    
    initial_deck_size = len(dealer.deck)
    dealer.deal_card(player)
    
    assert len(player.hand) == 1
    assert len(dealer.deck) == initial_deck_size - 1

def test_deal_card_infinite_decks():
    rng = np.random.default_rng(42)
    dealer = BlackjackDealer(rng, num_decks=0)
    
    player = MagicMock()
    player.hand = []
    
    initial_deck_size = len(dealer.deck)
    dealer.deal_card(player)
    
    assert len(player.hand) == 1
    # Con num_decks=0, el tamaño no debería cambiar (no se hace pop)
    assert len(dealer.deck) == initial_deck_size