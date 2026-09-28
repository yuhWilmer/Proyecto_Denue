"""Ejecución por lote del banco de preguntas de prueba.

Uso:
    python -m app.lote [--desde P01] [--hasta P10] [--simulado]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
import traceback

from app.agente import Bitacora, responder
from app.herramientas import Herramientas, cargar_datos


def main() -> None:
    parser = argparse.ArgumentParser(description="Ejecución por lotes del banco de preguntas.")
    parser.add_argument("--desde", type=str, default="P01", help="ID de la primera pregunta a ejecutar (ej: P01)")
    parser.add_argument("--hasta", type=str, default="P10", help="ID de la última pregunta a ejecutar (ej: P10)")
    parser.add_argument("--simulado", action="store_true", help="Usa el modelo simulado sin red")
    args = parser.parse_args()

    # Cargar banco de preguntas
    ruta_preguntas = Path("data/preguntas_prueba.json")
    with open(ruta_preguntas, "r", encoding="utf-8") as f:
        datos_preguntas = json.load(f)
    todas_preguntas = datos_preguntas.get("preguntas", [])

    # Filtrar por rango
    id_desde = args.desde.upper()
    id_hasta = args.hasta.upper()
    preguntas_a_ejecutar = [
        p for p in todas_preguntas
        if id_desde <= p["id"].upper() <= id_hasta
    ]

    print(f"Iniciando ejecución de {len(preguntas_a_ejecutar)} preguntas ({id_desde} a {id_hasta})...")

    # Cargar datos e instrucciones
    datos, sectores = cargar_datos("data/denue_tampico_madero.csv", "data/sectores_scian.csv")
    herramientas = Herramientas(datos, sectores)
    ruta_sistema = Path("prompts/sistema.md")
    sistema = ruta_sistema.read_text(encoding="utf-8") if ruta_sistema.exists() else ""

    if args.simulado:
        from app.modelo_simulado import llamar_modelo
        modelo_nombre = "simulado"
    else:
        from app.modelo import llamar_modelo
        modelo_nombre = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

    bitacora = Bitacora(modelo_nombre=modelo_nombre)
    print(f"Registrando en: {bitacora.ruta}")

    for idx, item in enumerate(preguntas_a_ejecutar):
        pid = item["id"]
        pregunta = item["pregunta"]
        print(f"\n[{idx + 1}/{len(preguntas_a_ejecutar)}] Ejecutando {pid}: {pregunta}")

        try:
            res = responder(
                pregunta=pregunta,
                herramientas=herramientas,
                sistema=sistema,
                llamar=llamar_modelo,
                bitacora=bitacora,
                id_pregunta=pid,
                canal="terminal",
            )
            print(f"-> Completada en {res['turnos']} turnos, {res['herramientas']} herramientas ({res['segundos']}s)")
            print(f"Respuesta:\n{res['respuesta']}")
        except Exception as e:
            error_detalle = f"{type(e).__name__}: {str(e)}"
            print(f"-> ERROR en {pid}: {error_detalle}")
            bitacora.registrar(pid, "error", error=error_detalle, traceback=traceback.format_exc())

        # Si es modelo real y aún quedan preguntas, pausar 4 segundos para cuidar cuota
        if not args.simulado and idx < len(preguntas_a_ejecutar) - 1:
            print("Pausa de 4 segundos para respetar cuota...")
            time.sleep(4)

    print("\nEjecución por lote terminada.")


if __name__ == "__main__":
    main()
