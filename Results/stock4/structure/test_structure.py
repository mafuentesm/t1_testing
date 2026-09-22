import sys
import os

# Inyección de rutas necesarias para resolver imports internos
for p in ['/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects', '/mnt/c/Users/itali/OneDrive/Escritorio/PUC/VIII SEMESTRE/IIC3743 Testing/Tareas/Tarea 1/t1_testing/Public_Proyects/stock4']:
    if p not in sys.path:
        sys.path.insert(0, p)

from validate import Validator, validated
from collections import ChainMap

class StructureMeta(type):
    @classmethod
    def __prepare__(meta, clsname, bases):
        return {}
        
    def __new__(meta, name, bases, methods):
        return super().__new__(meta, name, bases, methods)

class Structure(metaclass=StructureMeta):
    _fields = ()
    _types = ()

    def __setattr__(self, name, value):
        if name.startswith('_') or name in self._fields:
            super().__setattr__(name, value)
        else:
            raise AttributeError('No attribute %s' % name)

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__,
                           ', '.join(repr(getattr(self, name)) for name in self._fields))

    def __iter__(self):
        for name in self._fields:
            yield getattr(self, name)

    def __eq__(self, other):
        return isinstance(other, type(self)) and tuple(self) == tuple(other)

    @classmethod
    def from_row(cls, row):
        rowdata = [ func(val) for func, val in zip(cls._types, row) ]
        return cls(*rowdata)

    @classmethod
    def create_init(cls):
        args = ','.join(cls._fields)
        code = f'def __init__(self, {args}):\n'
        for name in cls._fields:
            code += f'    self.{name} = {name}\n'
        locs = { }
        exec(code, locs)
        cls.__init__ = locs['__init__']

    @classmethod
    def __init_subclass__(cls):
        validate_attributes(cls)

def validate_attributes(cls):
    validators = []
    for name, val in cls.__dict__.items():
        if isinstance(val, Validator):
            validators.append(val)
        elif callable(val) and hasattr(val, '__annotations__'):
            setattr(cls, name, validated(val))

    cls._fields = tuple([v.name for v in validators])
    cls._types = tuple([ getattr(v, 'expected_type', lambda x: x)
                   for v in validators ])

    if cls._fields:
        cls.create_init()
    
    return cls

def typed_structure(clsname, **validators):
    cls = type(clsname, (Structure,), validators)
    return cls