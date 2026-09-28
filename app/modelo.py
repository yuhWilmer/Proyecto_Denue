"""Módulo de comunicación con el modelo de lenguaje de Google Gemini.

Único archivo del proyecto que crea el cliente de Gemini y desactiva
explícitamente la ejecución automática de herramientas del SDK.
"""
from __future__ import annotations

import os
from typing import Any
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

_cliente: genai.Client | None = None


def obtener_cliente() -> genai.Client:
    """Obtiene o inicializa el cliente de Gemini con reintentos configurados."""
    global _cliente
    if _cliente is None:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "La variable de entorno GEMINI_API_KEY no está configurada en .env"
            )
        _cliente = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                retry_options=types.HttpRetryOptions(
                    attempts=5, initial_delay=2.0, max_delay=30.0
                )
            ),
        )
    return _cliente


def llamar_modelo(
    historial: list[Any],
    sistema: str,
    declaraciones: list[dict[str, Any]],
    forzar_texto: bool = False,
) -> types.GenerateContentResponse:
    """Envía el historial al modelo Gemini y devuelve la respuesta del SDK tal cual."""
    cliente = obtener_cliente()
    modelo = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

    config = types.GenerateContentConfig(
        system_instruction=sistema,
        tools=[types.Tool(function_declarations=declaraciones)],
        automatic_function_calling=types.AutomaticFunctionCallingConfig(
            disable=True
        ),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode="NONE" if forzar_texto else "AUTO"
            )
        ),
    )

    respuesta = cliente.models.generate_content(
        model=modelo,
        contents=historial,
        config=config,
    )
    return respuesta
