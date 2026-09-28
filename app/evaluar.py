"""Módulo de evaluación que compara las respuestas de la bitácora contra las esperadas.

Uso:
    python -m app.evaluar logs/corrida-A.jsonl [logs/corrida-B.jsonl ...]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from app.guardia import numeros
from app.herramientas import normalizar


def main() -> None:
    parser = argparse.ArgumentParser(description="Evalúa bitácoras contra las respuestas esperadas.")
    parser.add_argument("bitacoras", nargs="+", help="Rutas a uno o más archivos .jsonl de bitácoras reales.")
    args = parser.parse_args()

    # Cargar esperadas
    ruta_esp = Path("evaluacion/esperadas.json")
    if not ruta_esp.exists():
        print(f"ERROR: No se encontró {ruta_esp}")
        sys.exit(1)

    with open(ruta_esp, "r", encoding="utf-8") as f:
        datos_esp = json.load(f)
    mapa_esp = {e["id"]: e for e in datos_esp.get("esperadas", [])}

    # Leer eventos fin de las bitácoras (el último evento fin por cada id)
    ultimos_fines: dict[str, dict[str, Any]] = {}
    llamadas_totales = 0

    for ruta_b in args.bitacoras:
        p = Path(ruta_b)
        if not p.exists():
            print(f"Aviso: Bitácora {p} no encontrada, omitiendo.")
            continue

        for linea in p.read_text(encoding="utf-8").splitlines():
            linea = linea.strip()
            if not linea:
                continue
            try:
                ev = json.loads(linea)
            except json.JSONDecodeError:
                continue

            if ev.get("evento") == "modelo":
                llamadas_totales += 1

            if ev.get("evento") == "fin":
                pid = ev.get("id")
                if pid:
                    ultimos_fines[pid] = ev

    # Evaluar cada pregunta
    resultados_eval = []
    aprobadas_auto = 0
    total_auto = 0
    total_manual = 0

    print("=" * 80)
    print(f"{'ID':<6} | {'TIPO':<12} | {'ESTADO':<8} | {'TURNOS':<6} | {'HERR':<5} | {'DETALLES'}")
    print("-" * 80)

    for pid in sorted(mapa_esp.keys()):
        esp = mapa_esp[pid]
        fin = ultimos_fines.get(pid)
        rev = esp.get("revision", "automatica")

        if not fin:
            estado = "SIN_DATOS"
            detalle = "No hay evento fin en las bitácoras"
            item_res = {
                "id": pid,
                "revision": rev,
                "estado": estado,
                "detalle": detalle,
            }
            if rev == "automatica":
                total_auto += 1
            else:
                total_manual += 1
            resultados_eval.append(item_res)
            print(f"{pid:<6} | {rev:<12} | {estado:<8} | {'-':<6} | {'-':<5} | {detalle}")
            continue

        respuesta_texto = fin.get("respuesta", "")
        turnos = fin.get("turnos", 0)
        herramientas = fin.get("herramientas", 0)
        cifras_sr = fin.get("cifras_sin_respaldo", [])

        if rev == "automatica":
            total_auto += 1
            cifras_resp = numeros(respuesta_texto)
            cifras_req = esp.get("cifras_clave", [])
            textos_req = esp.get("textos_clave", [])

            cifras_cumple = all(c in cifras_resp for c in cifras_req)
            resp_norm = normalizar(respuesta_texto)
            textos_cumple = all(normalizar(t) in resp_norm for t in textos_req)

            if cifras_cumple and textos_cumple:
                estado = "PASA"
                aprobadas_auto += 1
                detalle = "Cifras y textos clave correctos"
            else:
                estado = "FALLA"
                faltantes_c = [c for c in cifras_req if c not in cifras_resp]
                faltantes_t = [t for t in textos_req if normalizar(t) not in resp_norm]
                detalle = f"Faltan cifras: {faltantes_c}, faltan textos: {faltantes_t}"
        else:
            total_manual += 1
            estado = "MANUAL"
            criterio = esp.get("criterio", "")
            detalle = f"Revisión manual: {criterio[:40]}..."

        item_res = {
            "id": pid,
            "revision": rev,
            "estado": estado,
            "turnos": turnos,
            "herramientas": herramientas,
            "cifras_sin_respaldo": cifras_sr,
            "detalle": detalle,
            "respuesta": respuesta_texto,
            "criterio": esp.get("criterio"),
        }
        resultados_eval.append(item_res)
        print(f"{pid:<6} | {rev:<12} | {estado:<8} | {turnos:<6} | {herramientas:<5} | {detalle[:35]}")

    print("=" * 80)
    print(f"Resumen: Automáticas aprobadas: {aprobadas_auto}/{total_auto} | Manuales: {total_manual} | Llamadas modelo: {llamadas_totales}")

    salida_final = {
        "aprobadas_automaticas": aprobadas_auto,
        "total_automaticas": total_auto,
        "total_manuales": total_manual,
        "llamadas_totales_modelo": llamadas_totales,
        "resultados": resultados_eval,
    }

    ruta_salida = Path("evaluacion/resultados.json")
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(salida_final, f, indent=2, ensure_ascii=False)

    print(f"Resultados guardados en {ruta_salida}")


if __name__ == "__main__":
    main()
