# >>> PREAMBULO AGENTE (autogenerado, no editar) >>>
import sys
import os
import ast
import types
import importlib

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_TEST_DIR, '../../..'))
_PUBLIC_ROOT = os.path.join(_PROJECT_ROOT, "Public_Proyects")
_SOURCE_DIR = os.path.normpath(os.path.join(_TEST_DIR, '../../../Public_Proyects/tree'))

# 1. Configuración de sys.path
for _p in [_PUBLIC_ROOT, _PROJECT_ROOT, _SOURCE_DIR]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

_curr_pkg_name = 'tree'
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

import numpy as np
import pytest
import tree.base as target


def test_f_entropy():
    p = np.array([0, 0, 1, 1])
    entropy = target.f_entropy(p)
    assert isinstance(entropy, float)
    assert entropy >= 0.0

    p_uniform = np.array([0, 1])
    entropy_uniform = target.f_entropy(p_uniform)
    assert entropy_uniform > 0.0


def test_information_gain():
    y = np.array([0, 0, 1, 1])
    splits = [np.array([0, 0]), np.array([1, 1])]
    gain = target.information_gain(y, splits)
    assert isinstance(gain, float)


def test_mse_criterion():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    splits = [np.array([1.0, 2.0]), np.array([3.0, 4.0])]
    criterion = target.mse_criterion(y, splits)
    assert isinstance(criterion, float)
    assert criterion <= 0.0


def test_xgb_criterion():
    class DummyLoss:
        def gain(self, actual, y_pred):
            return float(np.sum(actual))

    loss = DummyLoss()
    y = {"actual": np.array([1, 2]), "y_pred": np.array([1, 1])}
    left = {"actual": np.array([1]), "y_pred": np.array([1])}
    right = {"actual": np.array([2]), "y_pred": np.array([1])}

    gain = target.xgb_criterion(y, left, right, loss)
    assert isinstance(gain, float)
    assert gain == 0.0


def test_get_split_mask():
    X = np.array([[1, 2], [3, 4], [5, 6]])
    left_mask, right_mask = target.get_split_mask(X, 0, 3)
    assert isinstance(left_mask, np.ndarray)
    assert isinstance(right_mask, np.ndarray)
    assert left_mask.shape == (3,)
    assert right_mask.shape == (3,)
    assert np.array_equal(left_mask, np.array([True, False, False]))
    assert np.array_equal(right_mask, np.array([False, True, True]))


def test_split():
    X = np.array([1, 2, 3, 4])
    y = np.array([10, 20, 30, 40])
    left_y, right_y = target.split(X, y, 3)
    assert isinstance(left_y, np.ndarray)
    assert isinstance(right_y, np.ndarray)
    assert np.array_equal(left_y, np.array([10, 20]))
    assert np.array_equal(right_y, np.array([30, 40]))


def test_split_dataset_return_x():
    X = np.array([[1, 2], [3, 4], [5, 6]])
    target_dict = {"a": np.array([10, 20, 30])}
    left_X, right_X, left, right = target.split_dataset(X, target_dict, 0, 3, return_X=True)

    assert isinstance(left_X, np.ndarray)
    assert isinstance(right_X, np.ndarray)
    assert isinstance(left, dict)
    assert isinstance(right, dict)
    assert np.array_equal(left_X, np.array([[1, 2]]))
    assert np.array_equal(right_X, np.array([[3, 4], [5, 6]]))
    assert np.array_equal(left["a"], np.array([10]))
    assert np.array_equal(right["a"], np.array([20, 30]))


def test_split_dataset_no_return_x():
    X = np.array([[1, 2], [3, 4], [5, 6]])
    target_dict = {"a": np.array([10, 20, 30])}
    left, right = target.split_dataset(X, target_dict, 0, 3, return_X=False)

    assert isinstance(left, dict)
    assert isinstance(right, dict)
    assert np.array_equal(left["a"], np.array([10]))
    assert np.array_equal(right["a"], np.array([20, 30]))
