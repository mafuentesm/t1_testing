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

load_dotenv()

# ----- FUNCIONES AUXILIARES -----------------------------

def resolver_test_file_path(ruta_archivo, output_folder_path):
    nombre_archivo = os.path.basename(os.path.normpath(ruta_archivo))
    nombre_base = os.path.splitext(nombre_archivo)[0]
    return os.path.join(output_folder_path, f"test_{nombre_base}.py")

def resolver_modulo_importable(ruta_archivo):
    """
    Calcula la ruta de importación (dotted path) de ruta_archivo relativa a la
    raíz del proyecto (donde vive agent.py), para indicarle al LLM exactamente
    cómo debe importar el archivo bajo prueba
    (ej. Public_Proyects/fuzzywuzzy/fuzz.py -> Public_Proyects.fuzzywuzzy.fuzz).
    """
    project_root = os.path.dirname(os.path.abspath(__file__))
    ruta_relativa = os.path.relpath(os.path.abspath(ruta_archivo), project_root)
    sin_extension = os.path.splitext(ruta_relativa)[0]
    return sin_extension.replace(os.sep, ".")

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

def generar_tests(contenido_archivo, ruta_archivo):
    api_key = check_gemini_api_key()
    client = genai.Client()

    modulo_importable = resolver_modulo_importable(ruta_archivo)

    prompt = f"""
    Eres un agente experto en testing automático.
    A partir del siguiente contenido de código fuente, genera tests unitarios en Python utilizando pytest.

    Contenido del archivo:
    {contenido_archivo}

    El archivo fuente DEBE importarse en los tests exactamente así:
    from {modulo_importable} import <NombreDeClaseOFuncion>
    (ajusta <NombreDeClaseOFuncion> según lo que necesites usar del archivo, pero no cambies "{modulo_importable}").

    Reglas de import OBLIGATORIAS:
    - NO importes usando solo el nombre del archivo (ej. "from fuzz import ratio" es INCORRECTO).
    - NO inventes ni adivines otra ruta de módulo; usa siempre "{modulo_importable}" tal cual.
    - Ignora cualquier import relativo o interno que use el propio archivo fuente (ej. "import utils" o "from . import algo"): eso es asunto interno del archivo, no lo repliques en el test.

    Devuelve solo el código de los tests generados sin explicaciones adicionales.
    MUY IMPORTANTE: ASEGURATE DE QUE EL CÓDIGO NO COMIENCE CON COMILLAS TRIPLES NI COMENTARIOS, SOLO DEVUELVE EL CÓDIGO DE LOS TESTS.
    """

    try:
        chat = client.chats.create(model="gemini-3.1-flash-lite")
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        print(f"Error al comunicarse con la API de Gemini: {e}")
        sys.exit(1)

def almacenar_tests(tests_generados, ruta_archivo, output_folder_path): # debe tener el nombre de la clase dentro del archivo de ruta_archivo
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    output_file_path = resolver_test_file_path(ruta_archivo, output_folder_path)

    project_root = os.path.dirname(os.path.abspath(__file__))
    public_projects_root = os.path.join(project_root, "Public_Proyects")
    ruta_absoluta = os.path.abspath(ruta_archivo)
    paquete_relativo = None
    if os.path.commonpath([ruta_absoluta, public_projects_root]) == public_projects_root:
        paquete_relativo = os.path.dirname(os.path.relpath(ruta_absoluta, public_projects_root)) or None

    setup_code = f'''
import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PUBLIC_PROJECTS_ROOT = os.path.join(PROJECT_ROOT, "Public_Proyects")

# Directorio propio del paquete bajo prueba (ej. Public_Proyects/gin_rummy).
# Necesario porque varios de estos proyectos usan imports "planos" internos
# (ej. "import utils" en vez de "from . import utils").
PAQUETE_RELATIVO = {paquete_relativo!r}

extra_paths = [PROJECT_ROOT, PUBLIC_PROJECTS_ROOT]
if PAQUETE_RELATIVO:
    extra_paths.append(os.path.join(PUBLIC_PROJECTS_ROOT, PAQUETE_RELATIVO))

for path in extra_paths:
    if os.path.isdir(path) and path not in sys.path:
        sys.path.insert(0, path)

'''

    try:
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(setup_code + tests_generados.lstrip())
        print(f"Tests generados y almacenados en: {output_file_path}")
    except Exception as e:
        print(f"Error al escribir el archivo de tests: {e}")
        sys.exit(1)

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

def calcular_metricas(test_file_path, source_file_path=None):
    """
    Función para calcular métricas de cobertura y mutación.
    Devuelve un diccionario con las métricas calculadas.
    """
    if source_file_path is None:
        source_file_path = test_file_path

    source_file_path = os.path.abspath(source_file_path)
    ensure_project_import_paths(test_file_path, source_file_path)
    cov = coverage.Coverage(branch=True)
    cov.start()

    test_exit_code = pytest.main([test_file_path, '--disable-warnings', '-q'])

    cov.stop()
    cov.save()

    line_coverage = 0.0
    branch_coverage = 0.0
    mutation_score = 0.0

    if test_exit_code != 5:
        line_coverage, branch_coverage = calcular_cobertura(cov, source_file_path)

        try:
            mutation_score = calcular_mutation_score(source_file_path, test_file_path)
        except Exception as e:
            print(f"Error al calcular el mutation score: {e}")
            mutation_score = 0.0

    metrics = {
        "line_coverage": line_coverage,
        "branch_coverage": branch_coverage,
        "mutation_score": mutation_score
    }

    return metrics

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

def corregir_tests_con_gemini(tests, metrics, ruta_archivo):
    """
    Función para corregir los tests generados utilizando la API de Gemini.
    """
    api_key = check_gemini_api_key()
    client = genai.Client()

    modulo_importable = resolver_modulo_importable(ruta_archivo)

    prompt = f"""
    Eres un agente experto en testing automático.
    A partir de los tests generados previamente, realiza correcciones y mejoras para optimizar la cobertura y el score de mutación.
    Actualmente, las métricas obtenidas son: {metrics}.

    Los tests son los siguientes:
    {tests}

    El archivo fuente bajo prueba DEBE importarse en los tests exactamente así:
    from {modulo_importable} import <NombreDeClaseOFuncion>
    (ajusta <NombreDeClaseOFuncion> según lo que necesites usar del archivo, pero no cambies "{modulo_importable}").

    Reglas de import OBLIGATORIAS:
    - NO importes usando solo el nombre del archivo (ej. "from fuzz import ratio" es INCORRECTO).
    - NO inventes ni adivines otra ruta de módulo; usa siempre "{modulo_importable}" tal cual.
    - Ignora cualquier import relativo o interno que use el propio archivo fuente (ej. "import utils" o "from . import algo"): eso es asunto interno del archivo, no lo repliques en el test.

    Devuelve solo el código de los tests generados sin explicaciones adicionales.
    MUY IMPORTANTE: ASEGURATE DE QUE EL CÓDIGO NO COMIENCE CON COMILLAS TRIPLES NI COMENTARIOS, SOLO DEVUELVE EL CÓDIGO DE LOS TESTS.
    """

    try:
        chat = client.chats.create(model="gemini-3.1-flash-lite")
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        print(f"Error al comunicarse con la API de Gemini: {e}")
        sys.exit(1)

"""
MAIN PARA TAREA

si quieres testear, ejecutar:
python agent.py <ruta>/Public_Proyects/gin_rummy/base.py <ruta>/Results

e.g. python agent.py /Users/admin/t1_testing/Public_Proyects/gin_rummy/base.py /Users/admin/t1_testing/Results

"""

def main(ruta_archivo, output_folder):

    api_key = check_gemini_api_key()
        
    print(f"Iniciando Agente de Testing Automático...")
    print(f"Ruta del archivo: {ruta_archivo}")
    print(f"Directorio de salida: {output_folder}")

    client = genai.Client()

    """
    # -------- EJEMPLO DE USO DE LA API (Ejemplo Genérico) -----------------

    print("\n[Ejemplo] Consultando a Gemini Flash Lite 3.1...")
    try:
        prompt_ejemplo = f"Analiza la siguiente ruta de archivo para pruebas: {ruta_archivo}. Responde brevemente con un saludo y el rol que cumplirás como agente de testing."
        
        chat = client.chats.create(model="gemini-3.1-flash-lite")
        response = chat.send_message(prompt_ejemplo)
        
        print(f"Respuesta de prueba del modelo:\n--> {response.text}\n")
    except Exception as e:
        print(f"Error al comunicarse con la API de Gemini: {e}")
        sys.exit(1)
    """

    # =====================================================================
    # Tarea
    # =====================================================================

    contenido_archivo = read_file_content(ruta_archivo) # 1. Leer el contenido del archivo obtenido por ruta_archivo
    tests_generados = generar_tests(contenido_archivo, ruta_archivo) # 1.1 Pedir a la IA (gemini) que desarrolle tests a partir de ese contenido
    almacenar_tests(tests_generados, ruta_archivo, output_folder) # 1.2. Almacenar tests unitarios en la ruta de output_folder en un único archivo

    # 2 Calcular metricas de cobertura y mutación de los tests generados
    test_file_path = resolver_test_file_path(ruta_archivo, output_folder)
    metrics = calcular_metricas(test_file_path, ruta_archivo)
    almacenar_metricas(metrics, output_folder) # 2.1 Guardar métricas en un archivo de salida (ej. metrics.json) dentro de output_folder

    # 3. Evaluar si las métricas cumplen con los valores ideales (line_coverage >= 0.80, branch_coverage >= 0.50, mutation_score >= 0.50)
    metric_file_path = os.path.join(output_folder, "metrics.json")
    max_iterations = 3
    success = False

    for iteration in range(max_iterations):
        success = metric_values_are_optimal(metric_file_path)
        if success:
            print("[EXITO] Las métricas cumplen con los valores ideales.")
            break

        print(f"Iteración {iteration + 1}/{max_iterations}: las métricas no cumplen con los valores ideales. Generando nuevos tests...")
        tests_generados = corregir_tests_con_gemini(tests_generados, metrics, ruta_archivo) # 3.1 Pedir a la IA (gemini) que corrija los tests generados previamente
        almacenar_tests(tests_generados, ruta_archivo, output_folder) # 3.2. Almacenar tests corregidos en la ruta de output_folder en un único archivo
        metrics = calcular_metricas(test_file_path, ruta_archivo) # 3.3 Calcular métricas
        almacenar_metricas(metrics, output_folder) # 3.4 Guardar métricas en un archivo de salida (ej. metrics.json) dentro de output_folder
    else:
        success = metric_values_are_optimal(metric_file_path)

    if not success:
        print("[ADVERTENCIA] Se alcanzó el máximo de iteraciones sin cumplir la meta ideal. Se conserva la última versión generada.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente basado en LLM para generación iterativa de tests.")

    parser.add_argument("ruta_archivo", type=str, help="Ruta relativa al archivo de código fuente (ej. Proyectos_Publicos/bridge/base.py)")
    parser.add_argument("output_folder", type=str, help="Directorio general donde se guardarán los resultados (ej. Resultados)")
    
    args = parser.parse_args()
    
    main(args.ruta_archivo, args.output_folder)