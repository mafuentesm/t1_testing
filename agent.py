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

def almacenar_tests(tests_generados, output_folder):
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    output_file_path = os.path.join(output_folder, "generated_tests.py")
    
    try:
        with open(output_file_path, 'w', encoding='utf-8') as file:
            file.write(tests_generados)
        print(f"Tests generados y almacenados en: {output_file_path}")
    except Exception as e:
        print(f"Error al escribir el archivo de tests: {e}")
        sys.exit(1)
# -- -- FUNCIONES PRINCIPALES 2 -----------------------------


"""
MAIN PARA TAREA
"""

def main(ruta_archivo, output_folder):

    api_key = check_gemini_api_key()
    if not api_key:
        print("Error: No se encontró la variable GEMINI_API_KEY en el entorno.")
        sys.exit(1)
        
    print(f"Iniciando Agente de Testing Automático...")
    print(f"Ruta del archivo: {ruta_archivo}")
    print(f"Directorio de salida: {output_folder}")

    client = genai.Client()

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

    # =====================================================================
    # Tarea
    # =====================================================================

    # 1. Leer el contenido del archivo obtenido por ruta_archivo
    contenido_archivo = read_file_content(ruta_archivo)

    # 1.1 Pedir a la IA (gemini) que desarrolle tests a partir de ese contenido
    tests_generados = generar_tests(contenido_archivo)

    # 2. Almacenar tests unitarios en la ruta de output_folder en un único archivo 
    almacenar_tests(tests_generados, output_folder)

    # 2.1 Calcular metricas de cobertura y mutación de los tests generados
    # 2.2 Guardar métricas en un archivo de salida (ej. metrics.json) dentro de output_folder (seguir la estructura de metric_example.json)

    # 3. Evaluar si las métricas cumplen con los valores ideales (line_coverage >= 0.80, branch_coverage >= 0.50, mutation_score >= 0.50)
    # 3.1 Si cumplen, finalizar el proceso y mostrar mensaje de éxito

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente basado en LLM para generación iterativa de tests.")

    parser.add_argument("ruta_archivo", type=str, help="Ruta relativa al archivo de código fuente (ej. Proyectos_Publicos/bridge/base.py)")
    parser.add_argument("output_folder", type=str, help="Directorio general donde se guardarán los resultados (ej. Resultados)")
    
    args = parser.parse_args()
    
    main(args.ruta_archivo, args.output_folder)