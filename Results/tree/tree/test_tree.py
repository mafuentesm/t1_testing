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

import tree.tree as target
import numpy as np

def test_tree_initialization():
    tree_inst = target.Tree(regression=True, criterion=None, n_classes=2)
    assert tree_inst.regression is True
    assert tree_inst.criterion is None
    assert tree_inst.n_classes == 2
    assert tree_inst.is_terminal is True

def test_is_terminal_property():
    tree_inst = target.Tree()
    assert tree_inst.is_terminal is True
    tree_inst.left_child = target.Tree()
    assert tree_inst.is_terminal is True
    tree_inst.right_child = target.Tree()
    assert tree_inst.is_terminal is False

def test_find_splits():
    tree_inst = target.Tree()
    X = np.array([1.0, 2.0, 4.0])
    splits = tree_inst._find_splits(X)
    expected = [1.5, 3.0]
    assert sorted(splits) == sorted(expected)

def test_calculate_leaf_value_regression():
    tree_inst = target.Tree(regression=True)
    targets = {'y': np.array([2.0, 4.0, 6.0])}
    tree_inst._calculate_leaf_value(targets)
    assert tree_inst.outcome == 4.0

def test_calculate_leaf_value_classification():
    tree_inst = target.Tree(regression=False, n_classes=2)
    targets = {'y': np.array([0, 1, 0, 0])}
    tree_inst._calculate_leaf_value(targets)
    np.testing.assert_array_equal(tree_inst.outcome, np.array([3 / 4, 1 / 4]))

def test_predict_row_terminal():
    tree_inst = target.Tree()
    tree_inst.outcome = 42.0
    row = np.array([1.0, 2.0])
    assert tree_inst.predict_row(row) == 42.0

def test_predict_row_non_terminal():
    tree_inst = target.Tree()
    tree_inst.column_index = 0
    tree_inst.threshold = 5.0
    left = target.Tree()
    left.outcome = 1.0
    right = target.Tree()
    right.outcome = 2.0
    tree_inst.left_child = left
    tree_inst.right_child = right
    assert tree_inst.predict_row(np.array([3.0, 0.0])) == 1.0
    assert tree_inst.predict_row(np.array([6.0, 0.0])) == 2.0

def test_predict():
    tree_inst = target.Tree()
    tree_inst.outcome = 10.0
    X = np.array([[1.0], [2.0], [3.0]])
    predictions = tree_inst.predict(X)
    np.testing.assert_array_equal(predictions, np.array([10.0, 10.0, 10.0]))

def test_train_creates_terminal_on_insufficient_samples():
    tree_inst = target.Tree(regression=True)
    X = np.array([[1.0], [2.0]])
    target_data = {'y': np.array([1.0, 2.0])}
    tree_inst.train(X, target_data, min_samples_split=5)
    assert tree_inst.is_terminal is True
    assert tree_inst.outcome == 1.5

def test_train_successful_regression():

    def dummy_criterion(y, splits):
        return 0.5
    tree_inst = target.Tree(regression=True, criterion=dummy_criterion)
    X = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [4.0, 40.0], [5.0, 50.0], [6.0, 60.0]])
    y = np.array([1.0, 1.0, 1.0, 10.0, 10.0, 10.0])
    tree_inst.train(X, y, max_features=2, min_samples_split=2, max_depth=2, minimum_gain=0.01)
    assert tree_inst.is_terminal is False
    assert tree_inst.column_index is not None
    assert tree_inst.threshold is not None

def test_train_successful_classification():

    def dummy_criterion(y, splits):
        return 0.8
    tree_inst = target.Tree(regression=False, criterion=dummy_criterion)
    X = np.array([[1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [4.0, 40.0], [5.0, 50.0], [6.0, 60.0]])
    y = np.array([0, 0, 0, 1, 1, 1])
    tree_inst.train(X, y, max_features=2, min_samples_split=2, max_depth=2, minimum_gain=0.01)
    assert tree_inst.is_terminal is False
    assert tree_inst.n_classes == 2
