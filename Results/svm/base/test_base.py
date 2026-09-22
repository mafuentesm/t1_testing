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

# Configuración del path para encontrar el paquete svm
sys.path.insert(0, os.path.abspath(os.path.join(os.getcwd(), '../..')))

from svm.base import BaseEstimator

class ConcreteEstimator(BaseEstimator):
    def _predict(self, X=None):
        return np.zeros(X.shape[0])

def test_setup_input_valid():
    estimator = BaseEstimator()
    X = np.array([[1, 2], [3, 4]])
    y = np.array([0, 1])
    estimator._setup_input(X, y)
    assert np.array_equal(estimator.X, X)
    assert np.array_equal(estimator.y, y)
    assert estimator.n_samples == 2
    assert estimator.n_features == 2

def test_setup_input_empty_matrix_raises_error():
    estimator = BaseEstimator()
    with pytest.raises(ValueError, match="Got an empty matrix."):
        estimator._setup_input(np.array([]), y=np.array([1]))

def test_setup_input_missing_y_raises_error():
    estimator = BaseEstimator()
    estimator.y_required = True
    with pytest.raises(ValueError, match="Missed required argument y"):
        estimator._setup_input(np.array([[1]]), y=None)

def test_setup_input_empty_y_raises_error():
    estimator = BaseEstimator()
    with pytest.raises(ValueError, match="The targets array must be no-empty."):
        estimator._setup_input(np.array([[1]]), y=np.array([]))

def test_fit_stores_data():
    estimator = ConcreteEstimator()
    X = np.array([[1]])
    y = np.array([1])
    estimator.fit(X, y)
    assert estimator.X is not None
    assert estimator.y is not None

def test_predict_without_fit_raises_error():
    estimator = ConcreteEstimator()
    estimator.X = None
    with pytest.raises(ValueError, match="You must call `fit` before `predict`"):
        estimator.predict(np.array([[1]]))

def test_predict_success():
    estimator = ConcreteEstimator()
    estimator.fit(np.array([[1]]), np.array([0]))
    result = estimator.predict(np.array([[1]]))
    assert len(result) == 1

def test_predict_not_implemented_error():
    class IncompleteEstimator(BaseEstimator):
        pass
    
    estimator = IncompleteEstimator()
    estimator.fit_required = False
    with pytest.raises(NotImplementedError):
        estimator.predict(np.array([[1]]))

def test_setup_input_1d_array():
    estimator = BaseEstimator()
    X = np.array([1, 2, 3])
    y = np.array([0])
    estimator._setup_input(X, y)
    assert estimator.n_samples == 1
    assert estimator.n_features == (3,)