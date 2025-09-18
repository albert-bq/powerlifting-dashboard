import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os
from google.oauth2 import service_account
from google.cloud import bigquery
from dotenv import load_dotenv

# 🎨 Importar estilos
from theme import CUSTOM_COLORS, SEX_COLORS, DEFAULT_LAYOUT

# -----------------------------
# Configuración de página
# -----------------------------
st.set_page_config(
    page_title="Powerlifting Analytics Dashboard",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# Helpers de formato
# -----------------------------
def format_number(num):
    if pd.isna(num):
        return "N/A"
    if isinstance(num, (int, float, np.floating, np.integer)):
        if num >= 1000:
            return f"{num:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{num:.1f}".replace(".", ",")
    return str(num)

def format_kg(num):
    if pd.isna(num):
        return "N/A"
    return f"{format_number(num)} kg"

def format_count(num):
    try:
        n = int(num)
    except Exception:
        return "0"
    if n >= 1000:
        return f"{n:,}".replace(",", ".")
    return str(n)

# -----------------------------
# Credenciales BigQuery (con secrets)
# -----------------------------
def get_bq_client():
    """Devuelve un cliente de BigQuery usando st.secrets (funciona igual en local y en Cloud)."""
    try:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"]
        )
        client = bigquery.Client(
            credentials=creds,
            project=st.secrets["general"]["PROJECT_ID"]
        )
        return client, st.secrets["general"]["DATASET_ID"]
    except Exception as e:
        st.error(f"❌ Error al crear cliente de BigQuery: {e}")
        return None, None

# -----------------------------
# Carga de datos desde BigQuery
# -----------------------------
@st.cache_data
def load_data(sample: bool = True):
    client, dataset_id = get_bq_client()
    if not client:
        return pd.DataFrame()
    try:
        query = f"""
            SELECT 
                NameNormalized, Sex, Equipment, Country, Year, Date, AgeClass,
                WeightClass, BodyweightKg, Federation,
                Best3SquatKg, Best3BenchKg, Best3DeadliftKg, TotalKg,
                Wilks, Dots, Glossbrenner, Goodlift,
                Squat1Kg,Squat2Kg,Squat3Kg,
                Bench1Kg,Bench2Kg,Bench3Kg,
                Deadlift1Kg,Deadlift2Kg,Deadlift3Kg
            FROM `{client.project}.{dataset_id}.results_clean`
            WHERE Year >= 2000
        """
        if sample:
            query += " LIMIT 10000"
        df = client.query(query).to_dataframe(create_bqstorage_client=False)
        if "Date" in df.columns:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        return df
    except Exception as e:
        st.error(f"❌ Error al cargar datos desde BigQuery: {e}")
        return pd.DataFrame()


# 🚀 Cambiar a False para full dataset
df = load_data(sample=True)
if df.empty:
    st.stop()

# -----------------------------
# Helpers analíticos
# -----------------------------
def col_ok(df, *cols):
    return all(c in df.columns for c in cols)

def score_col(df):
    for c in ["Dots","Wilks","Goodlift","Glossbrenner"]:
        if c in df.columns:
            return c
    return None

def athlete_slice(df, name):
    return df[df["NameNormalized"] == name].copy()

def running_pr(series):
    return series.cummax()

def success_rate(row):
    out = {}
    spec = {
        "Sentadilla":["Squat1Kg","Squat2Kg","Squat3Kg"],
        "Banca":["Bench1Kg","Bench2Kg","Bench3Kg"],
        "Peso Muerto":["Deadlift1Kg","Deadlift2Kg","Deadlift3Kg"],
    }
    for lift, cols in spec.items():
        hit = sum((c in row and pd.notna(row[c]) and float(row[c])>0) for c in cols)
        out[lift] = round(100*hit/3,1)
    return out

def last_meet_rows(adf):
    if not col_ok(adf,"Date"): return None, None
    tmp = adf.sort_values("Date")
    return tmp.iloc[-1].to_dict(), tmp.tail(1)

def my_category_mask(df, row):
    mask = pd.Series(True, index=df.index)
    for c in ["Sex","Equipment","AgeClass","WeightClass"]:
        if c in df.columns and c in row and pd.notna(row[c]):
            mask &= (df[c].astype(str) == str(row[c]))
    return mask

# -----------------------------
# HEADER
# -----------------------------
st.markdown('<h1 style="text-align:center; color:#8c8cff;">Powerlifting Analytics Dashboard</h1>', unsafe_allow_html=True)
st.markdown("---")

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Información General",
    "🌍 Análisis Geográfico",
    "📦 Análisis por Categorías",
    "📑 Ficha del Atleta",
    "🎯 Comparador Personal"
])

# -----------------------------
# 1) Información General
# -----------------------------
with tab1:
    st.subheader("ℹ️ Información General")

    # -----------------------------
    # Filtros en sidebar
    # -----------------------------
    st.sidebar.header("⚙️ Configurar Filtros")

    sex_filter = st.sidebar.selectbox("Sexo", ["Todos"] + sorted(df["Sex"].dropna().unique().tolist()))
    equip_filter = st.sidebar.selectbox("Equipamiento", ["Todos"] + sorted(df["Equipment"].dropna().unique().tolist()))
    country_filter = st.sidebar.selectbox("País", ["Todos"] + sorted(df["Country"].dropna().unique().tolist()))
    year_min, year_max = int(df["Year"].min()), int(df["Year"].max())
    year_range = st.sidebar.slider("Rango de años", year_min, year_max, (year_min, year_max))
    age_filter = st.sidebar.selectbox("Categoría de edad", ["Todos"] + sorted(df["AgeClass"].dropna().unique().tolist()))
    total_min, total_max = float(df["TotalKg"].min()), float(df["TotalKg"].max())
    total_range = st.sidebar.slider("Rango de Totales (kg)", total_min, total_max, (total_min, total_max))

    # -----------------------------
    # Info dataset en sidebar
    # -----------------------------
    st.sidebar.markdown("---")
    st.sidebar.subheader("📊 Estado del Dataset")

    total_registros = len(df)          # total cargado (muestra o full)
    total_original = 2463024           # ⚠️ ajustar al total real de BigQuery
    st.sidebar.write(f"Usando **{format_count(total_registros)}** registros de {format_count(total_original)}")
    st.sidebar.progress(total_registros / total_original)

    # -----------------------------
    # Aplicar filtros
    # -----------------------------
    filtered = df.copy()
    if sex_filter != "Todos":
        filtered = filtered[filtered["Sex"] == sex_filter]
    if equip_filter != "Todos":
        filtered = filtered[filtered["Equipment"] == equip_filter]
    if country_filter != "Todos":
        filtered = filtered[filtered["Country"] == country_filter]
    if age_filter != "Todos":
        filtered = filtered[filtered["AgeClass"] == age_filter]
    filtered = filtered[
        (filtered["Year"] >= year_range[0]) & 
        (filtered["Year"] <= year_range[1]) &
        (filtered["TotalKg"] >= total_range[0]) & 
        (filtered["TotalKg"] <= total_range[1])
    ]

    if filtered.empty:
        st.warning("⚠️ No hay datos con los filtros seleccionados.")
    else:
        # Layout en dos columnas
        col1, col2 = st.columns(2)

        # -----------------------------
        # Gráfico 1: Participación en el tiempo
        # -----------------------------
        with col1:
            st.markdown("### 📊 Participación en el tiempo")
            part = filtered.groupby("Year").agg({
                "NameNormalized":"nunique",
                "TotalKg":"mean"
            }).reset_index()
            fig1 = make_subplots(specs=[[{"secondary_y": True}]])
            fig1.add_trace(go.Bar(x=part["Year"], y=part["NameNormalized"],
                                  name="Atletas únicos", marker_color=CUSTOM_COLORS[0]),
                           secondary_y=False)
            fig1.add_trace(go.Scatter(x=part["Year"], y=part["TotalKg"],
                                      name="Promedio Total (kg)", mode="lines+markers",
                                      line=dict(color=CUSTOM_COLORS[1], width=3)),
                           secondary_y=True)
            fig1.update_yaxes(title_text="Atletas únicos", secondary_y=False)
            fig1.update_yaxes(title_text="Promedio Total (kg)", secondary_y=True)
            fig1.update_layout(title="Participación en el tiempo", **DEFAULT_LAYOUT)
            st.plotly_chart(fig1, use_container_width=True)

        # -----------------------------
        # Gráfico 2: Evolución hombres vs mujeres
        # -----------------------------
        with col2:
            st.markdown("### 👥 Evolución de hombres y mujeres")
            sex_evol = filtered.groupby(["Year","Sex"]).size().reset_index(name="Competencias")
            fig2 = px.line(sex_evol, x="Year", y="Competencias", color="Sex", markers=True,
                           color_discrete_map=SEX_COLORS)
            fig2.update_layout(title="Evolución por Genero", **DEFAULT_LAYOUT)
            st.plotly_chart(fig2, use_container_width=True)


        # -----------------------------
        # Tres gráficos: Evolución de SBD por sexo
        # -----------------------------
        st.markdown("### 🏋️ Evolución por movimiento (Mejores marcas promedio por año)")

        colA, colB, colC = st.columns(3)

        # Squat
        with colA:
            # Squat promedio por año y sexo
            squat_evol = filtered.groupby(["Year","Sex"])["Best3SquatKg"].mean().reset_index()

            # Squat promedio general por año (M+F juntos)
            squat_avg = filtered.groupby("Year")["Best3SquatKg"].mean().reset_index()
            squat_avg["Sex"] = "Promedio"

            # Unir ambos
            squat_all = pd.concat([squat_evol, squat_avg], ignore_index=True)

            # Gráfico
            fig_squat = px.line(
                squat_all, x="Year", y="Best3SquatKg", color="Sex",
                markers=True, color_discrete_map={**SEX_COLORS, "Promedio": "#f39c12"}
            )
            fig_squat.update_layout(title="Squat", yaxis_title="kg", **DEFAULT_LAYOUT)
            st.plotly_chart(fig_squat, use_container_width=True)


        # Bench
        with colB:
            bench_evol = filtered.groupby(["Year","Sex"])["Best3BenchKg"].mean().reset_index()
            bench_avg = filtered.groupby("Year")["Best3BenchKg"].mean().reset_index()
            bench_avg["Sex"] = "Promedio"
            bench_all = pd.concat([bench_evol, bench_avg], ignore_index=True)

            fig_bench = px.line(
                bench_all, x="Year", y="Best3BenchKg", color="Sex",
                markers=True, color_discrete_map={**SEX_COLORS, "Promedio": "#f39c12"}
            )
            fig_bench.update_layout(title="Bench", yaxis_title="kg", **DEFAULT_LAYOUT)
            st.plotly_chart(fig_bench, use_container_width=True)

        # Deadlift
        with colC:
            dl_evol = filtered.groupby(["Year","Sex"])["Best3DeadliftKg"].mean().reset_index()
            dl_avg = filtered.groupby("Year")["Best3DeadliftKg"].mean().reset_index()
            dl_avg["Sex"] = "Promedio"
            dl_all = pd.concat([dl_evol, dl_avg], ignore_index=True)

            fig_dl = px.line(
                dl_all, x="Year", y="Best3DeadliftKg", color="Sex",
                markers=True, color_discrete_map={**SEX_COLORS, "Promedio": "#f39c12"}
            )
            fig_dl.update_layout(title="Deadlift", yaxis_title="kg", **DEFAULT_LAYOUT)
            st.plotly_chart(fig_dl, use_container_width=True)

        # -----------------------------
        # Gráficos circulares de distribución
        # -----------------------------
        st.markdown("### 🍩 Distribución de atletas")

        col_p1, col_p2 = st.columns(2)

        with col_p1:
            if "Sex" in filtered.columns:
                sex_counts = filtered["Sex"].value_counts().reset_index()
                sex_counts.columns = ["Sexo","Atletas"]
                fig_pie1 = px.pie(sex_counts, values="Atletas", names="Sexo",
                                  color="Sexo", color_discrete_map=SEX_COLORS,
                                  hole=0.4, title="Distribución por sexo")
                fig_pie1.update_layout(**DEFAULT_LAYOUT)
                st.plotly_chart(fig_pie1, use_container_width=True)

        with col_p2:
            if "Equipment" in filtered.columns:
                eq_counts = filtered["Equipment"].value_counts().reset_index()
                eq_counts.columns = ["Equipamiento","Atletas"]
                fig_pie2 = px.pie(eq_counts, values="Atletas", names="Equipamiento",
                                  hole=0.4, title="Distribución por equipamiento",
                                  color_discrete_sequence=CUSTOM_COLORS)
                fig_pie2.update_layout(**DEFAULT_LAYOUT)
                st.plotly_chart(fig_pie2, use_container_width=True)
# Fin tab1

# -----------------------------
# 2) Geográfico
# -----------------------------
with tab2:
    st.subheader("🌍 Análisis Geográfico")

    if filtered.empty:
        st.warning("⚠️ No hay datos con los filtros seleccionados.")
    else:
        # Selector de métrica
        metric_option = st.selectbox(
            "Métrica a visualizar en el mapa",
            ["TotalKg", "Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg"],
            index=0
        )

        # Agregación por país
        geo_df = filtered.groupby("Country").agg(
            atletas_totales=("NameNormalized","nunique"),
            atletas_mujeres=("Sex", lambda x: (x=="F").sum()),
            atletas_hombres=("Sex", lambda x: (x=="M").sum()),
            promedio_total=("TotalKg","mean"),
            promedio_squat=("Best3SquatKg","mean"),
            promedio_bench=("Best3BenchKg","mean"),
            promedio_deadlift=("Best3DeadliftKg","mean"),
            promedio_dots=("Dots","mean"),
            promedio_edad=("AgeClass", lambda x: pd.to_numeric(x, errors="coerce").mean())
        ).reset_index()

        geo_df = geo_df.dropna(subset=["Country"])

        if geo_df.empty:
            st.warning("⚠️ No hay datos de países con esta métrica.")
        else:
            # Mapa con hover enriquecido
            fig_map = px.choropleth(
                geo_df,
                locations="Country",
                locationmode="country names",
                color=metric_option if metric_option in geo_df.columns else "promedio_total",
                color_continuous_scale="Viridis",
                projection="natural earth",
                hover_data={
                    "atletas_totales": True,
                    "atletas_mujeres": True,
                    "atletas_hombres": True,
                    "promedio_total": ":.1f",
                    "promedio_squat": ":.1f",
                    "promedio_bench": ":.1f",
                    "promedio_deadlift": ":.1f",
                    "promedio_dots": ":.1f",
                    "promedio_edad": ":.1f"
                },
                title=f"Promedio de {metric_option} por País"
            )
            fig_map.update_layout(**DEFAULT_LAYOUT)
            st.plotly_chart(fig_map, use_container_width=True)


# -----------------------------
# 3) Análisis por Categorías
# -----------------------------
with tab3:
    st.subheader("📊 Análisis por Categorías")

    # Aplicar filtros globales
    filtered_df = df.copy()

    if sex_filter != "Todos":
        filtered_df = filtered_df[filtered_df["Sex"] == sex_filter]
    if equip_filter != "Todos":
        filtered_df = filtered_df[filtered_df["Equipment"] == equip_filter]
    if country_filter != "Todos":
        filtered_df = filtered_df[filtered_df["Country"] == country_filter]
    if age_filter != "Todos":
        filtered_df = filtered_df[filtered_df["AgeClass"] == age_filter]

    filtered_df = filtered_df[
        (filtered_df["Year"] >= year_range[0]) &
        (filtered_df["Year"] <= year_range[1])
    ]

    filtered_df = filtered_df[
        (filtered_df["TotalKg"] >= total_range[0]) &
        (filtered_df["TotalKg"] <= total_range[1])
    ]

    # Selección de movimiento global para esta pestaña
    lift_option = st.selectbox(
        "Selecciona el movimiento",
        ["Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg", "TotalKg"],
        index=3,
        key="cat_global"
    )

    col1, col2 = st.columns(2)

    # =========================
    # Columna 1 - Categorías de Edad
    # =========================
    with col1:
        st.markdown("### ⏳ Rendimiento por Categoría de Edad")

        if "AgeClass" in filtered_df.columns:
            age_df = filtered_df[["AgeClass", lift_option]].dropna()
            if not age_df.empty:
                fig_age = px.box(
                    age_df,
                    x="AgeClass",
                    y=lift_option,
                    color_discrete_sequence=CUSTOM_COLORS
                )
                fig_age.update_layout(**DEFAULT_LAYOUT)
                st.plotly_chart(fig_age, use_container_width=True)
            else:
                st.warning("⚠️ No hay datos suficientes para categorías de edad.")

    # =========================
    # Columna 2 - Peso Corporal
    # =========================
    with col2:
        st.markdown("### ⚖️ Rendimiento según Peso Corporal")

        if "BodyweightKg" in filtered_df.columns:
            bw_df = filtered_df[["BodyweightKg", lift_option, "Sex"]].dropna()
            if not bw_df.empty:
                fig_bw = px.scatter(
                    bw_df,
                    x="BodyweightKg",
                    y=lift_option,
                    color="Sex",
                    opacity=0.5,
                    color_discrete_map=SEX_COLORS
                )

                # Línea de promedio por bins de peso
                bw_df["Peso_bin"] = pd.cut(bw_df["BodyweightKg"], bins=12)
                mean_line = bw_df.groupby("Peso_bin")[lift_option].mean().reset_index()
                mean_line["Peso_bin_mid"] = mean_line["Peso_bin"].apply(lambda x: x.mid)

                fig_bw.add_scatter(
                    x=mean_line["Peso_bin_mid"],
                    y=mean_line[lift_option],
                    mode="lines+markers",
                    line=dict(color="gray", dash="dot"),
                    name="Promedio por rango"
                )

                fig_bw.update_layout(**DEFAULT_LAYOUT)
                st.plotly_chart(fig_bw, use_container_width=True)
            else:
                st.warning("⚠️ No hay datos suficientes para categorías de peso corporal.")

# -----------------------------
# 4) Ficha por Atleta
# -----------------------------
with tab4:
    st.subheader("📑 Ficha del Atleta")

    # Filtro de años (independiente del sidebar)
    year_min, year_max = int(df["Year"].min()), int(df["Year"].max())
    year_range = st.slider("Rango de años", year_min, year_max, (year_min, year_max), key="year_ficha")

    # Lista de atletas
    athletes = sorted(df["NameNormalized"].dropna().unique().tolist())
    who = st.selectbox("Selecciona un atleta", athletes, index=0, key="ficha_atleta")

    me = df[(df["NameNormalized"] == who) &
            (df["Year"] >= year_range[0]) &
            (df["Year"] <= year_range[1])].copy()

    if me.empty:
        st.warning("⚠️ No hay datos para este atleta en el rango seleccionado.")
    else:
        # Info básica
        nombre = who
        pais = me["Country"].mode().iloc[0] if "Country" in me.columns else "Desconocido"
        st.markdown(f"### 👤 {nombre}")
        st.markdown(f"**País:** {pais}")

        # -----------------------------
        # Tarjetas de PRs
        # -----------------------------
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("PR Squat", f"{me['Best3SquatKg'].max():.1f} kg")
        with col2:
            st.metric("PR Bench", f"{me['Best3BenchKg'].max():.1f} kg")
        with col3:
            st.metric("PR Deadlift", f"{me['Best3DeadliftKg'].max():.1f} kg")
        with col4:
            st.metric("Mejor Total", f"{me['TotalKg'].max():.1f} kg")

        # -----------------------------
        # Evolución anual de cada movimiento con proyección
        # -----------------------------
        colA, colB, colC = st.columns(3)

        # Función para graficar evolución + proyección
        def plot_with_projection(me, col, title, color):
            evol = me.groupby("Year")[col].mean().reset_index()

            fig = px.line(evol, x="Year", y=col, markers=True, title=title)
            fig.update_traces(line=dict(color=color, width=3))

            # proyección lineal
            d = me[["Date", col]].dropna()
            if len(d) >= 3:
                x = d["Date"].map(datetime.toordinal)
                y = d[col].astype(float)
                coef = np.polyfit(x, y, 1)
                fut = d["Date"].max() + pd.DateOffset(months=6)
                y_fut = coef[0]*fut.toordinal() + coef[1]

                fig.add_scatter(
                    x=[d["Date"].max().year, fut.year],
                    y=[d[col].iloc[-1], y_fut],
                    mode="lines+markers",
                    line=dict(color="gray", dash="dash"),
                    name="Proyección 6m"
                )

            fig.update_layout(**DEFAULT_LAYOUT)
            return fig

        with colA:
            st.plotly_chart(plot_with_projection(me, "Best3SquatKg", "Evolución Squat (kg)", CUSTOM_COLORS[0]),
                            use_container_width=True)

        with colB:
            st.plotly_chart(plot_with_projection(me, "Best3BenchKg", "Evolución Bench (kg)", CUSTOM_COLORS[1]),
                            use_container_width=True)

        with colC:
            st.plotly_chart(plot_with_projection(me, "Best3DeadliftKg", "Evolución Deadlift (kg)", CUSTOM_COLORS[2]),
                            use_container_width=True)

        # -----------------------------
        # Tabla de competencias
        # -----------------------------
        st.markdown("### 📋 Competencias del Atleta")
        cols = ["Year","AgeClass","Best3SquatKg","Best3BenchKg","Best3DeadliftKg","TotalKg"]
        table = me[cols].sort_values("Year", ascending=False)
        table = table.rename(columns={
            "Year": "Año",
            "AgeClass": "Categoría Edad",
            "Best3SquatKg": "Squat (kg)",
            "Best3BenchKg": "Bench (kg)",
            "Best3DeadliftKg": "Deadlift (kg)",
            "TotalKg": "Total (kg)"
        })
        st.dataframe(table, use_container_width=True)

        # -----------------------------
        # Proyección a 6 meses (barras comparativas)
        # -----------------------------
        proj = []
        if "Date" in me.columns:
            for lift, col in [("Squat","Best3SquatKg"),
                              ("Bench","Best3BenchKg"),
                              ("Deadlift","Best3DeadliftKg"),
                              ("Total","TotalKg")]:
                d = me[["Date",col]].dropna()
                if len(d) >= 3:
                    x = d["Date"].map(datetime.toordinal)
                    y = d[col].astype(float)
                    coef = np.polyfit(x,y,1)
                    fut = d["Date"].max() + pd.DateOffset(months=6)
                    y_fut = coef[0]*fut.toordinal() + coef[1]
                    proj.append([lift, d[col].max(), max(y_fut, d[col].max())])

        if proj:
            pdf = pd.DataFrame(proj, columns=["Levantamiento","PR actual","Proyección 6m"])
            st.markdown("### 🔮 Proyección de Rendimiento a 6 meses")
            fig_proj = px.bar(pdf, x="Levantamiento", y=["PR actual","Proyección 6m"], barmode="group",
                              color_discrete_sequence=CUSTOM_COLORS)
            fig_proj.update_layout(**DEFAULT_LAYOUT)
            st.plotly_chart(fig_proj, use_container_width=True)
            st.dataframe(pdf, hide_index=True, use_container_width=True)

# -----------------------------
# 5) Simulador de Nivel
# -----------------------------
with tab5:
    st.subheader("🧮 Simulador de Nivel")
    st.markdown("Introduce tus datos para comparar tu nivel con atletas reales en el dataset.")

    # =========================
    # Formulario de entrada
    # =========================
    col1, col2, col3 = st.columns(3)
    with col1:
        sex_in = st.selectbox("Sexo", ["M", "F"])
        equip_in = st.selectbox("Equipamiento", df["Equipment"].dropna().unique())
        country_in = st.selectbox("País", ["Todos"] + sorted(df["Country"].dropna().unique()))
    with col2:
        age_in = st.number_input("Edad", 15, 90, 25)
        bw_in = st.number_input("Peso corporal (kg)", 30.0, 200.0, 80.0, step=0.5)
    with col3:
        squat_in = st.number_input("Mejor Squat (kg)", 0.0, 500.0, 150.0, step=2.5)
        bench_in = st.number_input("Mejor Bench (kg)", 0.0, 400.0, 100.0, step=2.5)
        dead_in = st.number_input("Mejor Deadlift (kg)", 0.0, 500.0, 180.0, step=2.5)

    total_in = squat_in + bench_in + dead_in
    st.metric("Tu Total (kg)", f"{total_in:.1f}")

    # =========================
    # Filtrar dataset comparable
    # =========================
    comp_df = df.copy()
    comp_df = comp_df[(comp_df["Sex"] == sex_in)]
    comp_df = comp_df[(comp_df["BodyweightKg"].between(bw_in - 5, bw_in + 5))]
    comp_df = comp_df.dropna(subset=["TotalKg"])

    if not comp_df.empty:
        # Calcular percentil
        rank = (comp_df["TotalKg"] < total_in).sum()
        percentil = rank / len(comp_df) * 100

        # Atleta superior más cercano
        superior = comp_df[comp_df["TotalKg"] > total_in].sort_values("TotalKg").head(1)

        st.markdown(f"📊 Estás en el **percentil {percentil:.1f}%** de tu categoría.")
        if not superior.empty:
            falta = superior["TotalKg"].iloc[0] - total_in
            st.markdown(f"⬆️ Te faltan **{falta:.1f} kg** para alcanzar al siguiente atleta en tu categoría.")

        # =========================
        # Gauge (percentil)
        # =========================
        st.markdown("### 🎯 Tu posición en la categoría")
        st.info("Este velocímetro muestra en qué **percentil** estás comparado con todos los atletas en tu categoría. "
                "Percentil 50 = promedio. Percentil 90 = dentro del 10% superior.")

        fig_g = go.Figure(go.Indicator(
            mode="gauge+number",
            value=percentil,
            title={"text": "Tu Nivel Percentil en la Categoría", "font": {"size": 18, "color": "#C6D92D"}},
            number={"suffix": " %", "font": {"size": 36}},
            gauge={'axis': {'range': [0, 100]},
                'bar': {'color': "#C6D92D"},
                'steps': [
                    {'range': [0, 25], 'color': '#6E6E6E'},
                    {'range': [25, 50], 'color': '#2B2B2B'},
                    {'range': [50, 75], 'color': '#00C2C7'},
                    {'range': [75, 100], 'color': '#C6D92D'}
                ]}
        ))

        # 🔑 Quitar título "undefined"
        fig_g.update_layout(title=None, **DEFAULT_LAYOUT)

        st.plotly_chart(fig_g, use_container_width=True)


        # =========================
        # Histograma
        # =========================
        st.markdown("### 📊 Distribución de Totales en tu Categoría")
        st.info("Este gráfico muestra cómo se distribuyen los Totales de todos los atletas en tu categoría. "
                "La línea roja indica tu posición actual.")

        fig_hist = px.histogram(comp_df, x="TotalKg", nbins=30,
                                color_discrete_sequence=CUSTOM_COLORS,
                                title="Distribución de Totales (kg)")
        fig_hist.add_vline(x=total_in, line_dash="dash", line_color="red",
                           annotation_text="Tu Total", annotation_position="top")
        fig_hist.update_layout(**DEFAULT_LAYOUT)
        st.plotly_chart(fig_hist, use_container_width=True)

        # =========================
        # Comparativa de Totales
        # =========================
        if not superior.empty:
            st.markdown("### 🏋️ Comparativa de Rendimiento")
            st.info("Comparamos tu Total con el **promedio de tu categoría** y con el **atleta superior más cercano**.")

            comp_vals = {
                "Tú": total_in,
                "Promedio Cat": comp_df["TotalKg"].mean(),
                "Superior cercano": superior["TotalKg"].iloc[0]
            }
            fig_bar = px.bar(x=list(comp_vals.keys()), y=list(comp_vals.values()),
                             color=list(comp_vals.keys()),
                             color_discrete_sequence=CUSTOM_COLORS,
                             title="Comparativa de Totales (kg)")
            fig_bar.update_layout(**DEFAULT_LAYOUT)
            st.plotly_chart(fig_bar, use_container_width=True)

    else:
        st.warning("⚠️ No se encontraron atletas comparables en el dataset con tus parámetros.")

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.markdown(f"**Datos:** OpenPowerlifting (BigQuery GCP) | Última actualización: {datetime.now().strftime('%d/%m/%Y %H:%M')}")