"""Interfaz de línea de comandos para realizar una consulta individual al agente.

Uso:
    python -m app.cli "¿Cuántas farmacias hay en Tampico?" [--simulado]
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

from app.agente import Bitacora, responder
from app.herramientas import Herramientas, cargar_datos


def main() -> None:
    parser = argparse.ArgumentParser(description="Consulta individual al agente analista del DENUE.")
    parser.add_argument("pregunta", type=str, help="Pregunta que se enviará al agente.")
    parser.add_argument("--simulado", action="store_true", help="Usa el modelo simulado sin red.")
    args = parser.parse_args()

    # Cargar datos
    datos, sectores = cargar_datos("data/denue_tampico_madero.csv", "data/sectores_scian.csv")
    herramientas = Herramientas(datos, sectores)

    # Cargar instrucciones de sistema
    ruta_sistema = Path("prompts/sistema.md")
    sistema = ruta_sistema.read_text(encoding="utf-8") if ruta_sistema.exists() else ""

    # Determinar qué modelo usar
    if args.simulado:
        from app.modelo_simulado import llamar_modelo
        modelo_nombre = "simulado"
    else:
        from app.modelo import llamar_modelo
        import os
        modelo_nombre = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

    bitacora = Bitacora(modelo_nombre=modelo_nombre)
    res = responder(
        pregunta=args.pregunta,
        herramientas=herramientas,
        sistema=sistema,
        llamar=llamar_modelo,
        bitacora=bitacora,
        id_pregunta="CLI-1",
        canal="terminal",
    )

    print("\n" + "=" * 60)
    print(res["respuesta"])
    print("=" * 60)
    print(f"Estadísticas: {res['turnos']} turnos | {res['herramientas']} herramientas usadas | {res['segundos']} segundos")
    if res["cifras_sin_respaldo"]:
        print(f"Aviso de guardia - cifras sin respaldo: {res['cifras_sin_respaldo']}")


if __name__ == "__main__":
    main()
