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
import pytest # para testing
import coverage # para coverage
# cosmic-ray para mutation testing!!!
import cosmic_ray.commands
from cosmic_ray.config import ConfigDict
from cosmic_ray.modules import find_modules, filter_paths
from cosmic_ray.tools.survival_rate import survival_rate
from cosmic_ray.work_db import WorkDB, use_db

# COMENTAR
import subprocess
import time
import ast
import textwrap
import re

load_dotenv()

# ----- FUNCIONES AUXILIARES -----------------------------

def resolver_test_file_path(ruta_archivo, output_folder_path):
    nombre_archivo = os.path.basename(os.path.normpath(ruta_archivo))
    nombre_base = os.path.splitext(nombre_archivo)[0]
    return os.path.join(output_folder_path, f"test_{nombre_base}.py")

# COMENTAR
def resolver_modulo_importable(ruta_archivo):
    """
      Calcula la ruta de importación (dotted path) de ruta_archivo relativa a la
      raíz del proyecto (donde vive agent.py), para indicarle al LLM exactamente
      cómo debe importar el archivo bajo prueba
      (ej. Public_Proyects/fuzzywuzzy/fuzz.py -> Public_Proyects.fuzzywuzzy.fuzz).
      """

    project_root = os.path.dirname(os.path.abspath(__file__))
    public_projects_root = os.path.join(project_root, "Public_Proyects")
    abs_path = os.path.abspath(ruta_archivo)

    # Si está dentro de Public_Proyects, el módulo base es relativo a Public_Proyects
    if os.path.commonpath([abs_path, public_projects_root]) == public_projects_root:
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
        return list(dict.fromkeys(simbolos))
    except Exception:
        return []

# COMENTAR
def limpiar_fences_markdown(texto: str) -> str:
    texto = texto.strip()
    if texto.startswith("```"):
        lineas = texto.splitlines()
        if lineas[0].startswith("```"):
            lineas = lineas[1:]
        if lineas and lineas[-1].startswith("```"):
            lineas = lineas[:-1]
        texto = "\n".join(lineas).strip()
    return texto

# COMENTAR
def ejecutar_pytest_con_captura(test_file_path):
    """
    Ejecuta pytest en subproceso para aislar memoria y capturar el mensaje de error.
    Retorna: (compilo_y_paso: bool, error_message: str)
    """
    cmd = [sys.executable, "-m", "pytest", test_file_path, "-q", "--disable-warnings"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    pasan_todos = (res.returncode == 0)
    error_log = (res.stdout + "\n" + res.stderr) if not pasan_todos else ""
    return pasan_todos, error_log

def ensure_project_import_paths(test_file_path, source_file_path=None):
    """
    Agrega al sys.path la raíz del proyecto y Public_Proyects, y además el
    directorio propio del paquete bajo prueba (ej. Public_Proyects/gin_rummy).
    Esto último es necesario porque varios de estos proyectos usan imports
    "planos" internos (ej. "import utils" en vez de "from . import utils"),
    que solo resuelven si el propio directorio del paquete está en sys.path.
    """
    test_dir = os.path.dirname(os.path.abspath(test_file_path))
    project_root = os.path.abspath(os.path.join(test_dir, os.pardir))
    public_projects_root = os.path.join(project_root, "Public_Proyects")

    candidates = [project_root, public_projects_root]
    if source_file_path is not None:
        candidates.append(os.path.dirname(os.path.abspath(source_file_path)))

    for candidate in candidates:
        if os.path.isdir(candidate) and candidate not in sys.path:
            sys.path.insert(0, candidate)

def check_gemini_api_key():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: No se encontró la variable GEMINI_API_KEY en el entorno.")
        sys.exit(1)
    return api_key

# COMENTAR
def ejecutar_llamada_gemini_robusta(
    prompt: str, 
    output_folder: str, 
    max_reintentos: int = 4, 
    max_espera_total_seg: int = 60
) -> str:
    """
    Ejecuta llamadas al modelo de Gemini con reintentos automáticos ante 503/504.
    Garantiza que el tiempo total acumulado en esperas de reintento NUNCA supere
    el presupuesto asignado (por defecto, 60 segundos).
    """
    client = genai.Client()
    tiempo_espera_acumulado = 0

    for intento in range(max_reintentos):
        try:
            chat = client.chats.create(model="gemini-3.1-flash-lite")
            response = chat.send_message(prompt)
            return limpiar_fences_markdown(response.text)
        except Exception as e:
            error_str = str(e)
            es_sobrecarga = any(
                k in error_str 
                for k in ["503", "504", "High demand", "Time budget exceeded", "ResourceExhausted", "UNAVAILABLE"]
            )
            
            if es_sobrecarga:
                print(f"[API ERROR] Sobrecarga detectada (intento {intento + 1}/{max_reintentos}): {error_str}")
                
                # Calcular el tiempo de espera sugerido para esta ronda (15s, 20s, 25s...)
                espera_sugerida = 15 + (intento * 5)
                tiempo_restante_presupuesto = max_espera_total_seg - tiempo_espera_acumulado

                # Si aún quedan reintentos y queda tiempo en el presupuesto de 60s
                if intento < max_reintentos - 1 and tiempo_restante_presupuesto > 5:
                    tiempo_a_esperar = min(espera_sugerida, tiempo_restante_presupuesto)
                    print(f" -> Reintentando en {tiempo_a_esperar}s (espera acumulada: {tiempo_espera_acumulado + tiempo_a_esperar}s / {max_espera_total_seg}s)...")
                    time.sleep(tiempo_a_esperar)
                    tiempo_espera_acumulado += tiempo_a_esperar
                else:
                    # Se agotaron los reintentos o el presupuesto de 60 segundos
                    print(f"[ERROR AGENTE] Se agotó el presupuesto de reintentos ({tiempo_espera_acumulado}s acumulados).")
                    metric_file_path = os.path.join(output_folder, "metrics.json")
                    with open(metric_file_path, "w", encoding="utf-8") as f:
                        json.dump({"error": "High demand"}, f, indent=4)
                    sys.exit(0)
            else:
                print(f"Error fatal no recuperable en Gemini: {e}")
                sys.exit(1)
                
    return ""

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
def generar_tests(contenido_archivo, ruta_archivo, output_folder):
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

Devuelve exclusivamente código Python ejecutable, sin explicaciones ni bloques markdown.
"""
    
    # Agrega esto en generar_tests justo antes del return:
    print(f"\n--- VERIFICACIÓN DE SÍMBOLOS EXTRAÍDOS ---")
    print(f"Archivo: {ruta_archivo}")
    print(f"Símbolos reales detectados: {simbolos_validos}")
    print(f"------------------------------------------\n")
    
    return ejecutar_llamada_gemini_robusta(prompt, output_folder)

# COMENTAR
def almacenar_tests(tests_generados, ruta_archivo, output_folder_path):
    os.makedirs(output_folder_path, exist_ok=True)
    output_file_path = resolver_test_file_path(ruta_archivo, output_folder_path)

    project_root = os.path.dirname(os.path.abspath(__file__))
    public_projects_root = os.path.join(project_root, "Public_Proyects")
    source_file_abs = os.path.abspath(ruta_archivo)
    source_dir = os.path.dirname(source_file_abs)
    
    # Nombre del paquete (ej: 'tree', 'blackjack', 'mahjong')
    rel_path = os.path.relpath(source_file_abs, public_projects_root)
    pkg_name = rel_path.split(os.sep)[0]

    # Orden crítico de sys.path:
    # 1. public_projects_root para resolver 'import tree.base' viendo 'tree' como carpeta/paquete
    # 2. project_root
    # 3. source_dir al final para resolver imports planos tipo 'import utils' sin pisar el nombre del paquete
    setup_code = textwrap.dedent(f'''\
import sys
import os

for p in [{public_projects_root!r}, {project_root!r}, {source_dir!r}]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Evitar colisión si existe un archivo con el mismo nombre que el directorio (ej: tree/tree.py)
import types
if {pkg_name!r} not in sys.modules or not hasattr(sys.modules[{pkg_name!r}], "__path__"):
    pkg_path = os.path.join({public_projects_root!r}, {pkg_name!r})
    if os.path.isdir(pkg_path):
        pkg_mod = types.ModuleType({pkg_name!r})
        pkg_mod.__path__ = [pkg_path]
        pkg_mod.__file__ = os.path.join(pkg_path, "__init__.py")
        sys.modules[{pkg_name!r}] = pkg_mod
''')

    with open(output_file_path, 'w', encoding='utf-8') as file:
        file.write(setup_code + "\n" + tests_generados.lstrip())
    print(f"Tests generados y almacenados en: {output_file_path}")

# COMENTAR
def podar_suite_con_ast(test_file_path: str, max_rondas: int = 5) -> bool:
    """
    Elimina físicamente del archivo de tests cualquier función test_ o línea global 
    que provoque fallos en pytest (ImportError, AttributeError, AssertionError).
    Retorna True si la suite restante pasa al 100%.
    """
    for _ in range(max_rondas):
        pasan, error_log = ejecutar_pytest_con_captura(test_file_path)
        if pasan:
            return True

        nombre_archivo = os.path.basename(test_file_path)
        modificado = False

        # 1. Errores a nivel de módulo (líneas sueltas que impiden cargar la suite)
        match_linea = re.search(rf"{re.escape(nombre_archivo)}:(\d+):", error_log)
        if match_linea and ("ImportError" in error_log or "AttributeError" in error_log or "SyntaxError" in error_log):
            idx_linea = int(match_linea.group(1)) - 1
            try:
                with open(test_file_path, "r", encoding="utf-8") as f:
                    lineas = f.readlines()
                if 0 <= idx_linea < len(lineas) and not lineas[idx_linea].strip().startswith("#"):
                    lineas[idx_linea] = f"# [PODADO] {lineas[idx_linea]}"
                    with open(test_file_path, "w", encoding="utf-8") as f:
                        f.writelines(lineas)
                    modificado = True
                    continue
            except Exception:
                pass

        # 2. Funciones test_ específicas que fallaron
        tests_a_borrar = set(re.findall(r"(?:FAILED|ERROR)\s+.*?::(test_[a-zA-Z0-9_]+)", error_log))
        if tests_a_borrar:
            try:
                with open(test_file_path, "r", encoding="utf-8") as f:
                    contenido = f.read()

                arbol = ast.parse(contenido)
                arbol.body = [
                    nodo for nodo in arbol.body
                    if not (isinstance(nodo, (ast.FunctionDef, ast.AsyncFunctionDef)) and nodo.name in tests_a_borrar)
                ]

                with open(test_file_path, "w", encoding="utf-8") as f:
                    f.write(ast.unparse(arbol))
                modificado = True
            except Exception:
                pass

        if not modificado:
            break

    pasan_final, _ = ejecutar_pytest_con_captura(test_file_path)
    return pasan_final

# -- -- FUNCIONES PRINCIPALES 2 -----------------------------

def calcular_cobertura(cov, source_file_path):
    """
    Extrae line_coverage y branch_coverage (0.0-1.0) del archivo fuente a partir
    de un objeto coverage.Coverage ya detenido, usando el reporte JSON de coverage.py
    (que expone porcentajes de statements y de branches por separado).
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
        return line_coverage, branch_coverage
    except coverage.exceptions.NoDataError:
        return 0.0, 0.0
    finally:
        if json_report_path and os.path.exists(json_report_path):
            os.remove(json_report_path)

def calcular_mutation_score(source_file_path, test_file_path, timeout=30.0):
    """
    Ejecuta mutation testing con la librería cosmic-ray sobre source_file_path,
    utilizando los tests de test_file_path. Usa directamente cosmic_ray.commands
    (las mismas funciones que invoca su CLI internamente), sin depender de
    procesos externos. Devuelve la proporción de mutantes eliminados (0.0-1.0).
    """
    test_command = f"{sys.executable} -m pytest {test_file_path} -q --disable-warnings"

    config = ConfigDict({
        "module-path": source_file_path,
        "timeout": timeout,
        "excluded-modules": [],
        "test-command": test_command,
        "distributor": {"name": "local"},
    })

    modules = find_modules([Path(config["module-path"])])
    modules = filter_paths(modules, config.get("excluded-modules", ()))

    with tempfile.TemporaryDirectory() as tmp_dir:
        session_path = os.path.join(tmp_dir, "session.sqlite")

        with use_db(session_path) as db:
            cosmic_ray.commands.init(modules, db, config.operators_config)

        with use_db(session_path, mode=WorkDB.Mode.open) as db:
            cosmic_ray.commands.execute(db, config)
            rate = survival_rate(db)

    return max(0.0, 1.0 - (rate / 100.0))

# COMENTAR
def calcular_metricas(test_file_path, source_file_path=None):
    if source_file_path is None:
        source_file_path = test_file_path
    source_file_path = os.path.abspath(source_file_path)

    # Ejecución aislada con coverage run
    cmd = [
        sys.executable, "-m", "coverage", "run",
        "--branch",
        f"--source={os.path.dirname(source_file_path)}",
        "-m", "pytest", test_file_path, "-q", "--disable-warnings"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)

    line_coverage = 0.0
    branch_coverage = 0.0
    mutation_score = 0.0

    if res.returncode == 0:
        cov = coverage.Coverage()
        cov.load()
        line_coverage, branch_coverage = calcular_cobertura(cov, source_file_path)

        # Regla de optimización: correr mutación solo si hay cobertura mínima y tiempo suficiente
        if line_coverage >= 0.50:
            try:
                mutation_score = calcular_mutation_score(source_file_path, test_file_path, timeout=10.0)
            except Exception as e:
                print(f"Error en mutación: {e}")
                mutation_score = 0.0

    return {
        "line_coverage": line_coverage,
        "branch_coverage": branch_coverage,
        "mutation_score": mutation_score
    }

def almacenar_metricas(metrics: dict, output_folder_path: str):
    metrics_file_path = os.path.join(output_folder_path, "metrics.json")
    try:
        with open(metrics_file_path, 'w', encoding='utf-8') as file:
            json.dump(metrics, file)
        print(f"\nMétricas calculadas y almacenadas en: {metrics_file_path}")
    except Exception as e:
        print(f"Error al escribir el archivo de métricas: {e}")
        sys.exit(1)

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
            metrics = json.load(file)
            line_coverage = metrics.get("line_coverage", 0)
            branch_coverage = metrics.get("branch_coverage", 0)
            mutation_score = metrics.get("mutation_score", 0)

            if line_coverage >= 0.80 and branch_coverage >= 0.50 and mutation_score >= 0.50:
                return True
            else:
                return False
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de métricas en la ruta especificada: {metric_file_path}")
        sys.exit(1)
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        sys.exit(1)

# ----- FUNCIONES PARA ITERACIONES DE TESTING -----------------------------

# COMENTAR
def corregir_tests_con_gemini(tests, error_log, metrics, ruta_archivo, contenido_archivo, output_folder):
    check_gemini_api_key()

    modulo_importable = resolver_modulo_importable(ruta_archivo)
    simbolos_validos = obtener_simbolos_exportados(contenido_archivo)
    simbolos_str = ", ".join(simbolos_validos) if simbolos_validos else "los definidos en el código"

    prompt = f"""Eres un agente experto en depuración de pruebas con pytest.
Corrige el archivo de pruebas para que todos los tests que permanezcan se ejecuten exitosamente.

Identificadores declarados en el archivo bajo prueba: [{simbolos_str}]

Código fuente bajo prueba:
{contenido_archivo}

Código de tests actual:
{tests}

Reporte de errores de pytest:
{error_log[:3000]}

INSTRUCCIONES DE CORRECCIÓN GENERALES:
1. Revisa el reporte de errores. Si una función o prueba falla por identificadores no encontrados o problemas de compatibilidad de tipos/argumentos, ajusta el nombre al identificador exacto declarado en el archivo.
2. Si un bloque de prueba, fixture o función auxiliar no puede corregirse limpiamente, ELIMÍNALO por completo del archivo para preservar únicamente las pruebas exitosas.
3. Mantén sin modificaciones los casos de prueba que hayan pasado.
4. Conserva la importación: import {modulo_importable} as target
5. Todas las pruebas deben ser funciones independientes con el prefijo "test_".

Devuelve exclusivamente código Python ejecutable, sin explicaciones ni bloques markdown.
"""
    return ejecutar_llamada_gemini_robusta(prompt, output_folder)

"""
MAIN PARA TAREA

si quieres testear, ejecutar:
python agent.py <ruta>/Public_Proyects/gin_rummy/base.py <ruta>/Results

e.g. python agent.py /Users/admin/t1_testing/Public_Proyects/gin_rummy/base.py /Users/admin/t1_testing/Results

"""

def main(ruta_archivo, output_folder):
    t_inicio_total = time.perf_counter()

    check_gemini_api_key()
        
    print(f"Iniciando Agente de Testing Automático...")
    print(f"Ruta del archivo: {ruta_archivo}")
    print(f"Directorio de salida: {output_folder}")

    # =====================================================================
    # 1. Generación inicial de tests
    # =====================================================================
    contenido_archivo = read_file_content(ruta_archivo)
    
    t_inicio_gen = time.perf_counter()
    # Se pasa output_folder para registrar el error 503/504 si la llamada inicial se agota
    tests_generados = generar_tests(contenido_archivo, ruta_archivo, output_folder)
    print(f"Tiempo creación tests (inicial): {time.perf_counter() - t_inicio_gen:.2f} s")
    
    almacenar_tests(tests_generados, ruta_archivo, output_folder)

    # 2. Calcular métricas iniciales
    test_file_path = resolver_test_file_path(ruta_archivo, output_folder)
    metrics = calcular_metricas(test_file_path, ruta_archivo)
    almacenar_metricas(metrics, output_folder)

    # =====================================================================
    # 3. Iteraciones de corrección con control de tiempo (SLA 4 minutos)
    # =====================================================================
    metric_file_path = os.path.join(output_folder, "metrics.json")
    max_iterations = 2  # Con poda mecánica, 2 iteraciones son suficientes y ahorran tiempo

    for iteration in range(max_iterations):
        tiempo_transcurrido = time.perf_counter() - t_inicio_total
        if tiempo_transcurrido > 200:
            print(f"[CONTROL TIEMPO] ({tiempo_transcurrido:.1f}s). Abortando bucle de corrección.")
            break

        pasan_tests, error_log = ejecutar_pytest_con_captura(test_file_path)
        
        # Si fallan, intentamos primero una poda rápida local de los rotos
        if not pasan_tests:
            print(f"[PODA] Depurando tests fallidos localmente mediante AST...")
            pasan_tests = podar_suite_con_ast(test_file_path)

        if pasan_tests:
            metrics = calcular_metricas(test_file_path, ruta_archivo)
            almacenar_metricas(metrics, output_folder)
            if metric_values_are_optimal(metric_file_path):
                print("[EXITO] Las métricas cumplen con los valores ideales.")
                break
        else:
            print(f"[FALLO] Persisten errores en iteración {iteration + 1}. Consultando refinamiento...")
            metrics = {"line_coverage": 0.0, "branch_coverage": 0.0, "mutation_score": 0.0}
            almacenar_metricas(metrics, output_folder)

        t_inicio_iter = time.perf_counter()
        tests_generados = corregir_tests_con_gemini(
            read_file_content(test_file_path), error_log, metrics, ruta_archivo, contenido_archivo, output_folder
        )
        print(f"Tiempo refinamiento (iteración {iteration + 1}): {time.perf_counter() - t_inicio_iter:.2f} s")
        almacenar_tests(tests_generados, ruta_archivo, output_folder)

    # =====================================================================
    # 4. Evaluación y saneamiento final garantizado
    # =====================================================================
    pasan_final, _ = ejecutar_pytest_con_captura(test_file_path)
    if not pasan_final:
        print("[SANEAMIENTO FINAL] Aplicando poda definitiva de tests insalvables...")
        podar_suite_con_ast(test_file_path)

    pasan_final, _ = ejecutar_pytest_con_captura(test_file_path)
    if pasan_final:
        metricas_finales = calcular_metricas(test_file_path, ruta_archivo)
        almacenar_metricas(metricas_finales, output_folder)
        print(f"[FINAL] Suite 100% operativa. Métricas: {metricas_finales}")
    else:
        print("[ADVERTENCIA] No quedaron tests ejecutables tras el saneamiento.")

    print(f"Tiempo total ejecución archivo: {time.perf_counter() - t_inicio_total:.2f} s")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente basado en LLM para generación iterativa de tests.")

    parser.add_argument("ruta_archivo", type=str, help="Ruta relativa al archivo de código fuente (ej. Proyectos_Publicos/bridge/base.py)")
    parser.add_argument("output_folder", type=str, help="Directorio general donde se guardarán los resultados (ej. Resultados)")
    
    args = parser.parse_args()
    
    main(args.ruta_archivo, args.output_folder)