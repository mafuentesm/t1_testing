# >>> PREAMBULO AGENTE (autogenerado, no editar) >>>
import sys
import os
import ast
import types
import importlib

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_TEST_DIR, '../../..'))
_PUBLIC_ROOT = os.path.join(_PROJECT_ROOT, "Public_Proyects")
_SOURCE_DIR = os.path.normpath(os.path.join(_TEST_DIR, '../../../Public_Proyects/svm'))

# 1. Configuración de sys.path
for _p in [_PUBLIC_ROOT, _PROJECT_ROOT, _SOURCE_DIR]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

_curr_pkg_name = 'svm'
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

import svm.base as target
import numpy as np
import pytest

def test_base_estimator_setup_input_valid():
    estimator = target.BaseEstimator()
    X = [[1, 2], [3, 4]]
    y = [0, 1]
    estimator._setup_input(X, y)
    assert isinstance(estimator.X, np.ndarray)
    assert isinstance(estimator.y, np.ndarray)
    assert estimator.n_samples == 2
    assert estimator.n_features == 2

def test_base_estimator_setup_input_1d():
    estimator = target.BaseEstimator()
    X = [1, 2, 3]
    y = [0, 1, 2]
    estimator._setup_input(X, y)
    assert isinstance(estimator.X, np.ndarray)
    assert estimator.n_samples == 1
    assert estimator.n_features == (3,)

def test_base_estimator_empty_matrix():
    estimator = target.BaseEstimator()
    with pytest.raises(ValueError, match='Got an empty matrix.'):
        estimator._setup_input([], [1])

def test_base_estimator_y_required_missing():
    estimator = target.BaseEstimator()
    with pytest.raises(ValueError, match='Missed required argument y'):
        estimator._setup_input([[1, 2]], None)

def test_base_estimator_y_empty():
    estimator = target.BaseEstimator()
    with pytest.raises(ValueError, match='The targets array must be no-empty.'):
        estimator._setup_input([[1, 2]], [])

def test_base_estimator_y_not_required():

    class DummyEstimator(target.BaseEstimator):
        y_required = False
    estimator = DummyEstimator()
    estimator._setup_input([[1, 2]], None)
    assert estimator.y is None
    assert estimator.n_samples == 1
    assert estimator.n_features == 2

def test_base_estimator_fit():
    estimator = target.BaseEstimator()
    X = [[1, 2]]
    y = [1]
    estimator.fit(X, y)
    assert estimator.X is not None
    assert estimator.y is not None

def test_base_estimator_predict_fitted():

    class DummyEstimator(target.BaseEstimator):

        def _predict(self, X=None):
            return X
    estimator = DummyEstimator()
    estimator.X = np.array([[1, 2]])
    res = estimator.predict([[3, 4]])
    assert isinstance(res, np.ndarray)
    np.testing.assert_array_equal(res, np.array([[3, 4]]))

def test_base_estimator_abstract_predict():
    estimator = target.BaseEstimator()
    estimator.X = np.array([[1, 2]])
    with pytest.raises(NotImplementedError):
        estimator.predict([[1, 2]])
