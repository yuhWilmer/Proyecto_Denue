"""Bot de Telegram para el Agente analista del DENUE.

Actúa estrictamente como canal de entrada/salida: recibe mensajes, invoca
a agente.responder en un hilo secundario con asyncio.to_thread y devuelve el texto.
NO contiene lógica del agente, NO ejecuta herramientas por su cuenta y NO llama al SDK de Gemini directamente.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import os
from pathlib import Path
from typing import Any, Callable

from dotenv import load_dotenv
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.agente import Bitacora, responder
from app.herramientas import Herramientas, cargar_datos

load_dotenv()

# Bajar nivel de log para evitar imprimir URLs con token de Telegram
logging.basicConfig(level=logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

MENSAJE_START = (
    "🤖 *Agente Analista del DENUE*\n\n"
    "¡Hola! Soy un agente inteligente especializado en consultar los negocios y unidades económicas "
    "de Tampico y Ciudad Madero, con base en el DENUE 05/2026 del INEGI.\n\n"
    "📌 *¿Qué puedo responder?*\n"
    "• Conteo y ubicación de comercios, servicios e industrias.\n"
    "• Rankings por municipio, colonia, sector o actividad SCIAN.\n"
    "• Listados de establecimientos por rango de personal.\n\n"
    "⚠️ *Lo que NO contiene el DENUE:*\n"
    "• No registra número exacto de empleados (sólo rangos).\n"
    "• No contiene ventas, salarios, ingresos ni calificaciones.\n\n"
    "⏱️ *Tiempo de respuesta:*\n"
    "Cada consulta analiza miles de registros con verificación de cifras, por lo que una respuesta puede tardar varios segundos.\n\n"
    "🔒 *Aviso de privacidad:*\n"
    "Por favor, NO escribas datos personales sensibles. Tus mensajes son procesados a través de los servidores de Telegram y la API de Google."
)

MENSAJE_FUENTE = (
    "📊 *Fuente Oficial de Datos*\n\n"
    "Directorio Estadístico Nacional de Unidades Económicas (DENUE), edición 05/2026, INEGI.\n"
    "Recorte regional: Tampico y Ciudad Madero (22,900 establecimientos activos).\n"
    "Uso bajo los Términos de Libre Uso de la Información del INEGI."
)


def leer_permitidos(cadena: str | None) -> set[int]:
    """Parsea una lista de identificadores numéricos de Telegram separados por comas."""
    if not cadena:
        return set()
    permitidos = set()
    for item in cadena.split(","):
        item_limpio = item.strip()
        if item_limpio.isdigit():
            permitidos.add(int(item_limpio))
    return permitidos


def usuario_anonimo(user_id: int | str) -> str:
    """Devuelve los primeros 10 caracteres del SHA-256 del identificador de usuario."""
    return hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:10]


def partir_mensaje(texto: str, max_longitud: int = 4096) -> list[str]:
    """Divide un texto en trozos de 4096 caracteres o menos, priorizando cortes por saltos de línea."""
    if not texto:
        return [""]
    if len(texto) <= max_longitud:
        return [texto]

    trozos: list[str] = []
    restante = texto

    while len(restante) > max_longitud:
        corte = restante.rfind("\n", 0, max_longitud)
        if corte <= 0:
            corte = restante.rfind(" ", 0, max_longitud)
        if corte <= 0:
            corte = max_longitud

        trozos.append(restante[:corte].strip())
        restante = restante[corte:].lstrip()

    if restante:
        trozos.append(restante)

    return trozos


async def con_escribiendo(
    chat: Any,
    funcion: Callable[..., Any],
    *args: Any,
) -> Any:
    """Ejecuta una función síncrona/bloqueante en otro hilo con asyncio.to_thread,
    enviando la acción 'TYPING' cada 4 segundos para no congelar el bot."""
    tarea = asyncio.ensure_future(asyncio.to_thread(funcion, *args))
    while not tarea.done():
        try:
            await chat.send_action(ChatAction.TYPING)
        except Exception:
            pass
        await asyncio.wait([tarea], timeout=4)
    return tarea.result()


async def comando_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(MENSAJE_START, parse_mode="Markdown")


async def comando_fuente(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(MENSAJE_FUENTE, parse_mode="Markdown")


async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_user or not update.effective_message:
        return

    user_id = update.effective_user.id
    texto = update.effective_message.text or ""

    cadena_permitidos = os.environ.get("TELEGRAM_USUARIOS_PERMITIDOS", "")
    permitidos = leer_permitidos(cadena_permitidos)

    if user_id not in permitidos:
        msg_no_autorizado = (
            "⛔ *Acceso no autorizado*\n\n"
            "Este bot es privado y sólo atiende a usuarios autorizados.\n"
            f"Tu identificador numérico de Telegram es: `{user_id}`\n\n"
            "Para autorizarte, agrega este número a la variable `TELEGRAM_USUARIOS_PERMITIDOS` en el archivo `.env`."
        )
        await update.effective_message.reply_text(msg_no_autorizado, parse_mode="Markdown")
        return

    # Incrementar contador de peticiones de Telegram
    contador_tg = context.bot_data.get("contador_tg", 0) + 1
    context.bot_data["contador_tg"] = contador_tg
    id_pregunta = f"TG-{contador_tg}"

    herramientas: Herramientas = context.bot_data["herramientas"]
    sistema: str = context.bot_data["sistema"]
    llamar = context.bot_data["llamar"]
    bitacora: Bitacora = context.bot_data["bitacora"]
    u_hash = usuario_anonimo(user_id)

    try:
        resultado = await con_escribiendo(
            update.effective_chat,
            responder,
            texto,
            herramientas,
            sistema,
            llamar,
            bitacora,
            id_pregunta,
            "telegram",
            u_hash,
        )
        respuesta_texto = resultado.get("respuesta", "Sin respuesta disponible.")
    except Exception as e:
        error_msg = f"Error temporal: {type(e).__name__}"
        bitacora.registrar(id_pregunta, "error", error=error_msg)
        respuesta_texto = "Lo sentimos, ocurrió un problema temporal al procesar tu solicitud. Por favor intenta de nuevo en unos momentos."

    for trozo in partir_mensaje(respuesta_texto):
        await update.effective_message.reply_text(trozo)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot de Telegram para el Agente analista del DENUE.")
    parser.add_argument("--simulado", action="store_true", help="Usa el modelo simulado sin red")
    args = parser.parse_args()

    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        print("ERROR: TELEGRAM_BOT_TOKEN no está definido en las variables de entorno.")
        return

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

    app = ApplicationBuilder().token(token).build()
    app.bot_data["herramientas"] = herramientas
    app.bot_data["sistema"] = sistema
    app.bot_data["llamar"] = llamar_modelo
    app.bot_data["bitacora"] = bitacora
    app.bot_data["contador_tg"] = 0

    app.add_handler(CommandHandler("start", comando_start))
    app.add_handler(CommandHandler("fuente", comando_fuente))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))

    print(f"Bot de Telegram iniciado (modelo: {modelo_nombre}). Presiona Ctrl+C para detener.")
    app.run_polling()


if __name__ == "__main__":
    main()
