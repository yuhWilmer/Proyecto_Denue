"""Guardia de cifras del Agente analista del DENUE.

Implementa la extracción de números, recorrido recursivo de objetos
y verificación estricta de que cada cifra de la respuesta provenga de una herramienta.
"""
from __future__ import annotations

import re
from typing import Any

MENSAJE_CORRECCION_PLANTILLA = (
    "Revisión automática: estas cifras de tu respuesta no aparecen en la pregunta "
    "ni en los resultados de las herramientas: {cifras}. No calcules sumas ni porcentajes: "
    "si necesitas un total, pídelo a una herramienta. Corrige la respuesta."
)


def numeros(texto: str) -> set[int | float]:
    """Devuelve el conjunto de cifras de un texto como números (int o float).
    
    1. Elimina marcas de lista: número seguido de punto o paréntesis y espacio al inicio de renglón ('1. ', '2) ').
    2. Reconoce enteros, enteros con comas de miles y decimales con punto:
       7,184 -> 7184; 5.5 -> 5.5; 05 -> 5.
       Un decimal con parte decimal cero se guarda como entero (ej. 5.0 -> 5).
    """
    if not texto:
        return set()

    # Eliminar marcas de lista al inicio de línea
    sin_listas = re.sub(r"(?m)^\s*\d+[\.\)]\s+", "", str(texto))

    # Reconocer enteros con comas y decimales
    patron = r"\b\d{1,3}(?:,\d{3})+(?:\.\d+)?\b|\b\d+(?:\.\d+)?\b"
    encontrados: set[int | float] = set()

    for m in re.finditer(patron, sin_listas):
        cadena = m.group(0).replace(",", "")
        if "." in cadena:
            f = float(cadena)
            encontrados.add(int(f) if f.is_integer() else f)
        else:
            encontrados.add(int(cadena))

    return encontrados


def numeros_en(objeto: Any) -> set[int | float]:
    """Recorre recursivamente diccionarios (valores), listas y textos, juntando todas las cifras.
    
    Los números de Python se tratan como su texto, y True, False y None no aportan cifras.
    """
    cifras: set[int | float] = set()
    if objeto is None or isinstance(objeto, bool):
        return cifras

    if isinstance(objeto, (int, float)):
        if isinstance(objeto, float) and objeto.is_integer():
            cifras.add(int(objeto))
        else:
            cifras.add(objeto)
    elif isinstance(objeto, str):
        cifras.update(numeros(objeto))
    elif isinstance(objeto, dict):
        for val in objeto.values():
            cifras.update(numeros_en(val))
    elif isinstance(objeto, (list, tuple, set)):
        for elem in objeto:
            cifras.update(numeros_en(elem))

    return cifras


def cifras_sin_respaldo(
    respuesta: str,
    pregunta: Any,
    resultados: Any,
) -> list[int | float]:
    """Devuelve, ordenadas, las cifras de la respuesta que no están ni en la pregunta ni en los resultados."""
    cifras_resp = numeros(respuesta)
    cifras_preg = numeros_en(pregunta)
    cifras_res = numeros_en(resultados)

    respaldadas = cifras_preg | cifras_res
    huerfanas = cifras_resp - respaldadas
    return sorted(list(huerfanas))


def formatear_mensaje_correccion(cifras: list[int | float]) -> str:
    """Genera el mensaje de corrección exacto de la sección 8.3."""
    return MENSAJE_CORRECCION_PLANTILLA.format(cifras=cifras)
