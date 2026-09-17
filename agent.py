import argparse
import os
import sys
from dotenv import load_dotenv
from google import genai

load_dotenv()

def main(ruta_archivo, output_folder):

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: No se encontró la variable GEMINI_API_KEY en el entorno.")
        sys.exit(1)
        
    print(f"Iniciando Agente de Testing Automático...")
    print(f"Ruta del archivo: {ruta_archivo}")
    print(f"Directorio de salida: {output_folder}")

    # El cliente detecta automáticamente la API key desde las variables de entorno
    client = genai.Client()

    # =====================================================================
    # EJEMPLO DE USO DE LA API (Ejemplo Genérico) 
    # =====================================================================
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
    # BORRAR DESPUÉS DE PRUEBAS
    # =====================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Agente basado en LLM para generación iterativa de tests.")

    parser.add_argument("ruta_archivo", type=str, help="Ruta relativa al archivo de código fuente (ej. Proyectos_Publicos/bridge/base.py)")
    parser.add_argument("output_folder", type=str, help="Directorio general donde se guardarán los resultados (ej. Resultados)")
    
    args = parser.parse_args()
    
    main(args.ruta_archivo, args.output_folder)