import argparse
import os
import sys
from dotenv import load_dotenv
from google import genai # Para uso de API de Gemini
# Para testing
import pytest
import coverage
import cosmic_ray

load_dotenv()

# -- -- FUNCIONES AUXILIARES -----------------------------

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

def generar_tests(contenido_archivo):
    api_key = check_gemini_api_key()
    client = genai.Client()

    prompt = f"""
    Eres un agente experto en testing automático. 
    A partir del siguiente contenido de código fuente, genera tests unitarios en Python utilizando pytest.

    Contenido del archivo:
    {contenido_archivo}
    
    Devuelve solo el código de los tests generados sin explicaciones adicionales.
    """

    try:
        chat = client.chats.create(model="gemini-3.1-flash-lite")
        response = chat.send_message(prompt)
        return response.text
    except Exception as e:
        print(f"Error al comunicarse con la API de Gemini: {e}")
        sys.exit(1)

def almacenar_tests(tests_generados, output_folder_path):
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    class_name = os.path.basename(os.path.normpath(output_folder_path))
    output_file_path = os.path.join(output_folder_path, f"test_{class_name}.py")
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(tests_generados)
        print(f"Tests generados y almacenados en: {output_file_path}")
    except Exception as e:
        print(f"Error al escribir el archivo de tests: {e}")
        sys.exit(1)

# -- -- FUNCIONES PRINCIPALES 2 -----------------------------

def calcular_metricas(test_file_path):
    """
    Función para calcular métricas de cobertura y mutación.
    Devuelve un diccionario con las métricas calculadas.
    """
    # Calcular cobertura de código
    cov = coverage.Coverage()
    cov.start()
    
    # Ejecutar tests (estan en test_file_path) para medir cobertura
    pytest.main([test_file_path, '--maxfail=1', '--disable-warnings', '-q'])
    
    cov.stop()
    cov.save()
    
    line_coverage = cov.report() / 100.0  # Convertir a valor entre 0 y 1
    branch_coverage = cov.branch_coverage() / 100.0 if hasattr(cov, 'branch_coverage') else 0.0

    # Calcular score de mutación
    mutation_score = cosmic_ray.run_tests()  # Suponiendo que cosmic_ray está configurado correctamente

    metrics = {
        "line_coverage": line_coverage,
        "branch_coverage": branch_coverage,
        "mutation_score": mutation_score
    }

    return metrics

def almacenar_metricas(metrics, output_folder_path):
    metrics_file_path = os.path.join(output_folder_path, "metrics.json")
    try:
        with open(metrics_file_path, 'w', encoding='utf-8') as file:
            file.write(str(metrics))
        print(f"Métricas calculadas y almacenadas en: {metrics_file_path}")
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
            metrics = eval(file.read())
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

def corregir_tests_con_gemini(tests, metrics):
    """
    Función para corregir los tests generados utilizando la API de Gemini.
    """
    api_key = check_gemini_api_key()
    client = genai.Client()

    prompt = f"""
    Eres un agente experto en testing automático. 
    A partir de los tests generados previamente, realiza correcciones y mejoras para optimizar la cobertura y el score de mutación.
    Actualmente, las métricas obtenidas son: {metrics}.

    Los tests son los siguientes:
    {tests}

    Devuelve solo el código de los tests corregidos sin explicaciones adicionales.
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
    tests_generados = generar_tests(contenido_archivo) # 1.1 Pedir a la IA (gemini) que desarrolle tests a partir de ese contenido
    almacenar_tests(tests_generados, output_folder) # 1.2. Almacenar tests unitarios en la ruta de output_folder en un único archivo 

    # 2 Calcular metricas de cobertura y mutación de los tests generados
    test_file_path = os.path.join(output_folder, f"test_{os.path.basename(os.path.normpath(output_folder))}.py")
    metrics = calcular_metricas(test_file_path)
    almacenar_metricas(metrics, output_folder) # 2.1 Guardar métricas en un archivo de salida (ej. metrics.json) dentro de output_folder

    # 3. Evaluar si las métricas cumplen con los valores ideales (line_coverage >= 0.80, branch_coverage >= 0.50, mutation_score >= 0.50)
    metric_file_path = os.path.join(output_folder, "metrics.json")

    while not metric_values_are_optimal(metric_file_path):
        print("Las métricas no cumplen con los valores ideales. Generando nuevos tests...")
        # Repetir el proceso de generación de tests y cálculo de métricas

        tests_generados = corregir_tests_con_gemini(tests_generados, metrics) # 3.1 Pedir a la IA (gemini) que corrija los tests generados previamente
        almacenar_tests(tests_generados, output_folder) # 3.2. Almacenar tests corregidos en la ruta de output_folder en un único archivo
        metrics = calcular_metricas(test_file_path) # 3.3 Calcular métricas
        almacenar_metricas(metrics, output_folder) # 3.4 Guardar métricas en un archivo de salida (ej. metrics.json) dentro de output_folder

    print("¡Éxito! Las métricas cumplen con los valores ideales.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente basado en LLM para generación iterativa de tests.")

    parser.add_argument("ruta_archivo", type=str, help="Ruta relativa al archivo de código fuente (ej. Proyectos_Publicos/bridge/base.py)")
    parser.add_argument("output_folder", type=str, help="Directorio general donde se guardarán los resultados (ej. Resultados)")
    
    args = parser.parse_args()
    
    main(args.ruta_archivo, args.output_folder)