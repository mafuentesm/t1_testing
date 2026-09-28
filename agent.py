# librerias tipo stdlib
import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from dotenv import load_dotenv
# stack permitido
from google import genai # Para uso de API de Gemini
from google.genai import errors as genai_errors
from google.genai import types as genai_types
import httpx # dependencia de google-genai, para detectar errores de red
import pytest # para testing
import coverage # para coverage
import coverage.exceptions
# cosmic-ray para mutation testing!!!
import cosmic_ray.commands
from cosmic_ray.config import ConfigDict
from cosmic_ray.modules import find_modules, filter_paths
from cosmic_ray.mutating import mutate_and_test
from cosmic_ray.work_db import WorkDB, use_db
from cosmic_ray.work_item import TestOutcome, WorkerOutcome

# COMENTAR
import subprocess
import time
import ast
import textwrap
import re
import random
import shlex
import hashlib

load_dotenv()

# ----- CONFIGURACIÓN -----------------------------

MODELO_GEMINI = "gemini-3.5-flash-lite"
# Códigos HTTP transitorios ante los que vale la pena reintentar
CODIGOS_REINTENTABLES = {408, 429, 500, 502, 503, 504}

METRICAS_OBJETIVO = {"line_coverage": 0.80, "branch_coverage": 0.50, "mutation_score": 0.50}

TIMEOUT_PYTEST_SEG = 60           # Evita que un test con loop infinito / input() cuelgue al agente
LIMITE_ITERACIONES_SEG = 200      # Control de tiempo para el SLA de 4 minutos
PRESUPUESTO_MUTACION_SEG = 60.0   # Tiempo máximo por corrida de mutation testing

# Marcadores que delimitan el preámbulo inyectado en cada archivo de tests
MARCA_INICIO_PREAMBULO = "# >>> PREAMBULO AGENTE (autogenerado, no editar) >>>"
MARCA_FIN_PREAMBULO = "# <<< PREAMBULO AGENTE <<<"


class ErrorGemini(Exception):
    """Falla definitiva de la API de Gemini. sobrecarga=True si se agotaron los reintentos por 429/5xx."""
    def __init__(self, mensaje, sobrecarga=False):
        super().__init__(mensaje)
        self.sobrecarga = sobrecarga

# ----- FUNCIONES AUXILIARES -----------------------------

def resolver_test_file_path(ruta_archivo, output_folder_path):
    nombre_archivo = os.path.basename(os.path.normpath(ruta_archivo))
    nombre_base = os.path.splitext(nombre_archivo)[0]
    return os.path.join(output_folder_path, f"test_{nombre_base}.py")

def _esta_dentro_de(ruta, directorio):
    try:
        return os.path.commonpath([ruta, directorio]) == directorio
    except ValueError:  # distintas unidades en Windows
        return False

# COMENTAR
def resolver_modulo_importable(ruta_archivo):
    """
      Calcula la ruta de importación (dotted path) de ruta_archivo relativa a la
      raíz del proyecto (donde vive agent.py), para indicarle al LLM exactamente
      cómo debe importar el archivo bajo prueba
      (ej. Public_Proyects/fuzzywuzzy/fuzz.py -> fuzzywuzzy.fuzz).
      """

    project_root = os.path.dirname(os.path.abspath(__file__))
    public_projects_root = os.path.join(project_root, "Public_Proyects")
    abs_path = os.path.abspath(ruta_archivo)

    # Si está dentro de Public_Proyects, el módulo base es relativo a Public_Proyects
    if _esta_dentro_de(abs_path, public_projects_root):
        ruta_relativa = os.path.relpath(abs_path, public_projects_root)
    else:
        ruta_relativa = os.path.relpath(abs_path, project_root)

    sin_extension = os.path.splitext(ruta_relativa)[0]
    return sin_extension.replace(os.sep, ".")

# # COMENTAR
def obtener_simbolos_exportados(contenido_codigo: str) -> list:
    """Extrae las clases, funciones y variables globales directamente del código fuente."""
    try:
        arbol = ast.parse(contenido_codigo)
        simbolos = []
        for nodo in arbol.body:
            if isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not nodo.name.startswith("_"):
                    simbolos.append(nodo.name)
            elif isinstance(nodo, ast.Assign):
                for target_node in nodo.targets:
                    if isinstance(target_node, ast.Name) and not target_node.id.startswith("_"):
                        simbolos.append(target_node.id)
            elif isinstance(nodo, ast.AnnAssign):
                if isinstance(nodo.target, ast.Name) and not nodo.target.id.startswith("_"):
                    simbolos.append(nodo.target.id)
        return list(dict.fromkeys(simbolos))
    except Exception:
        return []

# COMENTAR
def limpiar_fences_markdown(texto) -> str:
    """
    Quita los bloques markdown de la respuesta del LLM. Si el modelo antepone
    texto explicativo antes del bloque ```python, se extrae solo el bloque.
    """
    if not texto:
        return ""
    texto = texto.strip()
    bloques = re.findall(r"```[ \t]*(?:python|py)?[ \t]*\n(.*?)(?:\n```|\Z)", texto, flags=re.DOTALL | re.IGNORECASE)
    if bloques:
        # El bloque más largo suele ser el archivo de tests completo
        return max(bloques, key=len).strip()
    return texto

def numerar_lineas(codigo: str) -> str:
    return "\n".join(f"{i:4d}| {linea}" for i, linea in enumerate(codigo.splitlines(), start=1))

def recortar_log(log: str, max_chars: int = 4000) -> str:
    """Conserva el inicio (primer traceback) y el final (resumen de pytest) del log."""
    if len(log) <= max_chars:
        return log
    mitad = max_chars // 2
    return log[:mitad] + "\n\n[... log recortado ...]\n\n" + log[-mitad:]

def separar_preambulo(contenido: str):
    """Retorna (preambulo, cuerpo). Si el archivo no tiene preámbulo, preambulo = ''."""
    idx_ini = contenido.find(MARCA_INICIO_PREAMBULO)
    idx_fin = contenido.find(MARCA_FIN_PREAMBULO)
    if idx_ini == -1 or idx_fin == -1 or idx_fin < idx_ini:
        return "", contenido
    fin = contenido.find("\n", idx_fin)
    fin = len(contenido) if fin == -1 else fin + 1
    return contenido[:fin], contenido[fin:]

def _a_texto(salida) -> str:
    if salida is None:
        return ""
    if isinstance(salida, bytes):
        return salida.decode("utf-8", errors="replace")
    return salida

# COMENTAR
def ejecutar_pytest_con_captura(test_file_path, timeout=TIMEOUT_PYTEST_SEG):
    """
    Ejecuta pytest en subproceso para aislar memoria y capturar el mensaje de error.
    Si la suite excede el timeout, se identifica el test que quedó colgado y se
    reporta como FAILED para que la poda pueda eliminarlo.
    Retorna: (compilo_y_paso: bool, error_message: str)
    """
    cmd = [sys.executable, "-m", "pytest", test_file_path, "-v", "--disable-warnings", "-p", "no:cacheprovider"]
    env = dict(os.environ, PYTHONUNBUFFERED="1")
    nombre_archivo = os.path.basename(test_file_path)
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        salida = _a_texto(e.stdout) + "\n" + _a_texto(e.stderr)
        resumen = []
        # Tests que ya habían fallado antes del cuelgue (líneas de progreso de -v)
        for m in re.finditer(r"::(\S+) (?:FAILED|ERROR)\b", salida):
            resumen.append(f"FAILED {nombre_archivo}::{m.group(1)}")
        # El test colgado es la última línea de progreso que no alcanzó a reportar resultado
        for linea in reversed(salida.splitlines()):
            m = re.search(r"::(\S+)", linea)
            if m:
                if not re.search(r"\b(PASSED|FAILED|ERROR|SKIPPED|XFAIL|XPASS)\b", linea):
                    resumen.append(f"FAILED {nombre_archivo}::{m.group(1)} - Timeout ({timeout}s)")
                break
        if not resumen:
            resumen.append(f"Timeout ({timeout}s) sin identificar el test")
        return False, salida + "\n" + "\n".join(resumen)

    pasan_todos = (res.returncode == 0)
    if pasan_todos:
        return True, ""
    # Se omiten las líneas de tests exitosos para no inflar el log
    lineas = [l for l in (res.stdout + "\n" + res.stderr).splitlines() if not re.search(r"::\S+ PASSED\b", l)]
    return False, "\n".join(lineas)

def check_gemini_api_key():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: No se encontró la variable GEMINI_API_KEY en el entorno.")
        sys.exit(1)
    return api_key

def _es_error_transitorio(e: Exception) -> bool:
    if isinstance(e, genai_errors.APIError):
        return e.code in CODIGOS_REINTENTABLES
    if isinstance(e, httpx.HTTPError):  # timeouts, conexión caída, etc.
        return True
    error_str = str(e)
    return any(
        k in error_str
        for k in ["503", "504", "INTERNAL", "High demand", "RESOURCE_EXHAUSTED", "ResourceExhausted", "UNAVAILABLE"]
    )

# COMENTAR
def ejecutar_llamada_gemini_robusta(
    prompt: str,
    max_reintentos: int = 3,
    max_espera_total_seg: int = 120,
    timeout_llamada_seg: int = 90
) -> str:
    """
    Ejecuta llamadas al modelo de Gemini con reintentos automáticos ante errores
    transitorios (429/5xx, red, respuesta vacía). Garantiza que el tiempo total
    acumulado en esperas de reintento NUNCA supere max_espera_total_seg, y que una
    llamada individual no quede colgada más de timeout_llamada_seg.
    Lanza ErrorGemini si no se pudo obtener una respuesta.
    """
    client = genai.Client(http_options=genai_types.HttpOptions(timeout=timeout_llamada_seg * 1000))
    tiempo_espera_acumulado = 0

    for intento in range(max_reintentos):
        try:
            response = client.models.generate_content(model=MODELO_GEMINI, contents=prompt)
            texto = limpiar_fences_markdown(response.text)
            if texto:
                return texto
            motivo = "respuesta vacía (posible bloqueo por seguridad o MAX_TOKENS)"
        except Exception as e:
            if not _es_error_transitorio(e):
                raise ErrorGemini(f"Error fatal no recuperable en Gemini: {e}") from e
            motivo = str(e)

        print(f"[API ERROR] Fallo transitorio (intento {intento + 1}/{max_reintentos}): {motivo}")

        # Calcular el tiempo de espera sugerido para esta ronda (15s, 20s, 25s...)
        espera_sugerida = 15 + (intento * 5)
        tiempo_restante_presupuesto = max_espera_total_seg - tiempo_espera_acumulado

        # Si aún quedan reintentos y queda tiempo en el presupuesto
        if intento < max_reintentos - 1 and tiempo_restante_presupuesto > 5:
            tiempo_a_esperar = min(espera_sugerida, tiempo_restante_presupuesto)
            print(f" -> Reintentando en {tiempo_a_esperar}s (espera acumulada: {tiempo_espera_acumulado + tiempo_a_esperar}s / {max_espera_total_seg}s)...")
            time.sleep(tiempo_a_esperar)
            tiempo_espera_acumulado += tiempo_a_esperar
        else:
            break

    raise ErrorGemini(
        f"Se agotó el presupuesto de reintentos ({tiempo_espera_acumulado}s acumulados).",
        sobrecarga=True,
    )

# -- -- FUNCIONES PRINCIPALES 1 -----------------------------

def read_file_content(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo en la ruta especificada: {file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        sys.exit(1)

#COMENTAR
def generar_tests(contenido_archivo, ruta_archivo):
    check_gemini_api_key()

    modulo_importable = resolver_modulo_importable(ruta_archivo)
    simbolos_validos = obtener_simbolos_exportados(contenido_archivo)
    simbolos_str = ", ".join(simbolos_validos) if simbolos_validos else "los definidos en el código"

    prompt = f"""Eres un agente experto en testing unitario con pytest.
Genera una suite de pruebas unitarias para el código fuente provisto.

Módulo a importar: {modulo_importable}
Identificadores declarados en el archivo: [{simbolos_str}]

Código fuente bajo prueba:
{contenido_archivo}

REGLAS GENERALES DE CONSTRUCCIÓN:
1. Primera línea de importación obligatoria:
   import {modulo_importable} as target
2. Utiliza única y estrictamente los identificadores provistos en la lista de declaraciones o definidos textualmente en el código fuente. Queda prohibido inferir o alterar nombres de tipos, funciones o variables.
3. Accede a las entidades exclusivamente mediante la notación: target.<identificador_exacto>.
4. Evita el uso de fixtures globales (@pytest.fixture); inicializa los objetos y dependencias de manera local e independiente dentro de cada función de test.
5. Cada función de prueba debe comenzar con el prefijo "test_".
6. No leas de stdin, no uses input(), no hagas llamadas de red ni bucles sin fin.

Devuelve exclusivamente código Python ejecutable, sin explicaciones ni bloques markdown.
"""

    print(f"\n--- VERIFICACIÓN DE SÍMBOLOS EXTRAÍDOS ---")
    print(f"Archivo: {ruta_archivo}")
    print(f"Símbolos reales detectados: {simbolos_validos}")
    print(f"------------------------------------------\n")

    return ejecutar_llamada_gemini_robusta(prompt)

# COMENTAR
def construir_preambulo(source_file_path: str, output_folder: str) -> str:
    """
    Genera el preámbulo que inicializa el paquete y resuelve alias/imports internos
    de forma transparente. Las rutas se calculan relativas al propio archivo de
    tests (__file__) para que la suite funcione en cualquier máquina.
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    public_projects_root = os.path.join(project_root, "Public_Proyects")
    source_abs = os.path.abspath(source_file_path)
    source_dir = os.path.dirname(source_abs)
    output_abs = os.path.abspath(output_folder)

    pkg_name = ""
    if _esta_dentro_de(source_abs, public_projects_root):
        partes = os.path.relpath(source_abs, public_projects_root).split(os.sep)
        if len(partes) > 1:
            pkg_name = partes[0]

    def _rel(ruta):
        try:
            return os.path.relpath(ruta, output_abs)
        except ValueError:  # distintas unidades en Windows: no hay ruta relativa
            return ruta

    setup_code = textwrap.dedent(f'''\
{MARCA_INICIO_PREAMBULO}
import sys
import os
import ast
import types
import importlib

_TEST_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.normpath(os.path.join(_TEST_DIR, {_rel(project_root)!r}))
_PUBLIC_ROOT = os.path.join(_PROJECT_ROOT, "Public_Proyects")
_SOURCE_DIR = os.path.normpath(os.path.join(_TEST_DIR, {_rel(source_dir)!r}))

# 1. Configuración de sys.path
for _p in [_PUBLIC_ROOT, _PROJECT_ROOT, _SOURCE_DIR]:
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

_curr_pkg_name = {pkg_name!r}
_curr_pkg_dir = os.path.join(_PUBLIC_ROOT, _curr_pkg_name) if _curr_pkg_name else ""

if _curr_pkg_name and os.path.isdir(_curr_pkg_dir):
    class _DynamicPackage(types.ModuleType):
        def __getattr__(self, name):
            if name.startswith("__"):
                raise AttributeError(name)
            # A. Intento como submódulo hermano (ej: blackjack.dealer)
            sub_py = os.path.join(_curr_pkg_dir, f"{{name}}.py")
            if os.path.exists(sub_py):
                try:
                    mod = importlib.import_module(f"{{self.__name__}}.{{name}}")
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
                                    mod = importlib.import_module(f"{{self.__name__}}.{{mod_name}}")
                                    val = getattr(mod, node.name)
                                    setattr(self, name, val)
                                    return val
                    except Exception:
                        pass

            raise AttributeError(f"module {{self.__name__!r}} has no attribute {{name!r}}")

    pkg_mod = _DynamicPackage(_curr_pkg_name)
    pkg_mod.__path__ = [_curr_pkg_dir]
    pkg_mod.__file__ = os.path.join(_curr_pkg_dir, "__init__.py")
    sys.modules[_curr_pkg_name] = pkg_mod
{MARCA_FIN_PREAMBULO}
''')
    return setup_code

# COMENTAR
def almacenar_tests(tests_code: str, source_file_path: str, output_folder: str):
    """
    Escribe el archivo de test agregando un preámbulo dinámico que inicializa
    el paquete y resuelve alias/imports internos de forma transparente.
    Si tests_code ya trae un preámbulo (p. ej. eco del LLM), se reemplaza.
    """
    os.makedirs(output_folder, exist_ok=True)
    test_file_path = resolver_test_file_path(source_file_path, output_folder)

    _, cuerpo = separar_preambulo(tests_code)
    final_content = construir_preambulo(source_file_path, output_folder) + "\n" + cuerpo.lstrip("\n")
    if not final_content.endswith("\n"):
        final_content += "\n"

    with open(test_file_path, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"Tests generados y almacenados en: {test_file_path}")

def _eliminar_bloque_top_level(lineas: list, idx: int) -> list:
    """
    Elimina la sentencia de nivel superior (función, clase, import, etc.) que
    contiene la línea idx, incluyendo sus decoradores y líneas de continuación.
    """
    def es_continuacion(linea):
        return (not linea.strip()) or linea[0] in " \t)]}" or linea.lstrip().startswith("#")

    inicio = idx
    while inicio > 0 and es_continuacion(lineas[inicio]):
        inicio -= 1
    while inicio > 0 and lineas[inicio - 1].startswith("@"):
        inicio -= 1
    fin = idx + 1
    while fin < len(lineas) and es_continuacion(lineas[fin]):
        fin += 1
    return lineas[:inicio] + lineas[fin:]

def _eliminar_tests_por_nombre(cuerpo: str, tests_a_borrar: set) -> str:
    """Elimina funciones test_ (también métodos dentro de clases) por nombre, vía AST."""
    arbol = ast.parse(cuerpo)

    def filtrar(nodos):
        return [
            n for n in nodos
            if not (isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in tests_a_borrar)
        ]

    nuevo_body = []
    for nodo in filtrar(arbol.body):
        if isinstance(nodo, ast.ClassDef):
            nodo.body = filtrar(nodo.body)
            if not nodo.body:
                continue
        nuevo_body.append(nodo)
    arbol.body = nuevo_body
    return ast.unparse(arbol) + "\n"

# COMENTAR
def podar_suite_con_ast(test_file_path: str, max_rondas: int = 6) -> bool:
    """
    Elimina físicamente del archivo de tests cualquier función test_ o sentencia
    global que provoque fallos en pytest (SyntaxError, errores de colección,
    AssertionError, timeouts). El preámbulo del agente nunca se modifica.
    Retorna True si la suite restante pasa al 100%.
    """
    nombre_archivo = os.path.basename(test_file_path)

    for _ in range(max_rondas):
        pasan, error_log = ejecutar_pytest_con_captura(test_file_path)
        if pasan:
            return True

        with open(test_file_path, "r", encoding="utf-8") as f:
            contenido = f.read()
        preambulo, cuerpo = separar_preambulo(contenido)
        offset = preambulo.count("\n")
        lineas = cuerpo.splitlines(keepends=True)
        nuevo_cuerpo = None

        # 1. Errores de sintaxis: se elimina la sentencia top-level que contiene la línea rota
        try:
            compile(cuerpo, test_file_path, "exec")
            error_sintaxis = None
        except SyntaxError as e:
            error_sintaxis = e

        if error_sintaxis is not None:
            idx = (error_sintaxis.lineno or 1) - 1
            if 0 <= idx < len(lineas):
                nuevo_cuerpo = "".join(_eliminar_bloque_top_level(lineas, idx))

        # 2. Errores de colección (ImportError, AttributeError, NameError a nivel de módulo)
        elif re.search(r"errors? during collection|ERROR collecting", error_log):
            refs = re.findall(rf"{re.escape(nombre_archivo)}:(\d+):", error_log)
            if refs:
                # La última referencia al archivo de tests es el frame más profundo dentro de él
                idx = int(refs[-1]) - 1 - offset
                if 0 <= idx < len(lineas):
                    nuevo_cuerpo = "".join(_eliminar_bloque_top_level(lineas, idx))

        # 3. Funciones test_ específicas que fallaron (incluye métodos de clases y parametrizados)
        else:
            tests_a_borrar = {
                m.group(1) for m in re.finditer(r"^(?:FAILED|ERROR)\s+.*?::(?:\w+::)?(test_\w+)", error_log, flags=re.MULTILINE)
            }
            if tests_a_borrar:
                try:
                    nuevo_cuerpo = _eliminar_tests_por_nombre(cuerpo, tests_a_borrar)
                except SyntaxError:
                    nuevo_cuerpo = None

        if nuevo_cuerpo is None or nuevo_cuerpo == cuerpo:
            break

        with open(test_file_path, "w", encoding="utf-8") as f:
            f.write(preambulo + nuevo_cuerpo)

    pasan_final, _ = ejecutar_pytest_con_captura(test_file_path)
    return pasan_final

# -- -- FUNCIONES PRINCIPALES 2 -----------------------------

def calcular_cobertura(cov, source_file_path):
    """
    Extrae line_coverage y branch_coverage (0.0-1.0) del archivo fuente a partir
    de un objeto coverage.Coverage ya detenido, usando el reporte JSON de coverage.py
    (que expone porcentajes de statements y de branches por separado).
    Retorna además las líneas y ramas no cubiertas, para guiar al LLM.
    """
    json_report_path = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
            json_report_path = tmp_file.name

        cov.json_report(morfs=[source_file_path], outfile=json_report_path)

        with open(json_report_path, 'r', encoding='utf-8') as file:
            report_data = json.load(file)

        totals = report_data.get("totals", {})
        line_coverage = totals.get("percent_statements_covered", 0.0) / 100.0
        branch_coverage = totals.get("percent_branches_covered", 0.0) / 100.0

        archivos = list(report_data.get("files", {}).values())
        detalle = archivos[0] if archivos else {}
        return line_coverage, branch_coverage, detalle.get("missing_lines", []), detalle.get("missing_branches", [])
    except coverage.exceptions.NoDataError:
        return 0.0, 0.0, [], []
    finally:
        if json_report_path and os.path.exists(json_report_path):
            os.remove(json_report_path)

def calcular_mutation_score(source_file_path, test_file_path, timeout=None, presupuesto_seg=PRESUPUESTO_MUTACION_SEG):
    """
    Ejecuta mutation testing con la librería cosmic-ray sobre source_file_path,
    utilizando los tests de test_file_path. Usa cosmic_ray.commands.init y
    cosmic_ray.mutating.mutate_and_test (lo mismo que ejecuta su distribuidor
    local), pero con un presupuesto de tiempo: si hay demasiados mutantes, se
    evalúa una muestra aleatoria reproducible.
    Devuelve la proporción de mutantes eliminados (0.0-1.0).
    """
    cmd = [sys.executable, "-m", "pytest", test_file_path, "-q", "-x", "--disable-warnings", "-p", "no:cacheprovider"]
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")

    # Línea base: la suite DEBE pasar sin mutantes. Si no, cosmic-ray contaría
    # cada mutante como "killed" y el score sería un falso 100%.
    t0 = time.perf_counter()
    try:
        base = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, env=env, timeout=TIMEOUT_PYTEST_SEG)
    except subprocess.TimeoutExpired:
        print("[MUTACIÓN] La suite base excede el timeout; mutation_score = 0.")
        return 0.0
    if base.returncode != 0:
        print("[MUTACIÓN] La suite base no pasa en el entorno de mutación; mutation_score = 0.")
        return 0.0
    duracion_base = time.perf_counter() - t0
    if timeout is None:
        # Un mutante que causa loop infinito se considera killed al exceder este tiempo
        timeout = max(10.0, 3.0 * duracion_base)

    test_command = " ".join(shlex.quote(p) for p in cmd)  # rutas con espacios
    config = ConfigDict({
        "module-path": source_file_path,
        "timeout": timeout,
        "excluded-modules": [],
        "test-command": test_command,
        "distributor": {"name": "local"},
    })

    modules = find_modules([Path(config["module-path"])])
    modules = filter_paths(modules, config.get("excluded-modules", ()))

    # Respaldo del fuente: cosmic-ray lo muta in-place
    with open(source_file_path, "rb") as f:
        contenido_original = f.read()

    deadline = time.perf_counter() + presupuesto_seg
    try:
        with tempfile.TemporaryDirectory() as tmp_dir:
            session_path = os.path.join(tmp_dir, "session.sqlite")

            with use_db(session_path) as db:
                cosmic_ray.commands.init(modules, db, config.operators_config)

            with use_db(session_path, mode=WorkDB.Mode.open) as db:
                pendientes = list(db.pending_work_items)
                random.Random(0).shuffle(pendientes)
                for item in pendientes:
                    if time.perf_counter() > deadline:
                        break
                    result = mutate_and_test(mutations=item.mutations, test_command=test_command, timeout=timeout)
                    db.set_result(item.job_id, result)

                evaluados = [r for _, r in db.results if r.worker_outcome == WorkerOutcome.NORMAL]
    finally:
        with open(source_file_path, "rb") as f:
            if f.read() != contenido_original:
                print("[MUTACIÓN] Restaurando archivo fuente mutado.")
                with open(source_file_path, "wb") as fw:
                    fw.write(contenido_original)

    if not pendientes:
        print("[MUTACIÓN] No se generaron mutantes para este archivo.")
        return 1.0
    if not evaluados:
        print("[MUTACIÓN] No alcanzó a evaluarse ningún mutante dentro del presupuesto.")
        return 0.0

    killed = sum(r.test_outcome != TestOutcome.SURVIVED for r in evaluados)
    print(f"[MUTACIÓN] {killed}/{len(evaluados)} mutantes eliminados ({len(pendientes)} generados).")
    return killed / len(evaluados)

_cache_metricas = {}

# COMENTAR
def calcular_metricas(test_file_path, source_file_path=None, presupuesto_mutacion_seg=PRESUPUESTO_MUTACION_SEG):
    """
    Retorna un dict con line_coverage, branch_coverage y mutation_score, más
    las claves auxiliares missing_lines / missing_branches (no se guardan en metrics.json).
    Los resultados se cachean por contenido del archivo de tests.
    """
    if source_file_path is None:
        source_file_path = test_file_path
    source_file_path = os.path.abspath(source_file_path)

    with open(test_file_path, "rb") as f:
        clave = (hashlib.sha256(f.read()).hexdigest(), source_file_path)
    if clave in _cache_metricas:
        return dict(_cache_metricas[clave])

    line_coverage = 0.0
    branch_coverage = 0.0
    mutation_score = 0.0
    missing_lines, missing_branches = [], []

    # Ejecución aislada con coverage run, con archivo de datos propio (evita .coverage obsoletos)
    with tempfile.TemporaryDirectory() as tmp_dir:
        data_file = os.path.join(tmp_dir, ".coverage")
        cmd = [
            sys.executable, "-m", "coverage", "run",
            "--branch",
            f"--data-file={data_file}",
            f"--source={os.path.dirname(source_file_path)}",
            "-m", "pytest", test_file_path, "-q", "--disable-warnings", "-p", "no:cacheprovider"
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, stdin=subprocess.DEVNULL, timeout=TIMEOUT_PYTEST_SEG)
            returncode = res.returncode
        except subprocess.TimeoutExpired:
            print("[COBERTURA] La suite excede el timeout bajo coverage.")
            returncode = -1

        if returncode == 0:
            cov = coverage.Coverage(data_file=data_file)
            cov.load()
            line_coverage, branch_coverage, missing_lines, missing_branches = calcular_cobertura(cov, source_file_path)

    # Regla de optimización: correr mutación solo si hay cobertura mínima
    if line_coverage >= 0.50:
        try:
            mutation_score = calcular_mutation_score(
                source_file_path, test_file_path, presupuesto_seg=presupuesto_mutacion_seg
            )
        except Exception as e:
            print(f"Error en mutación: {e}")
            mutation_score = 0.0

    metricas = {
        "line_coverage": line_coverage,
        "branch_coverage": branch_coverage,
        "mutation_score": mutation_score,
        "missing_lines": missing_lines,
        "missing_branches": missing_branches,
    }
    _cache_metricas[clave] = metricas
    return dict(metricas)

def almacenar_metricas(metrics: dict, output_folder_path: str):
    metrics_file_path = os.path.join(output_folder_path, "metrics.json")
    # Solo las métricas oficiales; las claves auxiliares no se persisten
    salida = {k: metrics.get(k, 0.0) for k in METRICAS_OBJETIVO}
    try:
        with open(metrics_file_path, 'w', encoding='utf-8') as file:
            json.dump(salida, file)
        print(f"\nMétricas calculadas y almacenadas en: {metrics_file_path}")
    except Exception as e:
        print(f"Error al escribir el archivo de métricas: {e}")
        sys.exit(1)

def metricas_son_optimas(metrics: dict) -> bool:
    return all(metrics.get(k, 0) >= umbral for k, umbral in METRICAS_OBJETIVO.items())

def metric_values_are_optimal(metric_file_path):
    """
    METRICAS IDEALES PARA EL PROYECTO
    {
    "line_coverage": 0.80,
    "branch_coverage": 0.50,
    "mutation_score": 0.50}
    """
    try:
        with open(metric_file_path, 'r', encoding='utf-8') as file:
            return metricas_son_optimas(json.load(file))
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de métricas en la ruta especificada: {metric_file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        sys.exit(1)

# ----- FUNCIONES PARA ITERACIONES DE TESTING -----------------------------

# COMENTAR
def corregir_tests_con_gemini(tests, error_log, metrics, ruta_archivo, contenido_archivo):
    check_gemini_api_key()

    modulo_importable = resolver_modulo_importable(ruta_archivo)
    simbolos_validos = obtener_simbolos_exportados(contenido_archivo)
    simbolos_str = ", ".join(simbolos_validos) if simbolos_validos else "los definidos en el código"

    missing_lines = metrics.get("missing_lines") or []
    missing_branches = metrics.get("missing_branches") or []
    ramas_str = ", ".join(f"{a}->{b}" for a, b in missing_branches) if missing_branches else "ninguna / desconocido"
    seccion_errores = (
        f"Reporte de errores de pytest (los tests que fallaron ya fueron ELIMINADOS del archivo):\n{recortar_log(error_log)}"
        if error_log else "Todos los tests actuales pasan."
    )

    prompt = f"""Eres un agente experto en testing unitario con pytest.
Mejora el archivo de pruebas para que todos sus tests pasen y aumente la cobertura y el mutation score.

Identificadores declarados en el archivo bajo prueba: [{simbolos_str}]

Métricas actuales (objetivo: line >= {METRICAS_OBJETIVO['line_coverage']}, branch >= {METRICAS_OBJETIVO['branch_coverage']}, mutation >= {METRICAS_OBJETIVO['mutation_score']}):
- line_coverage: {metrics.get('line_coverage', 0.0):.2f}
- branch_coverage: {metrics.get('branch_coverage', 0.0):.2f}
- mutation_score: {metrics.get('mutation_score', 0.0):.2f}
Líneas del código fuente NO cubiertas: {missing_lines if missing_lines else "ninguna / desconocido"}
Ramas NO cubiertas (línea origen->destino; negativo = salida de función): {ramas_str}

Código fuente bajo prueba (con número de línea):
{numerar_lineas(contenido_archivo)}

Código de tests actual:
{tests}

{seccion_errores}

INSTRUCCIONES:
1. Mantén sin modificaciones los casos de prueba actuales que pasan.
2. Agrega tests nuevos que ejecuten las líneas y ramas no cubiertas indicadas arriba.
3. Para mejorar el mutation score, verifica valores exactos (assert resultado == esperado), casos límite y excepciones con pytest.raises.
4. No reintroduzcas los tests que fallaron con la misma lógica: si los rehaces, basa las expectativas en el comportamiento real del código fuente.
5. Utiliza única y estrictamente los identificadores declarados; ajusta nombres al identificador exacto si hubo errores de atributos.
6. Conserva la importación: import {modulo_importable} as target
7. Todas las pruebas deben ser funciones independientes con el prefijo "test_", sin fixtures globales, sin input() ni red.

Devuelve el archivo de tests COMPLETO, exclusivamente código Python ejecutable, sin explicaciones ni bloques markdown.
"""
    return ejecutar_llamada_gemini_robusta(prompt)

"""
MAIN PARA TAREA

si quieres testear, ejecutar:
python agent.py <ruta>/Public_Proyects/gin_rummy/base.py <ruta>/Results

e.g. python agent.py /Users/admin/t1_testing/Public_Proyects/gin_rummy/base.py /Users/admin/t1_testing/Results

"""

def _puntaje(metrics: dict) -> float:
    return sum(metrics.get(k, 0.0) for k in METRICAS_OBJETIVO)

def main(ruta_archivo, output_folder):
    t_inicio_total = time.perf_counter()

    check_gemini_api_key()

    print(f"Iniciando Agente de Testing Automático...")
    print(f"Ruta del archivo: {ruta_archivo}")
    print(f"Directorio de salida: {output_folder}")
    os.makedirs(output_folder, exist_ok=True)

    # =====================================================================
    # 1. Generación inicial de tests
    # =====================================================================
    contenido_archivo = read_file_content(ruta_archivo)

    t_inicio_gen = time.perf_counter()
    try:
        tests_generados = generar_tests(contenido_archivo, ruta_archivo)
    except ErrorGemini as e:
        print(f"[ERROR AGENTE] {e}")
        if e.sobrecarga:
            with open(os.path.join(output_folder, "metrics.json"), "w", encoding="utf-8") as f:
                json.dump({"error": "High demand"}, f, indent=4)
            sys.exit(0)
        sys.exit(1)
    print(f"Tiempo creación tests (inicial): {time.perf_counter() - t_inicio_gen:.2f} s")

    almacenar_tests(tests_generados, ruta_archivo, output_folder)
    test_file_path = resolver_test_file_path(ruta_archivo, output_folder)

    # =====================================================================
    # 2. Ciclo evaluar -> (podar) -> refinar, con control de tiempo (SLA 4 minutos).
    #    Se conserva siempre la MEJOR versión de la suite, ya que un
    #    refinamiento del LLM puede empeorar una suite que ya funcionaba.
    # =====================================================================
    max_iterations = 2  # Número de refinamientos con Gemini
    mejor_cuerpo, mejor_metricas = None, None

    for iteration in range(max_iterations + 1):
        pasan_tests, error_log = ejecutar_pytest_con_captura(test_file_path)

        # Si fallan, intentamos primero una poda rápida local de los rotos
        if not pasan_tests:
            print(f"[PODA] Depurando tests fallidos localmente mediante AST...")
            pasan_tests = podar_suite_con_ast(test_file_path)

        if pasan_tests:
            restante = LIMITE_ITERACIONES_SEG - (time.perf_counter() - t_inicio_total)
            metrics = calcular_metricas(
                test_file_path, ruta_archivo,
                presupuesto_mutacion_seg=max(10.0, min(PRESUPUESTO_MUTACION_SEG, restante)),
            )
            almacenar_metricas(metrics, output_folder)
            if mejor_metricas is None or _puntaje(metrics) > _puntaje(mejor_metricas):
                mejor_metricas = metrics
                mejor_cuerpo = separar_preambulo(read_file_content(test_file_path))[1]
            if metricas_son_optimas(metrics):
                print("[EXITO] Las métricas cumplen con los valores ideales.")
                break
        else:
            print(f"[FALLO] Persisten errores en iteración {iteration + 1}.")
            metrics = {"line_coverage": 0.0, "branch_coverage": 0.0, "mutation_score": 0.0}
            if mejor_metricas is None:
                almacenar_metricas(metrics, output_folder)

        if iteration == max_iterations:
            break
        tiempo_transcurrido = time.perf_counter() - t_inicio_total
        if tiempo_transcurrido > LIMITE_ITERACIONES_SEG:
            print(f"[CONTROL TIEMPO] ({tiempo_transcurrido:.1f}s). Abortando bucle de corrección.")
            break

        print("Consultando refinamiento a Gemini...")
        t_inicio_iter = time.perf_counter()
        try:
            tests_generados = corregir_tests_con_gemini(
                separar_preambulo(read_file_content(test_file_path))[1],
                error_log, metrics, ruta_archivo, contenido_archivo
            )
        except ErrorGemini as e:
            # No se descarta el trabajo previo: se conserva la mejor suite obtenida
            print(f"[ERROR AGENTE] Refinamiento abortado: {e}")
            break
        print(f"Tiempo refinamiento (iteración {iteration + 1}): {time.perf_counter() - t_inicio_iter:.2f} s")
        almacenar_tests(tests_generados, ruta_archivo, output_folder)

    # =====================================================================
    # 3. Resultado final: se deja en disco la mejor suite y sus métricas
    # =====================================================================
    if mejor_cuerpo is not None:
        almacenar_tests(mejor_cuerpo, ruta_archivo, output_folder)
        almacenar_metricas(mejor_metricas, output_folder)
        print(f"[FINAL] Suite 100% operativa. Métricas: { {k: mejor_metricas[k] for k in METRICAS_OBJETIVO} }")
    else:
        almacenar_metricas({}, output_folder)
        print("[ADVERTENCIA] No quedaron tests ejecutables tras el saneamiento.")

    print(f"Tiempo total ejecución archivo: {time.perf_counter() - t_inicio_total:.2f} s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente basado en LLM para generación iterativa de tests.")

    parser.add_argument("ruta_archivo", type=str, help="Ruta relativa al archivo de código fuente (ej. Proyectos_Publicos/bridge/base.py)")
    parser.add_argument("output_folder", type=str, help="Directorio general donde se guardarán los resultados (ej. Resultados)")

    args = parser.parse_args()

    main(args.ruta_archivo, args.output_folder)
