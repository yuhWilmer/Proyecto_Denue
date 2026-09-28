"""Módulo central del agente inteligente del DENUE.

Implementa el ciclo de function calling de la sección 7.2:
percibir, decidir, actuar y observar dentro de un presupuesto estricto
de turnos y herramientas, con guardia de cifras y bitácora de eventos.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any, Callable
from google.genai import types

from app.guardia import cifras_sin_respaldo, formatear_mensaje_correccion
from app.herramientas import DECLARACIONES, Herramientas

MAX_TURNOS = 5
MAX_HERRAMIENTAS = 6
HERRAMIENTAS_VALIDAS = {"buscar_actividades", "contar", "ranking", "listar"}


class Bitacora:
    """Maneja el registro estructurado de eventos en un archivo .jsonl."""

    def __init__(
        self,
        ruta_archivo: str | Path | None = None,
        corrida_id: str | None = None,
        modelo_nombre: str = "simulado",
    ) -> None:
        ahora = datetime.now()
        self.corrida_id = corrida_id or ahora.strftime("%Y%m%d-%H%M%S")
        self.modelo_nombre = modelo_nombre

        if ruta_archivo:
            self.ruta = Path(ruta_archivo)
        else:
            carpeta_logs = Path("logs")
            carpeta_logs.mkdir(parents=True, exist_ok=True)
            self.ruta = carpeta_logs / f"corrida-{self.corrida_id}.jsonl"

    def registrar(self, id_preg: str, evento: str, **kwargs: Any) -> dict[str, Any]:
        """Escribe una línea JSON en el archivo de bitácora."""
        registro = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "corrida": self.corrida_id,
            "modelo": self.modelo_nombre,
            "id": id_preg,
            "evento": evento,
            **kwargs,
        }
        self.ruta.parent.mkdir(parents=True, exist_ok=True)
        with open(self.ruta, "a", encoding="utf-8") as f:
            f.write(json.dumps(registro, ensure_ascii=False) + "\n")
        return registro


def ejecutar(herramientas: Herramientas, nombre: str, args: dict[str, Any]) -> dict[str, Any]:
    """Ejecuta una herramienta de forma segura. NUNCA lanza excepciones al modelo."""
    if nombre not in HERRAMIENTAS_VALIDAS:
        return {
            "ok": False,
            "error": f"Herramienta inexistente: '{nombre}'",
            "valores_validos": sorted(list(HERRAMIENTAS_VALIDAS)),
        }

    metodo = getattr(herramientas, nombre, None)
    if not callable(metodo):
        return {
            "ok": False,
            "error": f"Herramienta '{nombre}' no es invocable.",
            "valores_validos": sorted(list(HERRAMIENTAS_VALIDAS)),
        }

    try:
        resultado = metodo(**(args or {}))
        if not isinstance(resultado, dict):
            return {
                "ok": True,
                "resultado": resultado,
            }
        return resultado
    except TypeError as te:
        return {
            "ok": False,
            "error": f"Argumento inválido o no reconocido para '{nombre}': {str(te)}",
            "valores_validos": None,
        }
    except Exception as e:
        return {
            "ok": False,
            "error": f"Error al ejecutar '{nombre}': {str(e)}",
            "valores_validos": None,
        }


def responder(
    pregunta: str,
    herramientas: Herramientas,
    sistema: str,
    llamar: Callable[..., Any],
    bitacora: Bitacora | None = None,
    id_pregunta: str = "P01",
    canal: str = "terminal",
    usuario: str | None = None,
) -> dict[str, Any]:
    """Ejecuta el ciclo de function calling del agente (Algoritmo de la sección 7.2)."""
    t_inicio = time.time()

    # Si no se pasó bitácora, crear una por defecto
    if bitacora is None:
        bitacora = Bitacora()

    # 1. historial <- [mensaje del usuario con la pregunta]; resultados <- []; usadas <- 0
    #    corregida <- falso; forzar_texto <- falso
    historial: list[types.Content] = [
        types.Content(role="user", parts=[types.Part(text=pregunta)])
    ]
    resultados: list[dict[str, Any]] = []
    usadas = 0
    corregida = False
    forzar_texto = False

    # Evento inicio
    datos_inicio: dict[str, Any] = {"pregunta": pregunta}
    if canal == "telegram":
        datos_inicio["canal"] = "telegram"
        if usuario is not None:
            datos_inicio["usuario"] = usuario
    bitacora.registrar(id_pregunta, "inicio", **datos_inicio)

    # 2. para turno = 1 .. MAX_TURNOS:
    for turno in range(1, MAX_TURNOS + 1):
        # 3. si turno = MAX_TURNOS: forzar_texto <- verdadero
        if turno == MAX_TURNOS:
            forzar_texto = True

        # 4. respuesta <- llamar(historial, sistema, DECLARACIONES, forzar_texto); evento "modelo"
        try:
            resp_modelo = llamar(
                historial,
                sistema,
                DECLARACIONES,
                forzar_texto=forzar_texto,
            )
        except Exception as e:
            bitacora.registrar(id_pregunta, "error", error=f"Error al llamar al modelo: {str(e)}")
            duracion = time.time() - t_inicio
            return {
                "respuesta": f"Lo siento, ocurrió un error temporal al consultar el servicio: {str(e)}",
                "turnos": turno,
                "herramientas": usadas,
                "cifras_sin_respaldo": [],
                "segundos": round(duracion, 2),
            }

        tokens_in = None
        if hasattr(resp_modelo, "usage_metadata") and resp_modelo.usage_metadata is not None:
            tokens_in = resp_modelo.usage_metadata.prompt_token_count

        datos_modelo: dict[str, Any] = {
            "turno": turno,
            "forzar_texto": forzar_texto,
        }
        if tokens_in is not None:
            datos_modelo["tokens_entrada"] = tokens_in
        bitacora.registrar(id_pregunta, "modelo", **datos_modelo)

        # 5. agregar al historial el contenido del modelo TAL COMO LLEGO
        if resp_modelo.candidates and resp_modelo.candidates[0].content:
            historial.append(resp_modelo.candidates[0].content)

        pedidas = getattr(resp_modelo, "function_calls", None) or []

        # 6. si el modelo pidio herramientas:
        if pedidas:
            partes_respuesta: list[types.Part] = []
            for fc in pedidas:
                # 8. si usadas >= MAX_HERRAMIENTAS: resultado <- error "presupuesto agotado"
                if usadas >= MAX_HERRAMIENTAS:
                    resultado = {
                        "ok": False,
                        "error": "Presupuesto de herramientas agotado para esta pregunta.",
                        "valores_validos": None,
                    }
                else:
                    # 9. si no: usadas <- usadas + 1; resultado <- ejecutar(...); agregarlo a resultados
                    usadas += 1
                    args = dict(fc.args or {})
                    resultado = ejecutar(herramientas, fc.name, args)
                    resultados.append(resultado)

                # 10. evento "herramienta"; preparar su function_response con el MISMO id
                bitacora.registrar(
                    id_pregunta,
                    "herramienta",
                    nombre=fc.name,
                    args=dict(fc.args or {}),
                    ok=resultado.get("ok", False),
                    error=resultado.get("error", None),
                )

                partes_respuesta.append(
                    types.Part(
                        function_response=types.FunctionResponse(
                            id=fc.id,
                            name=fc.name,
                            response=resultado,
                        )
                    )
                )

            # 11. agregar al historial UN mensaje de usuario con todas las function_response
            historial.append(types.Content(role="user", parts=partes_respuesta))

            # 12. si usadas >= MAX_HERRAMIENTAS: forzar_texto <- verdadero
            if usadas >= MAX_HERRAMIENTAS:
                forzar_texto = True

            # 13. continuar con el siguiente turno
            continue

        # 14. texto <- respuesta.text; sin_respaldo <- cifras_sin_respaldo(texto, pregunta, resultados)
        texto = resp_modelo.text or ""
        sin_respaldo = cifras_sin_respaldo(texto, pregunta, resultados)

        # 15. evento "guardia"
        bitacora.registrar(
            id_pregunta,
            "guardia",
            cifras_sin_respaldo=sin_respaldo,
            corregida=corregida,
        )

        # 16. si sin_respaldo y no corregida y turno < MAX_TURNOS:
        if sin_respaldo and not corregida and turno < MAX_TURNOS:
            # 17. corregida <- verdadero
            corregida = True
            # 18. agregar al historial un mensaje de usuario con la correccion (seccion 8.3); continuar
            mensaje_correccion = formatear_mensaje_correccion(sin_respaldo)
            historial.append(
                types.Content(role="user", parts=[types.Part(text=mensaje_correccion)])
            )
            continue

        # 19. si sin_respaldo: agregar al texto "[Aviso] Cifras sin respaldo en los datos: [...]"
        if sin_respaldo:
            texto = f"{texto}\n\n[Aviso] Cifras sin respaldo en los datos: {sin_respaldo}"

        # 20. evento "fin"; devolver {respuesta, turnos, herramientas, cifras_sin_respaldo, segundos}
        duracion = time.time() - t_inicio
        bitacora.registrar(
            id_pregunta,
            "fin",
            respuesta=texto,
            turnos=turno,
            herramientas=usadas,
            cifras_sin_respaldo=sin_respaldo,
            segundos=round(duracion, 2),
        )

        return {
            "respuesta": texto,
            "turnos": turno,
            "herramientas": usadas,
            "cifras_sin_respaldo": sin_respaldo,
            "segundos": round(duracion, 2),
        }

    # 21. error: se agotaron los turnos sin texto
    duracion = time.time() - t_inicio
    error_msg = "Se agotaron los turnos sin que el modelo produjera un texto de respuesta."
    bitacora.registrar(id_pregunta, "error", error=error_msg)
    return {
        "respuesta": f"Lo siento, {error_msg.lower()}",
        "turnos": MAX_TURNOS,
        "herramientas": usadas,
        "cifras_sin_respaldo": [],
        "segundos": round(duracion, 2),
    }
