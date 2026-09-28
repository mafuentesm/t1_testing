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
import stock4.tableformat as target

class DummyRecord:

    def __init__(self, name, price):
        self.name = name
        self.price = price

def test_table_formatter_is_abstract():
    with pytest.raises(TypeError):
        target.TableFormatter()

def test_text_table_formatter(capsys):
    formatter = target.TextTableFormatter()
    formatter.headings(['Name', 'Price'])
    formatter.row(['A', '10'])
    captured = capsys.readouterr()
    assert 'Name' in captured.out
    assert 'Price' in captured.out
    assert 'A' in captured.out
    assert '10' in captured.out

def test_csv_table_formatter(capsys):
    formatter = target.CSVTableFormatter()
    formatter.headings(['Name', 'Price'])
    formatter.row(['A', 10])
    captured = capsys.readouterr()
    assert 'Name,Price' in captured.out
    assert 'A,10' in captured.out

def test_html_table_formatter(capsys):
    formatter = target.HTMLTableFormatter()
    formatter.headings(['Name', 'Price'])
    formatter.row(['A', 10])
    captured = capsys.readouterr()
    assert '<tr> <th>Name</th> <th>Price</th> </tr>' in captured.out
    assert '<tr> <td>A</td> <td>10</td> </tr>' in captured.out

def test_print_table_execution(capsys):
    records = [DummyRecord('Apple', 100)]
    fields = ['name', 'price']
    formatter = target.CSVTableFormatter()
    target.print_table(records, fields, formatter)
    captured = capsys.readouterr()
    assert 'name,price' in captured.out
    assert 'Apple,100' in captured.out

def test_create_formatter_text(capsys):
    formatter = target.create_formatter('text')
    assert isinstance(formatter, target.TextTableFormatter)

def test_create_formatter_csv(capsys):
    formatter = target.create_formatter('csv')
    assert isinstance(formatter, target.CSVTableFormatter)

def test_create_formatter_html(capsys):
    formatter = target.create_formatter('html')
    assert isinstance(formatter, target.HTMLTableFormatter)

def test_create_formatter_with_column_formats_and_upper(capsys):
    formatter = target.create_formatter('csv', column_formats=['%s', '%.2f'], upper_headers=True)
    formatter.headings(['name', 'price'])
    formatter.row(['Apple', 12.3456])
    captured = capsys.readouterr()
    assert 'NAME,PRICE' in captured.out
    assert 'Apple,12.35' in captured.out

def test_column_format_mixin_direct(capsys):

    class CustomFormatter(target.ColumnFormatMixin, target.CSVTableFormatter):
        formats = ['%s', '%d']
    formatter = CustomFormatter()
    formatter.headings(['col1', 'col2'])
    formatter.row(['test', 5.99])
    captured = capsys.readouterr()
    assert 'test,5' in captured.out

def test_upper_headers_mixin_direct(capsys):

    class CustomFormatter(target.UpperHeadersMixin, target.CSVTableFormatter):
        pass
    formatter = CustomFormatter()
    formatter.headings(['lower', 'case'])
    captured = capsys.readouterr()
    assert 'LOWER,CASE' in captured.out
