"""Modelo simulado para pruebas sin conexión y sin consumir cuota de API.

Implementa un guion de 4 pasos cíclicos fabricando respuestas del SDK de google-genai.
"""
from __future__ import annotations

from typing import Any
from google.genai import types


def respuesta_falsa(partes: list[types.Part]) -> types.GenerateContentResponse:
    """Crea una respuesta simulada con la misma estructura que genera el SDK."""
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(role="model", parts=partes)
            )
        ]
    )


class SimuladorSDK:
    def __init__(self) -> None:
        self.paso = 1

    def reiniciar(self) -> None:
        self.paso = 1

    def llamar(
        self,
        historial: list[Any],
        sistema: str,
        declaraciones: list[dict[str, Any]],
        forzar_texto: bool = False,
    ) -> types.GenerateContentResponse:
        paso_actual = self.paso
        # Avanzar el paso para la próxima llamada (cíclico 1 a 4)
        self.paso = (self.paso % 4) + 1

        if forzar_texto and paso_actual in (1, 2):
            partes = [
                types.Part(
                    text="Respuesta: No pude completar la consulta con el presupuesto."
                )
            ]
            return respuesta_falsa(partes)

        if paso_actual == 1:
            partes = [
                types.Part(
                    function_call=types.FunctionCall(
                        id="sim-1",
                        name="buscar_actividades",
                        args={"texto": "farmacia"},
                    )
                )
            ]
        elif paso_actual == 2:
            partes = [
                types.Part(
                    function_call=types.FunctionCall(
                        id="sim-2",
                        name="contar",
                        args={
                            "codigo_act": "464111,464112",
                            "municipio": "Tampico",
                        },
                    )
                )
            ]
        elif paso_actual == 3:
            partes = [
                types.Part(
                    text="Respuesta: En Tampico hay 160 farmacias.\nDatos: DENUE 05/2026, INEGI"
                )
            ]
        else:  # paso 4
            partes = [
                types.Part(
                    text="Respuesta: En Tampico hay 154 farmacias (clases 464111 y 464112).\nDatos: DENUE 05/2026, INEGI"
                )
            ]

        return respuesta_falsa(partes)


_simulador_global = SimuladorSDK()


def reiniciar_simulado() -> None:
    """Reinicia el simulador al paso 1."""
    _simulador_global.reiniciar()


def llamar_modelo(
    historial: list[Any],
    sistema: str,
    declaraciones: list[dict[str, Any]],
    forzar_texto: bool = False,
) -> types.GenerateContentResponse:
    """Función con la misma firma que el cliente real de Gemini."""
    return _simulador_global.llamar(
        historial, sistema, declaraciones, forzar_texto=forzar_texto
    )
