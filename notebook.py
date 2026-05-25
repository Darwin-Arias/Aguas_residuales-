from pathlib import Path
import nbformat as nbf

BASE_DIR = Path(__file__).resolve().parent

NOTEBOOKS_DIR = BASE_DIR / "notebooks"
NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)

nb = nbf.v4.new_notebook()

cells = []

cells.append(nbf.v4.new_markdown_cell("""
# Notebook de Análisis AquaLimpia S. A.

Este notebook presenta el análisis exploratorio del desempeño de las plantas de tratamiento de aguas residuales de AquaLimpia S. A.

El objetivo es evaluar el cumplimiento normativo, la eficiencia de remoción de DBO y posibles alertas operativas.
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 1. Importación de librerías
"""))

cells.append(nbf.v4.new_code_cell("""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 2. Carga del dataset
"""))

cells.append(nbf.v4.new_code_cell(r"""
ruta = r"../data/dataset_set_A_aguas_residuales.xlsx"

df = pd.read_excel(ruta)

df.head()
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 3. Revisión inicial de los datos
"""))

cells.append(nbf.v4.new_code_cell("""
print("Filas y columnas:", df.shape)
df.info()
"""))

cells.append(nbf.v4.new_code_cell("""
df.describe()
"""))

cells.append(nbf.v4.new_code_cell("""
df.isnull().sum()
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 4. Preparación de datos e indicadores
"""))

cells.append(nbf.v4.new_code_cell("""
df["fecha_registro"] = pd.to_datetime(df["fecha_registro"])

df["eficiencia_remocion_DBO_pct"] = np.round(
    ((df["DBO_entrada_mg_L"] - df["DBO_salida_mg_L"]) /
     df["DBO_entrada_mg_L"]) * 100,
    2
)

df["estado_cumplimiento"] = np.where(
    df["cumplimiento_norma"] == 1,
    "Cumple",
    "No cumple"
)

df["alerta_operativa"] = np.where(
    (df["cumplimiento_norma"] == 0) |
    (df["eficiencia_remocion_DBO_pct"] < 85) |
    (df["DBO_salida_mg_L"] > 35),
    "Alerta",
    "Normal"
)

df.head()
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 5. Resumen por planta
"""))

cells.append(nbf.v4.new_code_cell("""
resumen = df.groupby("planta").agg(
    registros=("planta", "count"),
    caudal_promedio=("caudal_entrada_m3_d", "mean"),
    DBO_entrada_promedio=("DBO_entrada_mg_L", "mean"),
    DBO_salida_promedio=("DBO_salida_mg_L", "mean"),
    eficiencia_promedio=("eficiencia_remocion_DBO_pct", "mean"),
    cumplimiento_promedio=("cumplimiento_norma", "mean"),
    alertas=("alerta_operativa", lambda x: (x == "Alerta").sum())
).reset_index()

resumen["cumplimiento_promedio"] = resumen["cumplimiento_promedio"] * 100
resumen = resumen.round(2)

resumen
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 6. Gráfico: cumplimiento normativo por planta
"""))

cells.append(nbf.v4.new_code_cell("""
plt.figure(figsize=(8, 5))
plt.bar(resumen["planta"], resumen["cumplimiento_promedio"], color="steelblue")
plt.axhline(90, color="red", linestyle="--", label="Meta referencial 90%")
plt.title("Cumplimiento normativo por planta")
plt.xlabel("Planta")
plt.ylabel("Cumplimiento (%)")
plt.legend()
plt.tight_layout()
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 7. Gráfico: DBO de salida promedio por planta
"""))

cells.append(nbf.v4.new_code_cell("""
plt.figure(figsize=(8, 5))
plt.bar(resumen["planta"], resumen["DBO_salida_promedio"], color="orange")
plt.axhline(35, color="red", linestyle="--", label="Límite referencial DBO")
plt.title("DBO de salida promedio por planta")
plt.xlabel("Planta")
plt.ylabel("DBO salida mg/L")
plt.legend()
plt.tight_layout()
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 8. Gráfico: relación entre caudal y DBO de salida
"""))

cells.append(nbf.v4.new_code_cell("""
plt.figure(figsize=(8, 5))
plt.scatter(
    df["caudal_entrada_m3_d"],
    df["DBO_salida_mg_L"],
    c=df["cumplimiento_norma"],
    cmap="coolwarm",
    alpha=0.7
)
plt.axhline(35, color="red", linestyle="--", label="Límite DBO")
plt.title("Relación entre caudal de entrada y DBO de salida")
plt.xlabel("Caudal entrada m3/d")
plt.ylabel("DBO salida mg/L")
plt.legend()
plt.tight_layout()
plt.show()
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 9. Archivos de salida
"""))

cells.append(nbf.v4.new_code_cell("""
from pathlib import Path

resultados_dir = Path("../resultados")
resultados_dir.mkdir(parents=True, exist_ok=True)

salida_operaciones = df[[
    "fecha_registro",
    "planta",
    "caudal_entrada_m3_d",
    "DBO_entrada_mg_L",
    "DBO_salida_mg_L",
    "energia_aeracion_kWh",
    "lodos_generados_kg_d",
    "eficiencia_remocion_DBO_pct",
    "alerta_operativa"
]]

salida_gestion_ambiental = df[[
    "fecha_registro",
    "planta",
    "DBO_salida_mg_L",
    "estado_cumplimiento",
    "cumplimiento_norma"
]]

salida_operaciones.to_csv(resultados_dir / "salida_operaciones.csv", index=False, encoding="utf-8-sig")
salida_gestion_ambiental.to_csv(resultados_dir / "salida_gestion_ambiental.csv", index=False, encoding="utf-8-sig")
resumen.to_csv(resultados_dir / "resumen_por_planta.csv", index=False, encoding="utf-8-sig")

print("Archivos generados correctamente.")
"""))

cells.append(nbf.v4.new_markdown_cell("""
## 10. Conclusiones

El análisis permite observar diferencias de desempeño entre plantas de tratamiento.  
Los indicadores de cumplimiento normativo, DBO de salida y eficiencia de remoción permiten identificar riesgos ambientales y operativos.

Los archivos generados apoyan a:

- **Operaciones:** revisión de caudal, DBO, energía, lodos y alertas.
- **Gestión Ambiental:** revisión de DBO del efluente y cumplimiento normativo.

Este notebook deja evidencia reproducible del proceso analítico aplicado al caso AquaLimpia S. A.
"""))

nb["cells"] = cells

ruta_salida = NOTEBOOKS_DIR / "analisis_aqualimpia.ipynb"

with open(ruta_salida, "w", encoding="utf-8") as f:
    nbf.write(nb, f)

print("Notebook creado correctamente en:")
print(ruta_salida)