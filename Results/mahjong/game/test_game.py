import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/mahjong']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from unittest.mock import MagicMock
from mahjong.game import MahjongGame

@pytest.fixture
def game():
    return MahjongGame(allow_step_back=True)

def test_init_game(game):
    state, player_id = game.init_game()
    assert state is not None
    assert 0 <= player_id < 4
    assert len(game.players) == 4
    assert game.num_players == 4

def test_get_num_actions(game):
    assert game.get_num_actions() == 38

def test_get_num_players(game):
    assert game.get_num_players() == 4

def test_step_back_no_history(game):
    # Inicializamos para asegurar que el atributo history exista
    game.history = []
    assert game.step_back() is False

def test_step_back_with_history(game):
    game.history = [("d", "p", "r")]
    success = game.step_back()
    assert success is True
    assert len(game.history) == 0

def test_get_legal_actions_play_case(game):
    state = {'valid_act': ['play'], 'action_cards': ['1m', '2m']}
    actions = MahjongGame.get_legal_actions(state)
    assert actions == ['1m', '2m']
    assert state['valid_act'] == ['1m', '2m']

def test_get_legal_actions_other_case(game):
    state = {'valid_act': ['chi', 'pon']}
    actions = MahjongGame.get_legal_actions(state)
    assert actions == ['chi', 'pon']

def test_is_over(game):
    game.init_game()
    game.judger = MagicMock()
    game.judger.judge_game.return_value = (True, 0, None)
    assert game.is_over() is True
    assert game.winner == 0

def test_get_player_id(game):
    game.init_game()
    current_id = game.get_player_id()
    assert current_id == game.round.current_player