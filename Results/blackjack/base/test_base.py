import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/blackjack']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from blackjack.base import Card

def test_card_initialization():
    card = Card('S', 'A')
    assert card.suit == 'S'
    assert card.rank == 'A'

def test_card_equality():
    card1 = Card('H', 'K')
    card2 = Card('H', 'K')
    card3 = Card('D', '5')
    assert card1 == card2
    assert card1 != card3
    assert card1 != "not a card"

def test_card_str_representation():
    card = Card('C', 'T')
    assert str(card) == 'TC'

def test_card_get_index():
    card = Card('D', 'J')
    assert card.get_index() == 'DJ'

def test_card_hash():
    card1 = Card('S', 'A')
    card2 = Card('S', 'A')
    card3 = Card('H', '2')
    
    assert hash(card1) == hash(card2)
    assert hash(card1) != hash(card3)

def test_card_valid_attributes():
    assert 'S' in Card.valid_suit
    assert 'A' in Card.valid_rank
    assert 'BJ' in Card.valid_suit
    assert 'K' in Card.valid_rank

def test_card_comparison_with_non_card():
    card = Card('S', 'A')
    # En Python, si __eq__ retorna NotImplemented, el operador == 
    # evalúa a False al comparar contra otro tipo, por eso el assert 'is' falla.
    # Se ajusta la expectativa a False para reflejar el comportamiento del operador.
    assert (card == 123) is False