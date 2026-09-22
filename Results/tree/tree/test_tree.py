import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/tree']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
import numpy as np
import sys
import os

sys.path.append(os.getcwd())

from tree.tree import Tree

@pytest.fixture
def sample_data():
    X = np.array([[1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [1, 2], [3, 4], [5, 6], [7, 8], [9, 10], [1, 2]])
    y = np.array([0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0])
    return X, y

def test_tree_initialization():
    tree = Tree(regression=False)
    assert tree.regression is False
    assert tree.left_child is None
    assert tree.right_child is None

def test_is_terminal():
    tree = Tree()
    assert tree.is_terminal is True
    tree.left_child = Tree()
    tree.right_child = Tree()
    assert tree.is_terminal is False

def test_find_splits():
    tree = Tree()
    X = np.array([1, 2, 3, 4])
    splits = tree._find_splits(X)
    assert 1.5 in splits
    assert 2.5 in splits
    assert 3.5 in splits
    assert len(splits) == 3

def test_train_creates_leaf_when_conditions_not_met():
    tree = Tree(regression=False)
    X = np.array([[1], [2]])
    y = np.array([0, 1])
    tree.train(X, y, max_depth=0, min_samples_split=10)
    assert tree.is_terminal is True
    assert tree.outcome is not None

def test_predict_single_row(sample_data):
    X, y = sample_data
    tree = Tree(regression=False)
    tree.train(X, y, max_depth=2, min_samples_split=2)
    
    row = np.array([1, 2])
    prediction = tree.predict_row(row)
    assert isinstance(prediction, np.ndarray)

def test_predict_multiple_rows(sample_data):
    X, y = sample_data
    tree = Tree(regression=False)
    tree.train(X, y, max_depth=2, min_samples_split=2)
    
    predictions = tree.predict(X)
    assert len(predictions) == X.shape[0]

def test_regression_mode():
    tree = Tree(regression=True)
    X = np.array([[1], [2], [3], [4], [5], [6], [7], [8], [9], [10], [11]])
    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0])
    tree.train(X, y, max_depth=2, min_samples_split=2)
    assert tree.regression is True
    assert tree.outcome is not None or tree.left_child is not None