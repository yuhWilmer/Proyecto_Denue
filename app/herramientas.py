"""Herramientas del Agente analista del DENUE.

Módulo que contiene la normalización de texto, la carga de datos del DENUE
y las cuatro herramientas de consulta con sus filtros estructurados y declaraciones.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any
import pandas as pd

FUENTE_DENUE = "DENUE 05/2026, INEGI"

ESTRATOS_VALIDOS = [
    "0 a 5 personas",
    "6 a 10 personas",
    "11 a 30 personas",
    "31 a 50 personas",
    "51 a 100 personas",
    "101 a 250 personas",
    "251 y más personas",
]

# Orden de mayor a menor tamaño de personal ocupado
ORDEN_ESTRATOS = {estrato: idx for idx, estrato in enumerate(reversed(ESTRATOS_VALIDOS))}


def normalizar(texto: Any) -> str:
    """Convierte a minúsculas, quita acentos con NFKD (descartando no ASCII) y colapsa espacios."""
    if texto is None:
        return ""
    cadena = str(texto)
    descompuesta = unicodedata.normalize("NFKD", cadena)
    solo_ascii = "".join(c for c in descompuesta if ord(c) < 128)
    return " ".join(solo_ascii.lower().split())


def lematizar_palabra(p: str) -> str:
    """Regla de plurales sencillos de la sección 6.3:
    - Si tiene más de 5 letras y termina en 'es', quita 2 letras (hospitales -> hospital).
    - Si no, si tiene más de 4 letras y termina en 's', quita 1 letra (farmacias -> farmacia).
    """
    if len(p) > 5 and p.endswith("es"):
        return p[:-2]
    if len(p) > 4 and p.endswith("s"):
        return p[:-1]
    return p


def cargar_datos(ruta_denue: str, ruta_sectores: str) -> tuple[pd.DataFrame, dict[str, str]]:
    """Lee los dos CSV con dtype=str y keep_default_na=False.
    
    Agrega las columnas colonia_norm y actividad_norm pre-normalizadas.
    Devuelve la tupla (DataFrame, dict de sector -> nombre_sector).
    """
    df = pd.read_csv(ruta_denue, dtype=str, keep_default_na=False)
    sectores_df = pd.read_csv(ruta_sectores, dtype=str, keep_default_na=False)

    df["colonia_norm"] = df["colonia"].apply(normalizar)
    df["actividad_norm"] = df["actividad"].apply(normalizar)

    sectores_dict = dict(zip(sectores_df["sector"], sectores_df["nombre_sector"]))
    return df, sectores_dict


class Herramientas:
    """Conjunto de cuatro herramientas sobre el DENUE para Tampico y Ciudad Madero."""

    def __init__(self, datos: pd.DataFrame, sectores: dict[str, str]):
        self.datos = datos
        self.sectores = sectores
        # Mapeo rápido de codigo_act -> actividad
        subset_act = self.datos[["codigo_act", "actividad"]].drop_duplicates("codigo_act")
        self.actividades_map = dict(zip(subset_act["codigo_act"], subset_act["actividad"]))

    def _aplicar_filtros(
        self,
        df: pd.DataFrame,
        municipio: str | None = None,
        codigo_act: str | None = None,
        sector: str | None = None,
        estrato: str | None = None,
        colonia: str | None = None,
    ) -> tuple[pd.DataFrame | None, dict[str, Any], dict[str, Any] | None]:
        """Aplica los filtros comunes de forma estructurada.
        
        Devuelve (df_filtrado, filtros_aplicados, error_dict).
        Si ocurre un error de validación, df_filtrado es None y error_dict contiene la respuesta estructurada.
        """
        resultado = df
        filtros_corregidos: dict[str, Any] = {}

        # 1. Filtro municipio
        if municipio is not None:
            m_norm = normalizar(municipio)
            if m_norm == normalizar("Tampico"):
                val_corr = "Tampico"
            elif m_norm == normalizar("Ciudad Madero"):
                val_corr = "Ciudad Madero"
            else:
                return None, {}, {
                    "ok": False,
                    "error": f"Municipio '{municipio}' no es válido. Debe ser 'Tampico' o 'Ciudad Madero'.",
                    "valores_validos": ["Tampico", "Ciudad Madero"],
                }
            resultado = resultado[resultado["municipio"] == val_corr]
            filtros_corregidos["municipio"] = val_corr

        # 2. Filtro codigo_act (prefijos separados por coma)
        if codigo_act is not None:
            codigos_raw = [c.strip() for c in str(codigo_act).split(",") if c.strip()]
            if not codigos_raw:
                return None, {}, {
                    "ok": False,
                    "error": "El filtro codigo_act no puede estar vacío.",
                    "valores_validos": None,
                }
            for c in codigos_raw:
                if not (c.isdigit() and 2 <= len(c) <= 6):
                    return None, {}, {
                        "ok": False,
                        "error": f"Código SCIAN '{c}' inválido. Debe contener entre 2 y 6 dígitos numéricos.",
                        "valores_validos": None,
                    }
            prefijos = tuple(codigos_raw)
            mascara = resultado["codigo_act"].apply(lambda cod: cod.startswith(prefijos))
            resultado = resultado[mascara]
            filtros_corregidos["codigo_act"] = ",".join(codigos_raw)

        # 3. Filtro sector
        if sector is not None:
            sec_limpio = str(sector).strip()
            if sec_limpio not in self.sectores:
                return None, {}, {
                    "ok": False,
                    "error": f"Sector '{sector}' no existe en el catálogo SCIAN.",
                    "valores_validos": list(self.sectores.keys()),
                }
            resultado = resultado[resultado["sector"] == sec_limpio]
            filtros_corregidos["sector"] = sec_limpio

        # 4. Filtro estrato
        if estrato is not None:
            e_norm = normalizar(estrato)
            estrato_encontrado = None
            for est in ESTRATOS_VALIDOS:
                if normalizar(est) == e_norm:
                    estrato_encontrado = est
                    break
            if estrato_encontrado is None:
                return None, {}, {
                    "ok": False,
                    "error": f"Estrato '{estrato}' no es válido.",
                    "valores_validos": ESTRATOS_VALIDOS,
                }
            resultado = resultado[resultado["estrato"] == estrato_encontrado]
            filtros_corregidos["estrato"] = estrato_encontrado

        # 5. Filtro colonia (se aplica después de los demás filtros)
        if colonia is not None:
            c_norm = normalizar(colonia)
            mascara_col = resultado["colonia_norm"] == c_norm
            filas_col = resultado[mascara_col]
            if filas_col.empty:
                # Buscar sugerencias de colonias parecidas que contengan el texto
                colonias_candidatas = [
                    c for c in resultado["colonia"].unique()
                    if c_norm in normalizar(c) and c.strip()
                ]
                if not colonias_candidatas:
                    colonias_candidatas = [
                        c for c in self.datos["colonia"].unique()
                        if c_norm in normalizar(c) and c.strip()
                    ]
                return None, {}, {
                    "ok": False,
                    "error": f"No se encontraron establecimientos en la colonia '{colonia}'.",
                    "valores_validos": colonias_candidatas[:10],
                }
            # Nombre representativo tal como aparece en los datos
            nombre_col = filas_col["colonia"].iloc[0]
            filtros_corregidos["colonia"] = nombre_col
            resultado = filas_col

        return resultado, filtros_corregidos, None

    def buscar_actividades(self, texto: str) -> dict[str, Any]:
        """Busca clases de actividad por palabras clave con lematización simple de plurales."""
        if not texto or not isinstance(texto, str) or not texto.strip():
            return {
                "ok": False,
                "error": "El parámetro 'texto' es obligatorio y no puede estar vacío.",
                "valores_validos": None,
            }

        palabras = [
            lematizar_palabra(w)
            for w in re.findall(r"[a-z0-9]+", normalizar(texto))
            if len(w) >= 3
        ]

        # Si tras el filtro de 3 letras no quedan palabras, buscar con las palabras originales normalizadas
        if not palabras:
            palabras = [w for w in re.findall(r"[a-z0-9]+", normalizar(texto)) if w]

        if not palabras:
            return {
                "ok": True,
                "fuente": FUENTE_DENUE,
                "actividades": [],
            }

        # Filtrar actividades que contengan todas las palabras
        def coincide(act_norm: str) -> bool:
            return all(p in act_norm for p in palabras)

        mascara = self.datos["actividad_norm"].apply(coincide)
        coincidentes = self.datos[mascara]

        if coincidentes.empty:
            return {
                "ok": True,
                "fuente": FUENTE_DENUE,
                "actividades": [],
            }

        conteo = (
            coincidentes.groupby(["codigo_act", "actividad"])
            .size()
            .reset_index(name="establecimientos")
            .sort_values(by="establecimientos", ascending=False)
            .head(15)
        )

        lista_act = [
            {
                "codigo_act": fila["codigo_act"],
                "actividad": fila["actividad"],
                "establecimientos": int(fila["establecimientos"]),
            }
            for _, fila in conteo.iterrows()
        ]

        return {
            "ok": True,
            "fuente": FUENTE_DENUE,
            "actividades": lista_act,
        }

    def contar(
        self,
        municipio: str | None = None,
        codigo_act: str | None = None,
        sector: str | None = None,
        estrato: str | None = None,
        colonia: str | None = None,
    ) -> dict[str, Any]:
        """Cuenta establecimientos que cumplen con los filtros indicados."""
        filtrado, filtros_aplicados, error = self._aplicar_filtros(
            self.datos,
            municipio=municipio,
            codigo_act=codigo_act,
            sector=sector,
            estrato=estrato,
            colonia=colonia,
        )
        if error is not None:
            return error

        assert filtrado is not None
        return {
            "ok": True,
            "fuente": FUENTE_DENUE,
            "filtros": filtros_aplicados,
            "total": int(len(filtrado)),
        }

    def ranking(
        self,
        por: str,
        top: int = 5,
        municipio: str | None = None,
        codigo_act: str | None = None,
        sector: str | None = None,
        estrato: str | None = None,
    ) -> dict[str, Any]:
        """Genera un ranking de mayor a menor según una variable dada."""
        valores_por_validos = ["municipio", "colonia", "sector", "codigo_act", "estrato"]
        if por not in valores_por_validos:
            return {
                "ok": False,
                "error": f"El parámetro 'por' ('{por}') no es válido. Debe ser uno de: {valores_por_validos}.",
                "valores_validos": valores_por_validos,
            }

        # Ajuste de top al rango 1 a 20
        try:
            top_int = int(top)
        except (ValueError, TypeError):
            top_int = 5
        top_ajustado = max(1, min(20, top_int))

        # Ranking no filtra por colonia según el contrato (sección 6.3)
        filtrado, filtros_aplicados, error = self._aplicar_filtros(
            self.datos,
            municipio=municipio,
            codigo_act=codigo_act,
            sector=sector,
            estrato=estrato,
            colonia=None,
        )
        if error is not None:
            return error

        assert filtrado is not None
        total_filtrado = int(len(filtrado))

        # Agrupar por la variable solicitada
        conteo = (
            filtrado.groupby(por)
            .size()
            .reset_index(name="total")
            .sort_values(by="total", ascending=False)
            .head(top_ajustado)
        )

        filas = []
        for _, fila in conteo.iterrows():
            item: dict[str, Any] = {
                "valor": fila[por],
                "total": int(fila["total"]),
            }
            if por == "codigo_act":
                item["actividad"] = self.actividades_map.get(fila[por], "")
            elif por == "sector":
                item["nombre_sector"] = self.sectores.get(fila[por], "")
            filas.append(item)

        return {
            "ok": True,
            "fuente": FUENTE_DENUE,
            "por": por,
            "top": top_ajustado,
            "total_filtrado": total_filtrado,
            "filtros": filtros_aplicados,
            "filas": filas,
        }

    def listar(
        self,
        limite: int = 10,
        municipio: str | None = None,
        codigo_act: str | None = None,
        sector: str | None = None,
        estrato: str | None = None,
        colonia: str | None = None,
    ) -> dict[str, Any]:
        """Lista establecimientos individuales; exige al menos un filtro."""
        if all(f is None for f in (municipio, codigo_act, sector, estrato, colonia)):
            return {
                "ok": False,
                "error": "listar exige al menos un filtro para evitar resultados excesivos.",
                "valores_validos": None,
            }

        try:
            limite_int = int(limite)
        except (ValueError, TypeError):
            limite_int = 10
        limite_ajustado = max(1, min(20, limite_int))

        filtrado, filtros_aplicados, error = self._aplicar_filtros(
            self.datos,
            municipio=municipio,
            codigo_act=codigo_act,
            sector=sector,
            estrato=estrato,
            colonia=colonia,
        )
        if error is not None:
            return error

        assert filtrado is not None
        total = int(len(filtrado))

        # Ordenar del estrato mayor al menor y por nombre alfabéticamente
        df_ordenado = filtrado.copy()
        df_ordenado["_estrato_rank"] = df_ordenado["estrato"].map(ORDEN_ESTRATOS).fillna(999)
        df_ordenado = df_ordenado.sort_values(by=["_estrato_rank", "nombre"], ascending=[True, True])

        muestra = df_ordenado.head(limite_ajustado)
        establecimientos = [
            {
                "id": str(fila["id"]),
                "nombre": str(fila["nombre"]),
                "actividad": str(fila["actividad"]),
                "estrato": str(fila["estrato"]),
                "colonia": str(fila["colonia"]),
                "municipio": str(fila["municipio"]),
            }
            for _, fila in muestra.iterrows()
        ]

        return {
            "ok": True,
            "fuente": FUENTE_DENUE,
            "filtros": filtros_aplicados,
            "total": total,
            "mostrados": int(len(establecimientos)),
            "establecimientos": establecimientos,
        }


# Declaraciones en esquema JSON para Gemini (Section 6.4)
DECLARACIONES = [
    {
        "name": "buscar_actividades",
        "description": "Busca clases de actividad económica en el DENUE por palabra clave (ej. 'farmacia', 'taqueria', 'escuela'). Devuelve el código SCIAN de 6 dígitos, el nombre oficial de la clase y el número de establecimientos.",
        "parameters": {
            "type": "object",
            "properties": {
                "texto": {
                    "type": "string",
                    "description": "Palabra o frase clave de la actividad o giro a buscar.",
                },
            },
            "required": ["texto"],
        },
    },
    {
        "name": "contar",
        "description": "Cuenta establecimientos que cumplen todos los filtros dados. Sin filtros cuenta todo el conjunto de 22,900 establecimientos.",
        "parameters": {
            "type": "object",
            "properties": {
                "municipio": {
                    "type": "string",
                    "description": "'Tampico' o 'Ciudad Madero'. Omítelo para abarcar ambos municipios.",
                },
                "codigo_act": {
                    "type": "string",
                    "description": "Uno o varios códigos SCIAN separados por coma ('464111,464112'). Cada código funciona como prefijo.",
                },
                "sector": {
                    "type": "string",
                    "description": "Sector SCIAN (ej: '72', '46', '31-33', '48-49').",
                },
                "estrato": {
                    "type": "string",
                    "description": "Rango de personal ocupado: '0 a 5 personas', '6 a 10 personas', '11 a 30 personas', '31 a 50 personas', '51 a 100 personas', '101 a 250 personas', '251 y más personas'.",
                },
                "colonia": {
                    "type": "string",
                    "description": "Nombre de la colonia tal como está en el DENUE.",
                },
            },
        },
    },
    {
        "name": "ranking",
        "description": "Genera una lista ordenada de mayor a menor (top N) según una variable ('municipio', 'colonia', 'sector', 'codigo_act' o 'estrato').",
        "parameters": {
            "type": "object",
            "properties": {
                "por": {
                    "type": "string",
                    "description": "Variable por la que se agrupa y ordena: 'municipio', 'colonia', 'sector', 'codigo_act' o 'estrato'.",
                },
                "top": {
                    "type": "integer",
                    "description": "Cantidad de resultados a devolver (entre 1 y 20, por omisión 5).",
                },
                "municipio": {
                    "type": "string",
                    "description": "Filtro opcional de municipio ('Tampico' o 'Ciudad Madero').",
                },
                "codigo_act": {
                    "type": "string",
                    "description": "Uno o varios códigos SCIAN separados por coma.",
                },
                "sector": {
                    "type": "string",
                    "description": "Sector SCIAN.",
                },
                "estrato": {
                    "type": "string",
                    "description": "Rango de personal ocupado.",
                },
            },
            "required": ["por"],
        },
    },
    {
        "name": "listar",
        "description": "Lista establecimientos individuales con su id, nombre, actividad, estrato, colonia y municipio. Exige al menos un filtro.",
        "parameters": {
            "type": "object",
            "properties": {
                "limite": {
                    "type": "integer",
                    "description": "Número máximo de establecimientos a listar (entre 1 y 20, por omisión 10).",
                },
                "municipio": {
                    "type": "string",
                    "description": "'Tampico' o 'Ciudad Madero'.",
                },
                "codigo_act": {
                    "type": "string",
                    "description": "Uno o varios códigos SCIAN separados por coma.",
                },
                "sector": {
                    "type": "string",
                    "description": "Sector SCIAN.",
                },
                "estrato": {
                    "type": "string",
                    "description": "Rango de personal ocupado.",
                },
                "colonia": {
                    "type": "string",
                    "description": "Nombre de la colonia.",
                },
            },
        },
    },
]
