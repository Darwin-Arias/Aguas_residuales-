import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ==============================
# SIMULACION CASO AQUALIMPIA S.A.
# ==============================

np.random.seed(42)

# 1. Crear datos simulados
n_registros = 200

plantas = ["Planta Norte", "Planta Centro", "Planta Sur", "Planta Industrial"]
fechas = pd.date_range(start="2025-07-01", periods=120, freq="D")

df = pd.DataFrame({
    "fecha_registro": np.random.choice(fechas, n_registros),
    "planta": np.random.choice(plantas, n_registros),
    "caudal_entrada_m3_d": np.random.randint(4000, 9000, n_registros),
    "DBO_entrada_mg_L": np.random.randint(180, 380, n_registros),
    "SST_entrada_mg_L": np.random.randint(150, 350, n_registros),
    "pH_entrada": np.round(np.random.normal(7.1, 0.35, n_registros), 2),
    "energia_aeracion_kWh": np.round(np.random.uniform(900, 2100, n_registros), 1),
    "lodos_generados_kg_d": np.round(np.random.uniform(350, 750, n_registros), 1)
})

# 2. Simular DBO de salida según eficiencia del tratamiento
# Una mayor eficiencia genera menor DBO de salida
eficiencia_simulada = np.random.uniform(0.82, 0.94, n_registros)

# Penalizar algunos registros para simular fallas intermitentes
fallas = np.random.choice([0, 1], size=n_registros, p=[0.78, 0.22])
eficiencia_simulada = eficiencia_simulada - (fallas * np.random.uniform(0.08, 0.18, n_registros))

df["DBO_salida_mg_L"] = np.round(
    df["DBO_entrada_mg_L"] * (1 - eficiencia_simulada),
    1
)

# 3. Definir cumplimiento normativo
# Supuesto: cumple si la DBO de salida es menor o igual a 35 mg/L
limite_DBO = 35

df["cumplimiento_norma"] = np.where(
    df["DBO_salida_mg_L"] <= limite_DBO,
    1,
    0
)

df["estado_cumplimiento"] = np.where(
    df["cumplimiento_norma"] == 1,
    "Cumple",
    "No cumple"
)

# 4. Calcular indicadores analíticos
df["eficiencia_remocion_DBO_pct"] = np.round(
    ((df["DBO_entrada_mg_L"] - df["DBO_salida_mg_L"]) /
     df["DBO_entrada_mg_L"]) * 100,
    2
)

df["carga_DBO_entrada_kg_d"] = np.round(
    df["caudal_entrada_m3_d"] * df["DBO_entrada_mg_L"] / 1000,
    2
)

df["carga_DBO_salida_kg_d"] = np.round(
    df["caudal_entrada_m3_d"] * df["DBO_salida_mg_L"] / 1000,
    2
)

df["energia_por_m3_kWh"] = np.round(
    df["energia_aeracion_kWh"] / df["caudal_entrada_m3_d"],
    4
)

# 5. Crear alerta operativa
df["alerta_operativa"] = np.where(
    (df["cumplimiento_norma"] == 0) |
    (df["eficiencia_remocion_DBO_pct"] < 85),
    "Alerta",
    "Normal"
)

# 6. Resumen por planta
resumen_planta = df.groupby("planta").agg(
    registros=("planta", "count"),
    caudal_promedio=("caudal_entrada_m3_d", "mean"),
    DBO_entrada_promedio=("DBO_entrada_mg_L", "mean"),
    DBO_salida_promedio=("DBO_salida_mg_L", "mean"),
    eficiencia_promedio=("eficiencia_remocion_DBO_pct", "mean"),
    cumplimiento_promedio=("cumplimiento_norma", "mean"),
    alertas=("alerta_operativa", lambda x: (x == "Alerta").sum())
).reset_index()

resumen_planta["cumplimiento_promedio"] = resumen_planta["cumplimiento_promedio"] * 100
resumen_planta = resumen_planta.round(2)

print("RESUMEN POR PLANTA")
print(resumen_planta)

print("\nREGISTROS CON ALERTA OPERATIVA")
print(df[df["alerta_operativa"] == "Alerta"].head())

# 7. Crear archivos de salida para distintas áreas

# Área de Operaciones
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

# Área de Gestión Ambiental
salida_gestion_ambiental = df[[
    "fecha_registro",
    "planta",
    "DBO_salida_mg_L",
    "estado_cumplimiento",
    "cumplimiento_norma"
]]

salida_operaciones.to_csv("salida_operaciones.csv", index=False, encoding="utf-8-sig")
salida_gestion_ambiental.to_csv("salida_gestion_ambiental.csv", index=False, encoding="utf-8-sig")
resumen_planta.to_csv("resumen_por_planta.csv", index=False, encoding="utf-8-sig")

# 8. Visualizaciones exploratorias

plt.figure(figsize=(8, 5))
plt.bar(resumen_planta["planta"], resumen_planta["cumplimiento_promedio"])
plt.axhline(90, color="red", linestyle="--", label="Meta referencial 90%")
plt.title("Cumplimiento normativo promedio por planta")
plt.xlabel("Planta")
plt.ylabel("Cumplimiento (%)")
plt.legend()
plt.tight_layout()
plt.show()

plt.figure(figsize=(8, 5))
plt.scatter(
    df["caudal_entrada_m3_d"],
    df["DBO_salida_mg_L"],
    c=df["cumplimiento_norma"],
    cmap="coolwarm",
    alpha=0.7
)
plt.axhline(limite_DBO, color="red", linestyle="--", label="Limite DBO")
plt.title("Relacion entre caudal de entrada y DBO de salida")
plt.xlabel("Caudal de entrada (m3/d)")
plt.ylabel("DBO de salida (mg/L)")
plt.legend()
plt.tight_layout()
plt.show()

plt.figure(figsize=(8, 5))
plt.boxplot(
    [df[df["planta"] == planta]["eficiencia_remocion_DBO_pct"] for planta in plantas],
    labels=plantas
)
plt.title("Distribucion de eficiencia de remocion de DBO por planta")
plt.xlabel("Planta")
plt.ylabel("Eficiencia de remocion (%)")
plt.tight_layout()
plt.show()

# 9. Interpretacion final automatizada

cumplimiento_global = df["cumplimiento_norma"].mean() * 100
eficiencia_global = df["eficiencia_remocion_DBO_pct"].mean()
total_alertas = (df["alerta_operativa"] == "Alerta").sum()

print("\nINTERPRETACION GENERAL")
print(f"Cumplimiento normativo global: {cumplimiento_global:.2f}%")
print(f"Eficiencia promedio de remocion de DBO: {eficiencia_global:.2f}%")
print(f"Total de alertas operativas detectadas: {total_alertas}")

if cumplimiento_global < 90:
    print("Se recomienda priorizar acciones correctivas en las plantas con menor cumplimiento.")
else:
    print("El desempeño general es aceptable, aunque se deben revisar las alertas puntuales.")
