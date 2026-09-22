import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/stock4']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
from stock4.validate import Integer, Float, String, Positive, NonEmpty, PositiveInteger, PositiveFloat, NonEmptyString, validated, enforce

def test_type_validators():
    assert Integer.check(10) == 10
    assert Float.check(10.5) == 10.5
    assert String.check("test") == "test"
    
    with pytest.raises(TypeError):
        Integer.check("not an int")
    with pytest.raises(TypeError):
        Float.check(10)
    with pytest.raises(TypeError):
        String.check(123)

def test_logic_validators():
    assert Positive.check(5) == 5
    with pytest.raises(ValueError):
        Positive.check(-1)
        
    assert NonEmpty.check("abc") == "abc"
    with pytest.raises(ValueError):
        NonEmpty.check("")

def test_combined_validators():
    assert PositiveInteger.check(10) == 10
    with pytest.raises(TypeError):
        PositiveInteger.check("1")
    with pytest.raises(ValueError):
        PositiveInteger.check(-5)

    assert NonEmptyString.check("hello") == "hello"
    with pytest.raises(ValueError):
        NonEmptyString.check("")

def test_validated_decorator():
    @validated
    def add(x: Integer, y: Integer) -> Integer:
        return x + y

    assert add(1, 2) == 3
    
    with pytest.raises(TypeError, match="Bad Arguments"):
        add(1, "2")
        
    @validated
    def get_string() -> NonEmptyString:
        return ""
    
    with pytest.raises(TypeError, match="Bad return"):
        get_string()

def test_enforce_decorator():
    @enforce(x=PositiveInteger, return_=PositiveInteger)
    def double(x):
        return x * 2

    assert double(5) == 10
    
    with pytest.raises(TypeError, match="Bad Arguments"):
        double(-1)
        
    @enforce(x=PositiveInteger, return_=PositiveInteger)
    def fail(x):
        return -x
        
    with pytest.raises(TypeError, match="Bad return"):
        fail(5)

def test_validator_subclass_registry():
    from stock4.validate import Validator
    assert "Integer" in Validator.validators
    assert "Positive" in Validator.validators
    assert "PositiveInteger" in Validator.validators