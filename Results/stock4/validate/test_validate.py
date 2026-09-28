# >>> PREAMBULO AGENTE (autogenerado, no editar) >>>
import sys
import os
import ast
import types
import importlib

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_TEST_DIR, '../../..'))
_PUBLIC_ROOT = os.path.join(_PROJECT_ROOT, "Public_Proyects")
_SOURCE_DIR = os.path.normpath(os.path.join(_TEST_DIR, '../../../Public_Proyects/stock4'))

# 1. Configuración de sys.path
for _p in [_PUBLIC_ROOT, _PROJECT_ROOT, _SOURCE_DIR]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

_curr_pkg_name = 'stock4'
_curr_pkg_dir = os.path.join(_PUBLIC_ROOT, _curr_pkg_name) if _curr_pkg_name else ""

if _curr_pkg_name and os.path.isdir(_curr_pkg_dir):
    class _DynamicPackage(types.ModuleType):
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            # A. Intento como submódulo hermano (ej: blackjack.dealer)
            sub_py = os.path.join(_curr_pkg_dir, f"{name}.py")
            if os.path.exists(sub_py):
                try:
                    mod = importlib.import_module(f"{self.__name__}.{name}")
                    setattr(self, name, mod)
                    return mod
                except Exception:
                    pass

            for f in sorted(os.listdir(_curr_pkg_dir)):
                if f.endswith(".py") and not f.startswith("__"):
                    mod_name = f[:-3]
                    f_full = os.path.join(_curr_pkg_dir, f)
                    try:
                        with open(f_full, "r", encoding="utf-8") as _src:
                            tree = ast.parse(_src.read(), filename=f_full)
                        for node in tree.body:
                            if isinstance(node, (ast.ClassDef, ast.FunctionDef)):
                                if node.name == name or node.name.lower().endswith(name.lower()):
                                    mod = importlib.import_module(f"{self.__name__}.{mod_name}")
                                    val = getattr(mod, node.name)
                                    setattr(self, name, val)
                                    return val
                    except Exception:
                        pass

            raise AttributeError(f"module {self.__name__!r} has no attribute {name!r}")

    pkg_mod = _DynamicPackage(_curr_pkg_name)
    pkg_mod.__path__ = [_curr_pkg_dir]
    pkg_mod.__file__ = os.path.join(_curr_pkg_dir, "__init__.py")
    sys.modules[_curr_pkg_name] = pkg_mod
# <<< PREAMBULO AGENTE <<<

import pytest
import stock4.validate as target

def test_validator_base_and_subclass():
    val = target.Validator("test_name")
    assert val.name == "test_name"

    class DummyClass:
        pass

    val.__set_name__(DummyClass, "other_name")
    assert val.name == "other_name"

    checked = target.Validator.check(42)
    assert checked == 42

    class DerivedValidator(target.Validator):
        pass

    assert "DerivedValidator" in target.Validator.validators

def test_validator_descriptor():
    class Sample:
        x = target.Validator()

    obj = Sample()
    obj.x = 100
    assert obj.x == 100

def test_typed_validator():
    class DummyTyped(target.Typed):
        expected_type = int

    assert DummyTyped.check(10) == 10

    with pytest.raises(TypeError):
        DummyTyped.check("not an int")

def test_dynamic_typed_classes():
    assert target.Integer.check(5) == 5
    with pytest.raises(TypeError):
        target.Integer.check("5")

    assert target.Float.check(5.5) == 5.5
    with pytest.raises(TypeError):
        target.Float.check(5)

    assert target.String.check("hello") == "hello"
    with pytest.raises(TypeError):
        target.String.check(123)

def test_positive_validator():
    assert target.Positive.check(0) == 0
    assert target.Positive.check(5) == 5

    with pytest.raises(ValueError):
        target.Positive.check(-1)

def test_non_empty_validator():
    assert target.NonEmpty.check([1, 2]) == [1, 2]
    assert target.NonEmpty.check("abc") == "abc"

    with pytest.raises(ValueError):
        target.NonEmpty.check("")

    with pytest.raises(ValueError):
        target.NonEmpty.check([])

def test_combined_validators():
    assert target.PositiveInteger.check(10) == 10
    with pytest.raises(ValueError):
        target.PositiveInteger.check(-5)
    with pytest.raises(TypeError):
        target.PositiveInteger.check(2.5)

    assert target.PositiveFloat.check(3.14) == 3.14
    with pytest.raises(ValueError):
        target.PositiveFloat.check(-0.1)
    with pytest.raises(TypeError):
        target.PositiveFloat.check("3.14")

    assert target.NonEmptyString.check("data") == "data"
    with pytest.raises(ValueError):
        target.NonEmptyString.check("")
    with pytest.raises(TypeError):
        target.NonEmptyString.check(99)

def test_isvalidator():
    assert target.isvalidator(target.Validator) is True
    assert target.isvalidator(target.PositiveInteger) is True
    assert target.isvalidator(int) is False
    assert target.isvalidator("not a class") is False

def test_validated_decorator_success():
    @target.validated
    def add(a: target.Integer, b: target.Integer) -> target.Integer:
        return a + b

    assert add(3, 4) == 7

def test_validated_decorator_argument_error():
    @target.validated
    def add(a: target.Integer, b: target.Integer):
        return a + b

    with pytest.raises(TypeError) as excinfo:
        add("three", 4)
    assert "Bad Arguments" in str(excinfo.value)

def test_validated_decorator_return_error():
    @target.validated
    def bad_return(a: target.Integer) -> target.Positive:
        return -5

    with pytest.raises(TypeError) as excinfo:
        bad_return(10)
    assert "Bad return" in str(excinfo.value)

def test_enforce_decorator_success():
    @target.enforce(a=target.Integer, return_=target.Positive)
    def double(a):
        return a * 2

    assert double(5) == 10

def test_enforce_decorator_argument_error():
    @target.enforce(a=target.Integer)
    def double(a):
        return a * 2

    with pytest.raises(TypeError) as excinfo:
        double("abc")
    assert "Bad Arguments" in str(excinfo.value)

def test_enforce_decorator_return_error():
    @target.enforce(a=target.Integer, return_=target.Positive)
    def double(a):
        return a * 2

    with pytest.raises(TypeError) as excinfo:
        double(-3)
    assert "Bad return" in str(excinfo.value)
