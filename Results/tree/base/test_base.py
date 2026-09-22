import sys
import os
import importlib.util

# 1. Asegurar rutas en sys.path para dependencias internas
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/tree']:
    if p not in sys.path:
        sys.path.insert(0, p)

# 2. Cargar explícitamente el módulo bajo prueba sin modificar Public_Proyects
if 'tree.base' not in sys.modules:
    spec = importlib.util.spec_from_file_location('tree.base', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/tree/base.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules['tree.base'] = mod
    try:
        spec.loader.exec_module(mod)
    except Exception as e:
        pass

import pytest
import numpy as np
from tree.base import f_entropy, information_gain, mse_criterion, get_split_mask, split, split_dataset

def test_f_entropy():
    p = np.array([0, 0, 1, 1])
    entropy = f_entropy(p)
    assert isinstance(entropy, float)
    assert entropy >= 0

def test_information_gain():
    y = np.array([0, 0, 1, 1])
    splits = [np.array([0, 0]), np.array([1, 1])]
    gain = information_gain(y, splits)
    assert gain > 0

def test_mse_criterion():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    splits = [np.array([1.0, 2.0]), np.array([3.0, 4.0])]
    mse = mse_criterion(y, splits)
    assert isinstance(mse, float)

def test_get_split_mask():
    X = np.array([[1, 2], [3, 4], [5, 6]])
    column = 0
    value = 3
    left, right = get_split_mask(X, column, value)
    assert np.array_equal(left, [True, False, False])
    assert np.array_equal(right, [False, True, True])

def test_split():
    X = np.array([1, 2, 3, 4, 5])
    y = np.array([10, 20, 30, 40, 50])
    value = 3
    left_y, right_y = split(X, y, value)
    assert len(left_y) == 2
    assert len(right_y) == 3
    assert np.array_equal(left_y, [10, 20])

def test_split_dataset():
    X = np.array([[1], [2], [3], [4]])
    target = {"y": np.array([0, 0, 1, 1])}
    column = 0
    value = 3
    left_X, right_X, left_target, right_target = split_dataset(X, target, column, value, return_X=True)
    assert len(left_X) == 2
    assert len(right_X) == 2
    assert np.array_equal(left_target["y"], [0, 0])
    assert np.array_equal(right_target["y"], [1, 1])

def test_split_dataset_no_X():
    X = np.array([[1], [2], [3], [4]])
    target = {"y": np.array([0, 0, 1, 1])}
    column = 0
    value = 3
    left, right = split_dataset(X, target, column, value, return_X=False)
    assert "y" in left
    assert "y" in right
    assert len(left["y"]) == 2