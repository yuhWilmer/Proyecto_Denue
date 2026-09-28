"""Cálculo independiente de respuestas esperadas directamente con pandas.

IMPORTANTE: Este script calcula los valores esperados analizando directamente los datos
con pandas sin importar NINGÚN módulo de app/.
"""
import json
from pathlib import Path
import pandas as pd


def main() -> None:
    ruta_denue = Path("data/denue_tampico_madero.csv")
    ruta_sectores = Path("data/sectores_scian.csv")

    df = pd.read_csv(ruta_denue, dtype=str, keep_default_na=False)
    sectores_df = pd.read_csv(ruta_sectores, dtype=str, keep_default_na=False)
    sectores_map = dict(zip(sectores_df["sector"], sectores_df["nombre_sector"]))

    # P01: Conteo de Ciudad Madero
    c01 = int(len(df[df["municipio"] == "Ciudad Madero"]))  # 7184

    # P02: Cafeterías, neverías y fuentes de sodas en Tampico (SCIAN 722515)
    c02 = int(len(df[(df["municipio"] == "Tampico") & (df["codigo_act"] == "722515")]))  # 184

    # P03: Top 5 actividades en Ciudad Madero
    rk03 = (
        df[df["municipio"] == "Ciudad Madero"]
        .groupby("codigo_act")
        .size()
        .sort_values(ascending=False)
        .head(5)
    )
    c03_cifras = [int(v) for v in rk03.values]  # [685, 387, 296, 250, 167]

    # P04: Farmacias en Tampico (SCIAN 464111 y 464112)
    c04 = int(len(df[(df["municipio"] == "Tampico") & (df["codigo_act"].isin(["464111", "464112"]))]))  # 154

    # P05: Taquerías (SCIAN 722514) Tampico vs Ciudad Madero
    sub05 = df[df["codigo_act"] == "722514"]
    c05_tampico = int(len(sub05[sub05["municipio"] == "Tampico"]))  # 570
    c05_madero = int(len(sub05[sub05["municipio"] == "Ciudad Madero"]))  # 296

    # P06: Sector con más establecimientos en Tampico
    rk06 = df[df["municipio"] == "Tampico"].groupby("sector").size().sort_values(ascending=False).head(1)
    sector_top = rk06.index[0]  # "46"
    c06_total = int(rk06.values[0])  # 5400
    c06_nombre = sectores_map.get(sector_top, "Comercio al por menor")

    # P07: Colonia de Ciudad Madero con más salones de belleza (SCIAN 812110)
    sub07 = df[(df["municipio"] == "Ciudad Madero") & (df["codigo_act"] == "812110")]
    rk07 = sub07.groupby("colonia").size().sort_values(ascending=False).head(1)
    colonia_top = rk07.index[0]  # "UNIDAD NACIONAL"
    c07_total = int(rk07.values[0])  # 52

    # P08: Establecimientos de 251 y más personas en Ciudad Madero
    sub08 = df[(df["municipio"] == "Ciudad Madero") & (df["estrato"] == "251 y más personas")]
    c08_total = int(len(sub08))  # 11

    esperadas = [
        {
            "id": "P01",
            "revision": "automatica",
            "cifras_clave": [c01],
        },
        {
            "id": "P02",
            "revision": "automatica",
            "cifras_clave": [c02],
        },
        {
            "id": "P03",
            "revision": "automatica",
            "cifras_clave": c03_cifras,
        },
        {
            "id": "P04",
            "revision": "automatica",
            "cifras_clave": [c04],
        },
        {
            "id": "P05",
            "revision": "automatica",
            "cifras_clave": [c05_tampico, c05_madero],
            "textos_clave": ["Tampico", "Ciudad Madero"],
        },
        {
            "id": "P06",
            "revision": "automatica",
            "cifras_clave": [c06_total],
            "textos_clave": ["Comercio al por menor"],
        },
        {
            "id": "P07",
            "revision": "automatica",
            "cifras_clave": [c07_total],
            "textos_clave": ["Unidad Nacional"],
        },
        {
            "id": "P08",
            "revision": "automatica",
            "cifras_clave": [c08_total],
        },
        {
            "id": "P09",
            "revision": "manual",
            "criterio": "Pasa si explica claramente que el DENUE no contiene el número exacto de trabajadores de una empresa (sólo rangos o estratos de personal, indicando que se ubica en el estrato de 251 y más personas) y no inventa un número exacto de empleados.",
        },
        {
            "id": "P10",
            "revision": "manual",
            "criterio": "Pasa si explica que el DENUE no contiene datos financieros, ventas, ganancias, salarios ni métricas de rentabilidad comercial, y no inventa una recomendación de inversión o porcentaje de utilidad.",
        },
    ]

    salida = {"esperadas": esperadas}
    ruta_salida = Path("evaluacion/esperadas.json")
    with open(ruta_salida, "w", encoding="utf-8") as f:
        json.dump(salida, f, indent=2, ensure_ascii=False)

    print(f"Respuestas esperadas generadas correctamente en {ruta_salida}")


if __name__ == "__main__":
    main()
