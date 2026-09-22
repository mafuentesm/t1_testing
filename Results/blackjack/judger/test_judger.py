import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/blackjack']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from unittest.mock import MagicMock
from blackjack.judger import BlackjackJudger

class MockCard:
    def __init__(self, rank):
        self.rank = rank

@pytest.fixture
def judger():
    return BlackjackJudger(np_random=None)

def test_judge_score_basic(judger):
    cards = [MockCard("2"), MockCard("3")]
    assert judger.judge_score(cards) == 5

def test_judge_score_with_ace_as_11(judger):
    cards = [MockCard("A"), MockCard("9")]
    assert judger.judge_score(cards) == 20

def test_judge_score_with_ace_as_1(judger):
    cards = [MockCard("A"), MockCard("9"), MockCard("5")]
    # 11+9+5 = 25 -> bust, adjust Ace to 1 -> 1+9+5 = 15
    assert judger.judge_score(cards) == 15

def test_judge_score_multiple_aces(judger):
    cards = [MockCard("A"), MockCard("A"), MockCard("9")]
    # 11+11+9 = 31 -> 21+9 = 30 -> 11+1+9 = 21
    assert judger.judge_score(cards) == 21

def test_judge_round_alive(judger):
    player = MagicMock()
    player.hand = [MockCard("K"), MockCard("5")]
    status, score = judger.judge_round(player)
    assert status == "alive"
    assert score == 15

def test_judge_round_bust(judger):
    player = MagicMock()
    player.hand = [MockCard("K"), MockCard("Q"), MockCard("5")]
    status, score = judger.judge_round(player)
    assert status == "bust"
    assert score == 25

def test_judge_game_player_bust(judger):
    game = MagicMock()
    game.players = [MagicMock(status='bust')]
    game.winner = {}
    judger.judge_game(game, 0)
    assert game.winner['player0'] == -1

def test_judge_game_dealer_bust(judger):
    game = MagicMock()
    game.players = [MagicMock(status='alive', score=15)]
    game.dealer = MagicMock(status='bust')
    game.winner = {}
    judger.judge_game(game, 0)
    assert game.winner['player0'] == 2

def test_judge_game_player_wins(judger):
    game = MagicMock()
    game.players = [MagicMock(status='alive', score=20)]
    game.dealer = MagicMock(status='alive', score=18)
    game.winner = {}
    judger.judge_game(game, 0)
    assert game.winner['player0'] == 2

def test_judge_game_dealer_wins(judger):
    game = MagicMock()
    game.players = [MagicMock(status='alive', score=17)]
    game.dealer = MagicMock(status='alive', score=20)
    game.winner = {}
    judger.judge_game(game, 0)
    assert game.winner['player0'] == -1

def test_judge_game_tie(judger):
    game = MagicMock()
    game.players = [MagicMock(status='alive', score=19)]
    game.dealer = MagicMock(status='alive', score=19)
    game.winner = {}
    judger.judge_game(game, 0)
    assert game.winner['player0'] == 1