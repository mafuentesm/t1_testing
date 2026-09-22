import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/gin_rummy']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from unittest.mock import MagicMock
import sys

sys.modules['utils'] = MagicMock()
from gin_rummy.action_event import (
    ActionEvent, ScoreNorthPlayerAction, ScoreSouthPlayerAction,
    DrawCardAction, PickUpDiscardAction, DeclareDeadHandAction,
    GinAction, DiscardAction, KnockAction, knock_action_id
)

def test_action_event_comparison():
    assert ActionEvent(1) == ActionEvent(1)
    assert ActionEvent(1) != ActionEvent(2)
    assert ActionEvent(1) != "not an object"

def test_get_num_actions():
    assert ActionEvent.get_num_actions() == knock_action_id + 52

def test_decode_action_basic():
    assert isinstance(ActionEvent.decode_action(0), ScoreNorthPlayerAction)
    assert isinstance(ActionEvent.decode_action(1), ScoreSouthPlayerAction)
    assert isinstance(ActionEvent.decode_action(2), DrawCardAction)
    assert isinstance(ActionEvent.decode_action(3), PickUpDiscardAction)
    assert isinstance(ActionEvent.decode_action(4), DeclareDeadHandAction)
    assert isinstance(ActionEvent.decode_action(5), GinAction)

def test_decode_action_invalid():
    with pytest.raises(Exception, match="unknown action_id=999"):
        ActionEvent.decode_action(999)

def test_discard_and_knock_actions():
    import utils
    mock_card = MagicMock()
    utils.get_card.return_value = mock_card
    utils.get_card_id.return_value = 0
    
    action = ActionEvent.decode_action(6)
    assert isinstance(action, DiscardAction)
    assert action.card == mock_card
    
    action = ActionEvent.decode_action(knock_action_id)
    assert isinstance(action, KnockAction)
    assert action.card == mock_card

def test_action_strings():
    assert str(ScoreNorthPlayerAction()) == "score N"
    assert str(ScoreSouthPlayerAction()) == "score S"
    assert str(DrawCardAction()) == "draw_card"
    assert str(PickUpDiscardAction()) == "pick_up_discard"
    assert str(DeclareDeadHandAction()) == "declare_dead_hand"
    assert str(GinAction()) == "gin"

    import utils
    mock_card = MagicMock()
    mock_card.__str__.return_value = "AH"
    utils.get_card_id.return_value = 0
    
    assert str(DiscardAction(mock_card)) == "discard AH"
    assert str(KnockAction(mock_card)) == "knock AH"