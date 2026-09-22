import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/fuzzywuzzy']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from fuzzywuzzy.string_processing import StringProcessor

def test_replace_non_letters_non_numbers_with_whitespace():
    input_str = "hello, world! 123."
    expected = "hello  world  123 "
    assert StringProcessor.replace_non_letters_non_numbers_with_whitespace(input_str) == expected

def test_replace_non_letters_non_numbers_with_whitespace_unicode():
    input_str = "café@tés#123"
    expected = "café tés 123"
    assert StringProcessor.replace_non_letters_non_numbers_with_whitespace(input_str) == expected

def test_strip():
    input_str = "  hello  "
    assert StringProcessor.strip(input_str) == "hello"

def test_to_lower_case():
    input_str = "HELLO"
    assert StringProcessor.to_lower_case(input_str) == "hello"

def test_to_upper_case():
    input_str = "hello"
    assert StringProcessor.to_upper_case(input_str) == "HELLO"

def test_replace_with_multiple_special_chars():
    input_str = "a!!!b@@@c"
    # El regex \W reemplaza cada caracter no alfanumérico individualmente, 
    # por lo que múltiples caracteres generan múltiples espacios.
    assert StringProcessor.replace_non_letters_non_numbers_with_whitespace(input_str) == "a   b   c"