import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/fuzzywuzzy']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from fuzzywuzzy.fuzz import ratio, partial_ratio, token_sort_ratio, partial_token_sort_ratio, token_set_ratio, partial_token_set_ratio, QRatio, WRatio

def test_ratio():
    assert ratio("this is a test", "this is a test!") == 96
    assert ratio("test", "test") == 100
    assert ratio("", "test") == 0

def test_partial_ratio():
    assert partial_ratio("this is a test", "this is a test!") == 100
    assert partial_ratio("test", "this is a test") == 100

def test_token_sort_ratio():
    assert token_sort_ratio("fuzzy wuzzy was a bear", "wuzzy fuzzy was a bear") == 100
    assert token_sort_ratio("fuzzy wuzzy", "fuzzy wuzzy bear") < 100

def test_partial_token_sort_ratio():
    assert partial_token_sort_ratio("fuzzy wuzzy", "fuzzy wuzzy bear") == 100

def test_token_set_ratio():
    assert token_set_ratio("fuzzy was a bear", "fuzzy fuzzy was a bear") == 100
    assert token_set_ratio("fuzzy wuzzy", "wuzzy fuzzy") == 100

def test_partial_token_set_ratio():
    assert partial_token_set_ratio("fuzzy was a bear", "fuzzy") == 100

def test_qratio():
    assert QRatio("test", "test") == 100
    assert QRatio("test", "other") < 50

def test_wratio():
    # WRatio should be 100 for identical strings
    assert WRatio("fuzzy wuzzy", "fuzzy wuzzy") == 100
    # WRatio should handle different lengths appropriately
    assert WRatio("test", "this is a very long test string") > 0
    assert WRatio("a", "a") == 100

def test_empty_inputs():
    assert ratio("", "") == 0
    assert partial_ratio("", "test") == 0
    assert token_sort_ratio("", "") == 0
    assert token_set_ratio("", "") == 0
    assert QRatio("", "") == 0
    assert WRatio("", "") == 0

def test_none_inputs():
    assert ratio(None, "test") == 0
    assert WRatio(None, None) == 0