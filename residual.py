from pathlib import Path
import argparse
import base64
import shutil

import matplotlib.pyplot as plt
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
OUTPUTS_DIR = BASE_DIR / "outputs"
DASHBOARD_DIR = BASE_DIR / "dashboard"
DEFAULT_SOURCE = Path(
    r"C:\Users\drafg\Desktop\Ciencia de Datos\Semana 8\dataset_set_A_aguas_residuales.xlsx"
)
LOCAL_DATASET = DATA_DIR / "dataset_set_A_aguas_residuales.xlsx"


def preparar_carpetas() -> None:
    for folder in [DATA_DIR, OUTPUTS_DIR, DASHBOARD_DIR]:
        folder.mkdir(parents=True, exist_ok=True)


def cargar_datos(source: Path) -> pd.DataFrame:
    if source.exists() and source != LOCAL_DATASET:
        shutil.copy2(source, LOCAL_DATASET)
    input_path = LOCAL_DATASET if LOCAL_DATASET.exists() else source
    if not input_path.exists():
        raise FileNotFoundError(f"No se encontro el dataset: {input_path}")

    df = pd.read_excel(input_path)
    df.columns = [col.strip() for col in df.columns]
    df["fecha_registro"] = pd.to_datetime(df["fecha_registro"], errors="coerce")

    columnas_numericas = [
        "caudal_entrada_m3_d",
        "DBO_entrada_mg_L",
        "SST_entrada_mg_L",
        "pH_entrada",
        "energia_aeracion_kWh",
        "lodos_generados_kg_d",
        "DBO_salida_mg_L",
        "cumplimiento_norma",
    ]
    for col in columnas_numericas:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    df = df.dropna(subset=["fecha_registro", "planta"])
    return df


def enriquecer_datos(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["eficiencia_remocion_DBO_pct"] = (
        (df["DBO_entrada_mg_L"] - df["DBO_salida_mg_L"])
        / df["DBO_entrada_mg_L"]
        * 100
    )
    df["carga_DBO_entrada_kg_d"] = (
        df["caudal_entrada_m3_d"] * df["DBO_entrada_mg_L"] / 1000
    )
    df["carga_DBO_salida_kg_d"] = (
        df["caudal_entrada_m3_d"] * df["DBO_salida_mg_L"] / 1000
    )
    df["energia_por_m3_kWh"] = df["energia_aeracion_kWh"] / df["caudal_entrada_m3_d"]
    df["estado_cumplimiento"] = df["cumplimiento_norma"].map(
        {1: "Cumple", 0: "No cumple"}
    )
    df["alerta_operativa"] = (
        (df["cumplimiento_norma"] == 0)
        | (df["eficiencia_remocion_DBO_pct"] < 85)
        | (df["DBO_salida_mg_L"] > 35)
    ).map({True: "Alerta", False: "Normal"})
    df["mes"] = df["fecha_registro"].dt.to_period("M").astype(str)
    return df.sort_values("fecha_registro")


def resumen_general(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "indicador": [
                "Registros analizados",
                "Plantas evaluadas",
                "Cumplimiento normativo promedio (%)",
                "DBO salida promedio (mg/L)",
                "Eficiencia remocion DBO promedio (%)",
                "Alertas operativas",
            ],
            "valor": [
                len(df),
                df["planta"].nunique(),
                round(df["cumplimiento_norma"].mean() * 100, 2),
                round(df["DBO_salida_mg_L"].mean(), 2),
                round(df["eficiencia_remocion_DBO_pct"].mean(), 2),
                int((df["alerta_operativa"] == "Alerta").sum()),
            ],
        }
    )


def resumen_por_planta(df: pd.DataFrame) -> pd.DataFrame:
    resumen = (
        df.groupby("planta")
        .agg(
            registros=("planta", "size"),
            caudal_promedio_m3_d=("caudal_entrada_m3_d", "mean"),
            DBO_entrada_promedio_mg_L=("DBO_entrada_mg_L", "mean"),
            DBO_salida_promedio_mg_L=("DBO_salida_mg_L", "mean"),
            eficiencia_promedio_pct=("eficiencia_remocion_DBO_pct", "mean"),
            energia_promedio_kWh=("energia_aeracion_kWh", "mean"),
            lodos_promedio_kg_d=("lodos_generados_kg_d", "mean"),
            cumplimiento_pct=("cumplimiento_norma", lambda x: x.mean() * 100),
            alertas=("alerta_operativa", lambda x: (x == "Alerta").sum()),
        )
        .reset_index()
    )
    columnas_redondeo = resumen.select_dtypes("number").columns
    resumen[columnas_redondeo] = resumen[columnas_redondeo].round(2)
    return resumen.sort_values("cumplimiento_pct")


def guardar_salidas(df: pd.DataFrame, resumen_planta: pd.DataFrame) -> None:
    operaciones = df[
        [
            "fecha_registro",
            "planta",
            "caudal_entrada_m3_d",
            "DBO_entrada_mg_L",
            "DBO_salida_mg_L",
            "eficiencia_remocion_DBO_pct",
            "energia_aeracion_kWh",
            "energia_por_m3_kWh",
            "lodos_generados_kg_d",
            "alerta_operativa",
        ]
    ]
    ambiental = df[
        [
            "fecha_registro",
            "planta",
            "DBO_salida_mg_L",
            "estado_cumplimiento",
            "cumplimiento_norma",
            "eficiencia_remocion_DBO_pct",
        ]
    ]

    operaciones.to_csv(OUTPUTS_DIR / "salida_operaciones.csv", index=False, encoding="utf-8-sig")
    ambiental.to_csv(OUTPUTS_DIR / "salida_gestion_ambiental.csv", index=False, encoding="utf-8-sig")
    resumen_planta.to_csv(OUTPUTS_DIR / "resumen_por_planta.csv", index=False, encoding="utf-8-sig")

    with pd.ExcelWriter(OUTPUTS_DIR / "aqualimpia_resultados.xlsx", engine="openpyxl") as writer:
        resumen_general(df).to_excel(writer, sheet_name="Resumen_general", index=False)
        resumen_planta.to_excel(writer, sheet_name="Resumen_por_planta", index=False)
        operaciones.to_excel(writer, sheet_name="Operaciones", index=False)
        ambiental.to_excel(writer, sheet_name="Gestion_ambiental", index=False)


def guardar_grafico(path: Path, fig) -> str:
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    return base64.b64encode(path.read_bytes()).decode("utf-8")


def crear_graficos(df: pd.DataFrame, resumen_planta: pd.DataFrame) -> dict:
    colores = ["#2166AC", "#67A9CF", "#F4A261", "#D1495B", "#2A9D8F"]
    graficos = {}

    fig, ax = plt.subplots(figsize=(8, 4.5))
    orden = resumen_planta.sort_values("cumplimiento_pct", ascending=False)
    ax.bar(orden["planta"], orden["cumplimiento_pct"], color=colores[: len(orden)])
    ax.axhline(df["cumplimiento_norma"].mean() * 100, color="#333333", linestyle="--", linewidth=1)
    ax.set_title("Cumplimiento normativo por planta")
    ax.set_ylabel("Cumplimiento (%)")
    ax.set_ylim(0, 100)
    ax.grid(axis="y", alpha=0.25)
    graficos["cumplimiento"] = guardar_grafico(DASHBOARD_DIR / "cumplimiento_por_planta.png", fig)

    mensual = (
        df.groupby(["mes", "planta"])["DBO_salida_mg_L"]
        .mean()
        .reset_index()
        .pivot(index="mes", columns="planta", values="DBO_salida_mg_L")
    )
    fig, ax = plt.subplots(figsize=(8, 4.5))
    mensual.plot(ax=ax, marker="o")
    ax.axhline(35, color="#D1495B", linestyle="--", linewidth=1, label="Referencia alerta 35 mg/L")
    ax.set_title("Tendencia mensual de DBO de salida")
    ax.set_ylabel("DBO salida (mg/L)")
    ax.set_xlabel("Mes")
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8)
    graficos["dbo_mensual"] = guardar_grafico(DASHBOARD_DIR / "dbo_salida_mensual.png", fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    scatter = ax.scatter(
        df["caudal_entrada_m3_d"],
        df["DBO_salida_mg_L"],
        c=df["cumplimiento_norma"],
        cmap="RdYlGn",
        alpha=0.78,
        edgecolor="#222222",
        linewidth=0.3,
    )
    ax.set_title("Relacion entre caudal de entrada y DBO de salida")
    ax.set_xlabel("Caudal entrada (m3/d)")
    ax.set_ylabel("DBO salida (mg/L)")
    ax.grid(alpha=0.25)
    graficos["dispersion"] = guardar_grafico(DASHBOARD_DIR / "caudal_vs_dbo_salida.png", fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    orden_ef = resumen_planta.sort_values("eficiencia_promedio_pct", ascending=True)
    ax.barh(orden_ef["planta"], orden_ef["eficiencia_promedio_pct"], color="#2A9D8F")
    ax.set_title("Eficiencia promedio de remocion de DBO")
    ax.set_xlabel("Eficiencia (%)")
    ax.grid(axis="x", alpha=0.25)
    graficos["eficiencia"] = guardar_grafico(DASHBOARD_DIR / "eficiencia_remocion.png", fig)

    return graficos


def crear_dashboard(df: pd.DataFrame, resumen_planta: pd.DataFrame, graficos: dict) -> None:
    kpis = resumen_general(df)
    tabla_planta = resumen_planta.to_html(index=False, classes="tabla", border=0)
    fecha_min = df["fecha_registro"].min().strftime("%d-%m-%Y")
    fecha_max = df["fecha_registro"].max().strftime("%d-%m-%Y")

    html = f"""<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <title>Dashboard AquaLimpia S. A.</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f7f9; color: #1f2933; }}
    header {{ background: #0b4f6c; color: white; padding: 28px 40px; }}
    main {{ padding: 28px 40px; }}
    h1, h2 {{ margin: 0 0 12px 0; }}
    .subtitulo {{ opacity: .9; }}
    .kpis {{ display: grid; grid-template-columns: repeat(3, minmax(180px, 1fr)); gap: 14px; margin: 22px 0; }}
    .kpi {{ background: white; border-left: 5px solid #2a9d8f; padding: 16px; box-shadow: 0 1px 5px rgba(0,0,0,.08); }}
    .kpi strong {{ display: block; font-size: 24px; color: #0b4f6c; margin-top: 8px; }}
    .grid {{ display: grid; grid-template-columns: repeat(2, minmax(280px, 1fr)); gap: 18px; }}
    .panel {{ background: white; padding: 18px; box-shadow: 0 1px 5px rgba(0,0,0,.08); }}
    img {{ width: 100%; height: auto; }}
    .tabla {{ width: 100%; border-collapse: collapse; background: white; font-size: 13px; }}
    .tabla th {{ background: #0b4f6c; color: white; text-align: left; padding: 9px; }}
    .tabla td {{ padding: 8px; border-bottom: 1px solid #d8dee4; }}
    .nota {{ background: #fff8e6; border-left: 5px solid #f4a261; padding: 14px 16px; margin: 22px 0; }}
  </style>
</head>
<body>
  <header>
    <h1>Dashboard exploratorio AquaLimpia S. A.</h1>
    <div class="subtitulo">Periodo analizado: {fecha_min} a {fecha_max}. Registros: {len(df)}.</div>
  </header>
  <main>
    <section class="kpis">
      {''.join(f'<div class="kpi">{row.indicador}<strong>{row.valor}</strong></div>' for row in kpis.itertuples())}
    </section>
    <div class="nota">
      La solucion permite priorizar plantas con menor cumplimiento, revisar desviaciones de DBO y detectar alertas operativas asociadas a eficiencia, caudal, energia y lodos.
    </div>
    <section class="grid">
      <div class="panel"><h2>Cumplimiento</h2><img src="data:image/png;base64,{graficos['cumplimiento']}"></div>
      <div class="panel"><h2>Tendencia de DBO</h2><img src="data:image/png;base64,{graficos['dbo_mensual']}"></div>
      <div class="panel"><h2>Caudal vs DBO salida</h2><img src="data:image/png;base64,{graficos['dispersion']}"></div>
      <div class="panel"><h2>Eficiencia</h2><img src="data:image/png;base64,{graficos['eficiencia']}"></div>
    </section>
    <section class="panel" style="margin-top:18px;">
      <h2>Resumen por planta</h2>
      {tabla_planta}
    </section>
  </main>
</body>
</html>"""
    (DASHBOARD_DIR / "dashboard_aqualimpia.html").write_text(html, encoding="utf-8")


def crear_informe(df: pd.DataFrame, resumen_planta: pd.DataFrame) -> None:
    peor_planta = resumen_planta.iloc[0]
    mejor_planta = resumen_planta.sort_values("cumplimiento_pct", ascending=False).iloc[0]
    texto = f"""# Informe analitico: AquaLimpia S. A.

## Enfoque propuesto

La problematica puede abordarse mediante un analisis exploratorio y reproducible en Python. El objetivo es transformar los registros operacionales de las plantas en indicadores utiles para tomar decisiones: cumplimiento normativo, DBO de entrada y salida, eficiencia de remocion, consumo energetico, generacion de lodos y alertas operativas.

Esta solucion es adecuada porque combina tres necesidades del caso: control ambiental, gestion operacional y evidencia reproducible. Al automatizar el procesamiento del dataset, la empresa puede actualizar sus resultados en nuevos periodos sin rehacer manualmente el analisis.

## Indicadores calculados

- Eficiencia de remocion de DBO: permite evaluar que porcentaje de contaminante organico es removido por el tratamiento.
- Carga de DBO de entrada y salida: relaciona concentracion con caudal, por lo que representa mejor la presion real sobre la planta.
- Cumplimiento normativo: identifica registros que cumplen o no cumplen la norma.
- Energia por metro cubico tratado: apoya la revision de eficiencia operacional.
- Alerta operativa: marca eventos con incumplimiento, DBO de salida elevada o baja eficiencia de remocion.

## Resultados principales

- Registros analizados: {len(df)}.
- Plantas evaluadas: {df['planta'].nunique()}.
- Cumplimiento promedio: {df['cumplimiento_norma'].mean() * 100:.2f}%.
- DBO de salida promedio: {df['DBO_salida_mg_L'].mean():.2f} mg/L.
- Eficiencia promedio de remocion de DBO: {df['eficiencia_remocion_DBO_pct'].mean():.2f}%.
- Planta con menor cumplimiento: {peor_planta['planta']} ({peor_planta['cumplimiento_pct']:.2f}%).
- Planta con mayor cumplimiento: {mejor_planta['planta']} ({mejor_planta['cumplimiento_pct']:.2f}%).

## Uso para la toma de decisiones

El area de Operaciones puede usar el archivo `salida_operaciones.csv` para revisar registros con alerta, comparar caudal, energia, lodos y eficiencia, y priorizar ajustes de proceso. El area de Gestion Ambiental puede usar `salida_gestion_ambiental.csv` para respaldar reportes de cumplimiento y observar tendencias de DBO del efluente tratado.

## Recomendacion

Se recomienda priorizar auditorias tecnicas en las plantas con menor cumplimiento, revisar los dias con alta DBO de salida y comparar esos eventos con caudal, carga de entrada, energia de aireacion y lodos generados. Tambien conviene actualizar este dashboard mensualmente para anticipar riesgos regulatorios.
"""
    (OUTPUTS_DIR / "informe_final.md").write_text(texto, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Proyecto analitico AquaLimpia S. A.")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE, help="Ruta del archivo Excel fuente.")
    args = parser.parse_args()

    preparar_carpetas()
    df = cargar_datos(args.source)
    df = enriquecer_datos(df)
    resumen_planta = resumen_por_planta(df)
    guardar_salidas(df, resumen_planta)
    graficos = crear_graficos(df, resumen_planta)
    crear_dashboard(df, resumen_planta, graficos)
    crear_informe(df, resumen_planta)

    print("Proyecto generado correctamente.")
    print(f"Dashboard: {DASHBOARD_DIR / 'dashboard_aqualimpia.html'}")
    print(f"Resultados: {OUTPUTS_DIR}")


if __name__ == "__main__":
    main()
