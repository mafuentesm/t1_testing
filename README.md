

#### Inicialización del proyecto

```
cd ruta/del/proyecto
pip install -r requirements.txt
```

```mermaid
flowchart TD
    A([Inicio: main]) --> B[Verificar API Key y Leer Archivo]
    B --> C[Extraer símbolos con AST]
    C --> D[Generar Tests Iniciales con Gemini]
    D --> E[Limpiar Formato Markdown]
    E --> F[Almacenar Tests e Inyectar sys.path]
    F --> G[Calcular Métricas Iniciales]
    
    G --> H{¿Métricas Ideales?}
    H -- Sí --> Z([Fin: Suite 100% Operativa])
    
    H -- No --> I[Inicio Bucle Iterativo: Max 2]
    I --> J{¿Tiempo > 200s?}
    J -- Sí --> S[Saneamiento Final]
    
    J -- No --> K[Ejecutar Pytest con Captura]
    K --> L{¿Pasan todos los tests?}
    
    L -- No --> M[Poda Local con AST]
    M --> N{¿Pasan tras poda?}
    L -- Sí --> N
    
    N -- Sí --> O[Recalcular Métricas]
    O --> P{¿Métricas Ideales?}
    P -- Sí --> Z
    P -- No --> Q[Refinamiento con Gemini]
    
    N -- No --> Q
    
    Q --> R[Almacenar Tests Corregidos]
    R --> I
    
    S --> T[Ejecutar Pytest Final]
    T --> U{¿Pasan todos?}
    U -- No --> V[Poda Definitiva con AST]
    U -- Sí --> W[Calcular Métricas Finales]
    V --> W
    W --> Z
```