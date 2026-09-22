import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/svm']:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
import numpy as np
import sys
import os

# Configuración del path para encontrar los módulos
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from svm.svm import SVM

@pytest.fixture
def sample_data():
    X = np.array([[1, 2], [2, 3], [3, 3], [2, 1], [3, 2]])
    y = np.array([1, 1, 1, -1, -1])
    return X, y

def test_svm_initialization():
    model = SVM(C=2.0, tol=1e-4, max_iter=200)
    assert model.C == 2.0
    assert model.tol == 1e-4
    assert model.max_iter == 200
    assert model.b == 0

def test_svm_fit(sample_data):
    X, y = sample_data
    model = SVM(C=1.0)
    model.fit(X, y)
    assert model.alpha is not None
    assert len(model.alpha) == len(y)
    assert np.all(model.alpha >= 0)

def test_svm_predict(sample_data):
    X, y = sample_data
    model = SVM(C=1.0)
    model.fit(X, y)
    predictions = model._predict(X)
    assert predictions.shape == y.shape
    assert set(np.unique(predictions)).issubset({-1.0, 1.0})

def test_svm_clip():
    model = SVM()
    assert model.clip(10, 5, 0) == 5
    assert model.clip(-1, 5, 0) == 0
    assert model.clip(2, 5, 0) == 2

def test_svm_find_bounds():
    model = SVM(C=1.0)
    model.y = np.array([1, -1])
    model.alpha = np.array([0.5, 0.5])
    
    # i=0, j=1: y[i] != y[j]
    L, H = model._find_bounds(0, 1)
    assert L == 0
    assert H == 1.0
    
    # i=0, j=1: y[i] == y[j]
    model.y = np.array([1, 1])
    L, H = model._find_bounds(0, 1)
    assert L == 0
    assert H == 1.0

def test_svm_random_index(sample_data):
    X, y = sample_data
    model = SVM()
    model.n_samples = len(X)
    # Ejecutamos varias veces
    indices = [model.random_index(0) for _ in range(50)]
    for idx in indices:
        assert idx != 0
        assert 0 <= idx < len(X)