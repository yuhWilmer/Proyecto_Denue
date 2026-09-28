"""Pruebas sin red para las herramientas, la guardia, el ciclo y el bot.

Ejecutable con:
    python -m pruebas.prueba_herramientas
"""
from __future__ import annotations

import json
from pathlib import Path

from app.agente import Bitacora, ejecutar, responder
from app.bot import leer_permitidos, partir_mensaje, usuario_anonimo
from app.guardia import cifras_sin_respaldo, numeros, numeros_en
from app.herramientas import Herramientas, cargar_datos
from app.modelo_simulado import llamar_modelo, reiniciar_simulado


def main() -> None:
    # ---------------------------------------------------------
    # 1. Cargar datos del archivo completo
    # ---------------------------------------------------------
    datos, sectores = cargar_datos("data/denue_tampico_madero.csv", "data/sectores_scian.csv")
    h = Herramientas(datos, sectores)

    # 1.1 buscar_actividades con farmacia
    res_b = h.buscar_actividades("farmacia")
    assert res_b["ok"] is True, "buscar_actividades debe ser exitoso"
    assert len(res_b["actividades"]) >= 2, "Debe encontrar al menos 2 clases de farmacia"
    cods = [a["codigo_act"] for a in res_b["actividades"]]
    assert "464111" in cods and "464112" in cods, "Debe contener 464111 y 464112"

    # 1.2 contar municipios
    res_tam = h.contar(municipio="Tampico")
    assert res_tam["ok"] is True and res_tam["total"] == 15716, f"Tampico debe tener 15716, dio {res_tam.get('total')}"

    res_mad = h.contar(municipio="Ciudad Madero")
    assert res_mad["ok"] is True and res_mad["total"] == 7184, f"Ciudad Madero debe tener 7184, dio {res_mad.get('total')}"

    # 1.3 contar total sin filtros
    res_tot = h.contar()
    assert res_tot["ok"] is True and res_tot["total"] == 22900, f"Total debe ser 22900, dio {res_tot.get('total')}"

    # 1.4 ranking por municipio
    res_rk_mun = h.ranking(por="municipio", top=5)
    assert res_rk_mun["ok"] is True, "ranking municipio falló"
    assert res_rk_mun["filas"][0]["valor"] == "Tampico" and res_rk_mun["filas"][0]["total"] == 15716

    # 1.5 ranking por sector
    res_rk_sec = h.ranking(por="sector", top=3)
    assert res_rk_sec["ok"] is True, "ranking sector falló"
    assert "nombre_sector" in res_rk_sec["filas"][0], "ranking por sector debe incluir nombre_sector"

    # 1.6 listar con filtro
    res_lis = h.listar(limite=3, municipio="Tampico", estrato="251 y más personas")
    assert res_lis["ok"] is True, "listar debe ser exitoso"
    assert res_lis["mostrados"] <= 3, "No debe mostrar más del límite"
    assert len(res_lis["establecimientos"]) == res_lis["mostrados"]

    # ---------------------------------------------------------
    # 2. Errores estructurados
    # ---------------------------------------------------------
    # 2.1 Municipio inválido
    err_mun = h.contar(municipio="Monterrey")
    assert err_mun["ok"] is False, "Debe rechazar municipio no válido"
    assert "Tampico" in err_mun["valores_validos"] and "Ciudad Madero" in err_mun["valores_validos"]

    # 2.2 Código con letras
    err_cod_letra = h.contar(codigo_act="ABC123")
    assert err_cod_letra["ok"] is False, "Debe rechazar código SCIAN con letras"

    # 2.3 Código de longitud inválida
    err_cod_len = h.contar(codigo_act="1")
    assert err_cod_len["ok"] is False, "Debe rechazar código SCIAN menor a 2 dígitos"

    # 2.4 Sector inexistente
    err_sec = h.contar(sector="999")
    assert err_sec["ok"] is False, "Debe rechazar sector inexistente"
    assert len(err_sec["valores_validos"]) > 0

    # 2.5 Estrato inválido
    err_est = h.contar(estrato="muchos empleados")
    assert err_est["ok"] is False, "Debe rechazar estrato no reconocido"

    # 2.6 Listar sin filtros
    err_lis = h.listar(limite=5)
    assert err_lis["ok"] is False, "listar debe exigir al menos un filtro"

    # 2.7 Errores de ejecutar(): herramienta inexistente
    err_ejec_herr = ejecutar(h, "herramienta_fantasma", {})
    assert err_ejec_herr["ok"] is False, "ejecutar debe rechazar herramienta desconocida"
    assert "contar" in err_ejec_herr["valores_validos"]

    # 2.8 Errores de ejecutar(): argumento inexistente
    err_ejec_arg = ejecutar(h, "contar", {"ciudad": "Tampico"})
    assert err_ejec_arg["ok"] is False, "ejecutar debe capturar TypeError por argumento desconocido"

    # ---------------------------------------------------------
    # 3. Guardia y números
    # ---------------------------------------------------------
    # 3.1 Comas de miles y decimales
    nums_1 = numeros("Tampico tiene 7,184 comercios y 5.5 de tasa, con 05 sucursales y 10.0 de factor")
    assert 7184 in nums_1, "Debe convertir 7,184 a 7184"
    assert 5.5 in nums_1, "Debe reconocer float 5.5"
    assert 5 in nums_1, "Debe convertir 05 a entero 5"
    assert 10 in nums_1, "Debe convertir 10.0 a entero 10"

    # 3.2 Marcas de lista
    nums_lista = numeros("1. Tampico: 570\n2) Ciudad Madero: 296")
    assert 1 not in nums_lista and 2 not in nums_lista, "Debe descartar marcas de lista '1. ' y '2) '"
    assert 570 in nums_lista and 296 in nums_lista, "Debe conservar los números del renglón"

    # 3.3 Casos de la traza E.2
    pregunta_e2 = "¿Dónde hay más taquerías, en Tampico o en Ciudad Madero? Dame la cifra de cada municipio."
    res_e2 = [
        {
            "ok": True,
            "fuente": "DENUE 05/2026, INEGI",
            "actividades": [
                {
                    "codigo_act": "722514",
                    "actividad": "Restaurantes con servicio de preparación de tacos y tortas",
                    "establecimientos": 866,
                }
            ],
        },
        {
            "ok": True,
            "fuente": "DENUE 05/2026, INEGI",
            "por": "municipio",
            "filtros": {"codigo_act": "722514"},
            "total_filtrado": 866,
            "filas": [
                {"valor": "Tampico", "total": 570},
                {"valor": "Ciudad Madero", "total": 296},
            ],
        },
    ]

    # G1: Tampico tiene 570 taquerías y Ciudad Madero 296.
    assert cifras_sin_respaldo("Tampico tiene 570 taquerías y Ciudad Madero 296.", pregunta_e2, res_e2) == []

    # G2: Tampico tiene 570 y Madero 296: una diferencia de 274.
    assert cifras_sin_respaldo("Tampico tiene 570 y Madero 296: una diferencia de 274.", pregunta_e2, res_e2) == [274]

    # G3: En total hay 866; Tampico concentra el 65.8 %.
    assert cifras_sin_respaldo("En total hay 866; Tampico concentra el 65.8 %.", pregunta_e2, res_e2) == [65.8]

    # G4: Lista con 1. Tampico 570 y 2. Madero 296 Clase SCIAN 722514, DENUE 05/2026
    texto_g4 = "1. Tampico: 570\n2. Ciudad Madero: 296\nClase SCIAN 722514, DENUE 05/2026."
    assert cifras_sin_respaldo(texto_g4, pregunta_e2, res_e2) == []

    # G5: Tampico tiene 1,570 taquerías.
    assert cifras_sin_respaldo("Tampico tiene 1,570 taquerías.", pregunta_e2, res_e2) == [1570]

    # G6: Ciudad Madero tiene 570 taquerías y Tampico 296.
    assert cifras_sin_respaldo("Ciudad Madero tiene 570 taquerías y Tampico 296.", pregunta_e2, res_e2) == []

    # ---------------------------------------------------------
    # 4. Ciclo completo con modelo simulado
    # ---------------------------------------------------------
    reiniciar_simulado()
    ruta_log_test = Path("logs/test_prueba_suite.jsonl")
    ruta_log_test.unlink(missing_ok=True)
    b_test = Bitacora(ruta_archivo=ruta_log_test, modelo_nombre="simulado")

    sistema_texto = Path("prompts/sistema.md").read_text(encoding="utf-8")
    resp_sim = responder(
        pregunta="¿Cuántas farmacias hay en Tampico?",
        herramientas=h,
        sistema=sistema_texto,
        llamar=llamar_modelo,
        bitacora=b_test,
        id_pregunta="P04",
    )

    assert resp_sim["turnos"] == 4, f"El simulado debe terminar en 4 turnos, terminó en {resp_sim['turnos']}"
    assert resp_sim["herramientas"] == 2, f"El simulado debe usar 2 herramientas, usó {resp_sim['herramientas']}"
    assert resp_sim["cifras_sin_respaldo"] == [], "No debe quedar cifras sin respaldo"
    assert "154" in resp_sim["respuesta"], "La respuesta final debe contener 154"

    # Verificar secuencia de eventos en la bitácora
    eventos = [json.loads(line)["evento"] for line in ruta_log_test.read_text(encoding="utf-8").splitlines()]
    eventos_esperados = [
        "inicio",
        "modelo",
        "herramienta",
        "modelo",
        "herramienta",
        "modelo",
        "guardia",
        "modelo",
        "guardia",
        "fin",
    ]
    assert eventos == eventos_esperados, f"Secuencia de eventos incorrecta: {eventos}"
    ruta_log_test.unlink(missing_ok=True)

    # ---------------------------------------------------------
    # 5. Funciones puras del bot
    # ---------------------------------------------------------
    # 5.1 leer_permitidos
    assert leer_permitidos("123, 456, 789") == {123, 456, 789}
    assert leer_permitidos(None) == set()
    assert leer_permitidos("") == set()

    # 5.2 usuario_anonimo
    assert usuario_anonimo(123456789) == "15e2b0d3c3", "Hash SHA256 anónimo debe coincidir con el del manual"

    # 5.3 partir_mensaje
    assert partir_mensaje("hola mundo", 20) == ["hola mundo"]
    trozos = partir_mensaje("línea 1\nlínea 2\nlínea 3", 10)
    assert len(trozos) >= 2, "Debe partir el mensaje largo"
    assert all(len(t) <= 10 for t in trozos), "Ningún trozo debe superar max_longitud"

    print("OK")


if __name__ == "__main__":
    main()
