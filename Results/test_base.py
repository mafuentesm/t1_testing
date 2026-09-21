
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLIC_PROJECTS_ROOT = os.path.join(PROJECT_ROOT, "Public_Proyects")

# Directorio propio del paquete bajo prueba (ej. Public_Proyects/gin_rummy).
# Necesario porque varios de estos proyectos usan imports "planos" internos
# (ej. "import utils" en vez de "from . import utils").
PAQUETE_RELATIVO = 'gin_rummy'

extra_paths = [PROJECT_ROOT, PUBLIC_PROJECTS_ROOT]
if PAQUETE_RELATIVO:
    extra_paths.append(os.path.join(PUBLIC_PROJECTS_ROOT, PAQUETE_RELATIVO))

for path in extra_paths:
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)

import pytest
from Public_Proyects.gin_rummy.base import Card

def test_card_initialization():
    card = Card('S', 'A')
    assert card.suit == 'S'
    assert card.rank == 'A'

def test_card_equality():
    card1 = Card('H', '5')
    card2 = Card('H', '5')
    card3 = Card('D', '5')
    assert card1 == card2
    assert card1 != card3
    assert card1 != "5H"

def test_card_hash():
    card1 = Card('S', 'A')
    card2 = Card('S', 'A')
    card3 = Card('H', '2')
    assert hash(card1) == hash(card2)
    assert hash(card1) != hash(card3)

def test_card_str():
    card = Card('D', 'J')
    assert str(card) == 'JD'

def test_card_get_index():
    card = Card('C', '3')
    assert card.get_index() == 'C3'

def test_card_invalid_comparisons():
    card = Card('S', 'A')
    assert (card == 123) is False

def test_card_valid_suit_and_rank_attributes():
    assert 'S' in Card.valid_suit
    assert 'A' in Card.valid_rank
    assert len(Card.valid_suit) == 6
    assert len(Card.valid_rank) == 13