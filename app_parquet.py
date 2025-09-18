import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from pathlib import Path
from datetime import datetime
import streamlit.components.v1 as components

# -----------------------------
# Configuración de página
# -----------------------------
st.set_page_config(
    page_title="Powerlifting Analytics Dashboard 1.2",
    page_icon="🏋️‍♂️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------
# Helpers de formato (ES)
# -----------------------------
def format_number(num):
    """Formatear números con punto para miles y coma para decimales"""
    if pd.isna(num):
        return "N/A"
    if isinstance(num, (int, float, np.floating, np.integer)):
        if num >= 1000:
            return f"{num:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")
        else:
            return f"{num:.1f}".replace(".", ",")
    return str(num)

def format_kg(num):
    """Formatear peso con kg al final"""
    if pd.isna(num):
        return "N/A"
    return f"{format_number(num)} kg"

def format_count(num):
    """Formatear conteos"""
    try:
        n = int(num)
    except Exception:
        return "0"
    if n >= 1000:
        return f"{n:,}".replace(",", ".")
    return str(n)

def _switch_to_tab(label_contains: str):
    """Hack para volver a una pestaña específica luego de un submit."""
    components.html(f"""
    <script>
      const tryClick = () => {{
        const tabs = Array.from(window.parent.document.querySelectorAll('div[role="tablist"] button'));
        const target = tabs.find(el => el.textContent.trim().includes("{label_contains}"));
        if (target) target.click();
      }};
      setTimeout(tryClick, 0);
      setTimeout(tryClick, 60);
      setTimeout(tryClick, 150);
    </script>
    """, height=0)

# -----------------------------
# CSS personalizado
# -----------------------------
st.markdown("""
<style>
    .main-header {
        font-size: 3.5rem;
        font-weight: 800;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 15px;
        box-shadow: 0 8px 16px rgba(0,0,0,0.1);
        color: white;
        text-align: center;
    }
    .filter-section {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        margin-bottom: 1rem;
    }
    .apply-button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 2rem;
        border-radius: 25px;
        font-weight: bold;
        cursor: pointer;
        width: 100%;
        margin-top: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Carga de datos
# -----------------------------
@st.cache_data
def load_data():
    """Cargar datos procesados"""
    data_path = Path("data/processed/powerlifting_clean.parquet")
    if not data_path.exists():
        st.error("Datos no encontrados. Ejecuta primero el notebook de procesamiento.")
        return pd.DataFrame()
    df = pd.read_parquet(data_path)  # 👈 Carga rápida y optimizada
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
    return df


df = load_data()
if df.empty:
    st.stop()

# -----------------------------
# Session state para filtros
# -----------------------------
if 'filters_applied' not in st.session_state:
    st.session_state.filters_applied = False
if 'current_filters' not in st.session_state:
    st.session_state.current_filters = {}

# -----------------------------
# HEADER
# -----------------------------
st.markdown('<h1 class="main-header">Powerlifting Analytics Dashboard</h1>', unsafe_allow_html=True)
st.markdown("**Análisis global de competencias de powerlifting basado en datos de OpenPowerlifting**")
st.markdown("---")

# -----------------------------
# SIDEBAR - FILTROS
# -----------------------------
st.sidebar.markdown('<div class="filter-section">', unsafe_allow_html=True)
st.sidebar.markdown("### 🎛️ Configurar Filtros")

sexes = ['Todos'] + (sorted(df['Sex'].dropna().astype(str).unique().tolist()) if 'Sex' in df.columns else [])
temp_sex = st.sidebar.selectbox("👥 Sexo", sexes, key="temp_sex")

equipments = ['Todos'] + (sorted(df['Equipment'].dropna().astype(str).unique().tolist()) if 'Equipment' in df.columns else [])
temp_equipment = st.sidebar.selectbox("🏋️ Equipamiento", equipments, key="temp_equipment")

countries_unique = sorted([c for c in (df['Country'].dropna().astype(str).unique().tolist() if 'Country' in df.columns else []) if pd.notna(c)])
countries = ['Todos'] + countries_unique
temp_country = st.sidebar.selectbox("🌍 País", countries, key="temp_country")

min_year = int(df['Year'].min()) if 'Year' in df.columns else 2000
max_year = int(df['Year'].max()) if 'Year' in df.columns else datetime.now().year
temp_year_range = st.sidebar.slider("📅 Rango de años", min_year, max_year, (2010, max_year), key="temp_year_range")

age_classes_unique = sorted([ac for ac in (df['AgeClass'].dropna().astype(str).unique().tolist() if 'AgeClass' in df.columns else []) if pd.notna(ac)])
age_classes = ['Todos'] + age_classes_unique
temp_age_class = st.sidebar.selectbox("🎂 Categoría de edad", age_classes, key="temp_age_class")

total_min = float(df['TotalKg'].min()) if 'TotalKg' in df.columns else 0.0
total_max = float(df['TotalKg'].max()) if 'TotalKg' in df.columns else 1000.0
temp_total_range = st.sidebar.slider(
    "💪 Rango de totales (kg)",
    float(total_min), float(total_max),
    (max(0.0, float(total_min)), min(800.0, float(total_max))),
    key="temp_total_range"
)

# Botón aplicar filtros
if st.sidebar.button("🔄 Aplicar Filtros", key="apply_filters"):
    st.session_state.current_filters = {
        'sex': temp_sex,
        'equipment': temp_equipment,
        'country': temp_country,
        'year_range': temp_year_range,
        'age_class': temp_age_class,
        'total_range': temp_total_range
    }
    st.session_state.filters_applied = True
    st.rerun()
st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Filtros activos o defaults
if st.session_state.filters_applied:
    filters = st.session_state.current_filters
    st.sidebar.markdown("### 📋 Filtros Activos")
    st.sidebar.write(f"**Sexo:** {filters['sex']}")
    st.sidebar.write(f"**Equipamiento:** {filters['equipment']}")
    st.sidebar.write(f"**País:** {filters['country']}")
    st.sidebar.write(f"**Años:** {filters['year_range'][0]} - {filters['year_range'][1]}")
    st.sidebar.write(f"**Edad:** {filters['age_class']}")
    st.sidebar.write(f"**Totales:** {format_kg(filters['total_range'][0])} - {format_kg(filters['total_range'][1])}")
else:
    filters = {
        'sex': 'Todos',
        'equipment': 'Todos',
        'country': 'Todos',
        'year_range': (2010, max_year),
        'age_class': 'Todos',
        'total_range': (float(df['TotalKg'].min()), float(df['TotalKg'].max()))

    }

# -----------------------------
# Aplicar filtros a los datos
# -----------------------------
filtered_df = df.copy()
if 'Sex' in filtered_df.columns and filters['sex'] != 'Todos':
    filtered_df = filtered_df[filtered_df['Sex'].astype(str) == str(filters['sex'])]
if 'Equipment' in filtered_df.columns and filters['equipment'] != 'Todos':
    filtered_df = filtered_df[filtered_df['Equipment'].astype(str) == str(filters['equipment'])]
if 'Country' in filtered_df.columns and filters['country'] != 'Todos':
    filtered_df = filtered_df[filtered_df['Country'].astype(str) == str(filters['country'])]
if 'AgeClass' in filtered_df.columns and filters['age_class'] != 'Todos':
    filtered_df = filtered_df[filtered_df['AgeClass'].astype(str) == str(filters['age_class'])]
if 'Year' in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df['Year'] >= filters['year_range'][0]) & (filtered_df['Year'] <= filters['year_range'][1])]
if 'TotalKg' in filtered_df.columns:
    filtered_df = filtered_df[(filtered_df['TotalKg'] >= filters['total_range'][0]) & (filtered_df['TotalKg'] <= filters['total_range'][1])]

# -----------------------------
# Métricas principales
# -----------------------------
st.markdown("### 📊 Métricas Principales")
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    st.metric("Total Registros", format_count(len(filtered_df)))
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    unique_athletes = filtered_df['NameNormalized'].nunique() if 'NameNormalized' in filtered_df.columns else 0
    st.metric("Atletas Únicos", format_count(unique_athletes))
    st.markdown('</div>', unsafe_allow_html=True)

with col3:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    countries_n = filtered_df['Country'].nunique() if 'Country' in filtered_df.columns else 0
    st.metric("Países", str(countries_n))
    st.markdown('</div>', unsafe_allow_html=True)

with col4:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    total_mean = filtered_df['TotalKg'].mean() if 'TotalKg' in filtered_df.columns and not filtered_df['TotalKg'].empty else np.nan
    st.metric("Total Promedio", format_kg(total_mean))
    st.markdown('</div>', unsafe_allow_html=True)

with col5:
    st.markdown('<div class="metric-container">', unsafe_allow_html=True)
    total_max_v = filtered_df['TotalKg'].max() if 'TotalKg' in filtered_df.columns and not filtered_df['TotalKg'].empty else np.nan
    st.metric("Total Máximo", format_kg(total_max_v))
    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")

# -----------------------------
# Tabs principales (con Compararme)
# -----------------------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Tendencias", "🌍 Geografía", "⚖️ Categorías", "🏆 Elite", "🔬 Compararme"])

# -----------------------------
# Tab 1: Tendencias
# -----------------------------
with tab1:
    st.markdown("### Evolución Temporal del Powerlifting")
    col1, col2 = st.columns(2)

    with col1:
        if 'Year' in filtered_df.columns and 'TotalKg' in filtered_df.columns and 'NameNormalized' in filtered_df.columns:
            yearly_stats = filtered_df.groupby('Year').agg({
                'TotalKg': ['count', 'mean', 'max'],
                'NameNormalized': 'nunique'
            }).round(1)
            yearly_stats.columns = ['Competencias', 'Total_Promedio', 'Total_Maximo', 'Atletas_Unicos']
            yearly_stats = yearly_stats.reset_index()

            fig_evolution = make_subplots(specs=[[{"secondary_y": True}]])
            hover_template_line = '<b>Año:</b> %{x}<br><b>Total Promedio:</b> %{y:.1f} kg<extra></extra>'
            hover_template_bar = '<b>Año:</b> %{x}<br><b>Competencias:</b> %{y:,.0f}<extra></extra>'

            fig_evolution.add_trace(
                go.Scatter(
                    x=yearly_stats['Year'],
                    y=yearly_stats['Total_Promedio'],
                    mode='lines+markers',
                    name='Total Promedio',
                    line=dict(color='#667eea', width=3),
                    hovertemplate=hover_template_line
                ),
                secondary_y=False
            )

            fig_evolution.add_trace(
                go.Bar(
                    x=yearly_stats['Year'],
                    y=yearly_stats['Competencias'],
                    name='Competencias',
                    opacity=0.6,
                    marker_color='#764ba2',
                    hovertemplate=hover_template_bar
                ),
                secondary_y=True
            )

            fig_evolution.update_yaxes(title_text="Total Promedio (kg)", secondary_y=False)
            fig_evolution.update_yaxes(title_text="Número de Competencias", secondary_y=True)
            fig_evolution.update_layout(title="Evolución de Totales y Participación", height=400)

            st.plotly_chart(fig_evolution, use_container_width=True)
        else:
            st.info("Faltan columnas necesarias para la evolución anual.")

    with col2:
        if 'Date' in filtered_df.columns:
            monthly_activity = filtered_df.groupby(filtered_df['Date'].dt.month).size()
            months = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
            yvals = [int(monthly_activity.get(m, 0)) for m in range(1, 13)]

            fig_monthly = go.Figure(data=[
                go.Bar(
                    x=months,
                    y=yvals,
                    marker_color='rgba(102, 126, 234, 0.8)',
                    text=[format_count(v) for v in yvals],
                    textposition='auto',
                    hovertemplate='<b>Mes:</b> %{x}<br><b>Competencias:</b> %{y:,.0f}<extra></extra>'
                )
            ])
            fig_monthly.update_layout(
                title="Distribución de Competencias por Mes",
                height=400,
                xaxis_title="Mes",
                yaxis_title="Número de Competencias"
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
        else:
            st.info("No hay columna 'Date' para la distribución mensual.")

# -----------------------------
# Tab 2: Geografía (Mapa Top 1 por país y sexo)
# -----------------------------
with tab2:
    st.markdown("### Mapa interactivo: Top 1 por país y sexo")
    needed = {'Country', 'Sex', 'TotalKg'}
    if not needed.issubset(set(filtered_df.columns)):
        st.info("Faltan columnas mínimas para el mapa (Country, Sex, TotalKg).")
    else:
        g = filtered_df.copy()
        g = g[g['Country'].notna() & g['Sex'].notna() & g['TotalKg'].notna()]
        if g.empty:
            st.info("No hay datos suficientes para el mapa con los filtros actuales.")
        else:
            if 'NameNormalized' not in g.columns:
                g['NameNormalized'] = '—'
            if 'Date' in g.columns:
                g['Date'] = pd.to_datetime(g['Date'], errors='coerce')
                g['YearStr'] = g['Date'].dt.year.fillna(0).astype(int).astype(str).replace({'0': '—'})
            else:
                g['YearStr'] = '—'

            def top_by_sex(df_, sex):
                d = df_[df_['Sex'].astype(str) == sex]
                if d.empty:
                    return pd.DataFrame(columns=['Country','NameTop','TotalTop','YearTop'])
                idx = d.groupby('Country', observed=True)['TotalKg'].idxmax()
                t = d.loc[idx, ['Country','NameNormalized','TotalKg','YearStr']].copy()
                t.columns = ['Country','NameTop','TotalTop','YearTop']
                return t

            top_m = top_by_sex(g, 'M')
            top_f = top_by_sex(g, 'F')

            countries_df = pd.DataFrame({'Country': sorted(g['Country'].astype(str).unique().tolist())})
            # primer merge (M)
            m = countries_df.merge(top_m, on='Country', how='left')
            m = m.merge(top_f, on='Country', how='left', suffixes=('M','F'))

            # Columnas esperadas tras merge:
            # NameTopM, TotalTopM, YearTopM, NameTopF, TotalTopF, YearTopF
            # Métrica para color: mejor total del país en cualquiera de los dos
            m['BestAny'] = pd.to_numeric(
                np.nanmax(
                    np.vstack([
                        pd.to_numeric(m.get('TotalTopM', pd.Series(index=m.index)), errors='coerce'),
                        pd.to_numeric(m.get('TotalTopF', pd.Series(index=m.index)), errors='coerce')
                    ]),
                    axis=0
                ),
                errors='coerce'
            )
            m['BestAny'] = m['BestAny'].fillna(0)

            def safe_fmt(v): 
                return format_kg(v) if pd.notna(v) else "—"
            def safe_str(v): 
                return v if (isinstance(v, str) and v.strip()!='') else "—"

            m['M_info'] = m.apply(lambda r: f"{safe_str(r.get('NameTopM'))} — {safe_fmt(r.get('TotalTopM'))} ({safe_str(r.get('YearTopM'))})", axis=1)
            m['F_info'] = m.apply(lambda r: f"{safe_str(r.get('NameTopF'))} — {safe_fmt(r.get('TotalTopF'))} ({safe_str(r.get('YearTopF'))})", axis=1)
            m['Count']  = g.groupby('Country').size().reindex(m['Country']).fillna(0).astype(int).values

            unique_c = m['Country'].dropna().astype(str).unique()
            use_iso3 = len(unique_c) > 0 and all(len(c)==3 and c.isupper() for c in unique_c)
            locationmode = 'country names'

            fig_map = go.Figure(data=go.Choropleth(
                locations=m['Country'],
                z=m['BestAny'],
                locationmode=locationmode,
                colorscale='Blues',
                colorbar_title='Mejor total (kg)',
                customdata=np.stack([m['M_info'], m['F_info'], m['Count']], axis=-1),
                hovertemplate="<b>%{location}</b><br>" +
                              "👨 TOP M: %{customdata[0]}<br>" +
                              "👩 TOP F: %{customdata[1]}<br>" +
                              "Registros: %{customdata[2]:,.0f}<extra></extra>"
            ))
            fig_map.update_layout(
                height=520,
                margin=dict(l=0, r=0, t=40, b=0),
                title="Top 1 por país (M/F) — pasa el mouse para ver detalles"
            )
            st.plotly_chart(fig_map, use_container_width=True)

# -----------------------------
# Tab 3: Categorías (distribuciones)
# -----------------------------
with tab3:
    st.markdown("### Categorías y distribuciones")
    need = {'TotalKg', 'Equipment', 'AgeClass', 'Sex'}
    if not need.issubset(set(filtered_df.columns)):
        st.info("Faltan columnas mínimas (TotalKg, Equipment, AgeClass, Sex).")
    else:
        dfc = filtered_df.copy()
        dfc = dfc[dfc['TotalKg'].notna()]
        if dfc.empty:
            st.info("Sin datos para mostrar en esta pestaña con los filtros actuales.")
        else:
            c1, c2 = st.columns([1.4, 1])
            with c2:
                sex_pick = st.radio("Sexo", options=['Todos','M','F'], horizontal=True)
            if sex_pick != 'Todos':
                dfc = dfc[dfc['Sex'].astype(str) == sex_pick]

            left, right = st.columns([1.25, 1])
            with left:
                st.markdown("#### Promedio de Total por Equipamiento × Edad (Top categorías)")
                top_equip = dfc['Equipment'].value_counts().head(10).index
                top_age   = dfc['AgeClass'].value_counts().head(10).index
                dheat = dfc[dfc['Equipment'].isin(top_equip) & dfc['AgeClass'].isin(top_age)]
                if dheat.empty:
                    st.info("No hay suficientes datos para el heatmap con los filtros actuales.")
                else:
                    pivot = dheat.pivot_table(values='TotalKg', index='Equipment', columns='AgeClass', aggfunc='mean').round(1)
                    fig_heat = px.imshow(
                        pivot,
                        aspect='auto',
                        labels=dict(color="Total Promedio (kg)"),
                    )
                    fig_heat.update_layout(height=520, margin=dict(l=10,r=10,t=40,b=10))
                    st.plotly_chart(fig_heat, use_container_width=True)

            with right:
                st.markdown("#### Distribución por Edad (Boxplot)")
                top_age2 = dfc['AgeClass'].value_counts().head(8).index
                dbox = dfc[dfc['AgeClass'].isin(top_age2)]
                if dbox.empty:
                    st.info("Sin datos suficientes para boxplot.")
                else:
                    fig_box = px.box(
                        dbox,
                        x='AgeClass',
                        y='TotalKg',
                        color='Sex',
                        points=False,
                        labels={'AgeClass':'Categoría de Edad','TotalKg':'Total (kg)'}
                    )
                    fig_box.update_layout(height=520, margin=dict(l=10,r=10,t=40,b=10))
                    st.plotly_chart(fig_box, use_container_width=True)


# -----------------------------
# Tab 4: Elite
# -----------------------------
with tab4:
    st.markdown("### Atletas Elite")
    needed_cols = ['TotalKg', 'NameNormalized', 'BodyweightKg', 'Equipment', 'Country', 'Date']
    if all(c in filtered_df.columns for c in needed_cols):
        top_athletes = filtered_df.nlargest(20, 'TotalKg').copy()

        display_data = top_athletes[['NameNormalized', 'TotalKg', 'BodyweightKg', 'Equipment', 'Country', 'Date']].copy()
        display_data['TotalKg_formatted'] = display_data['TotalKg'].apply(format_kg)
        display_data['BodyweightKg_formatted'] = display_data['BodyweightKg'].apply(format_kg)
        display_data['Date_formatted'] = pd.to_datetime(display_data['Date'], errors='coerce').dt.strftime('%d/%m/%Y')

        final_display = display_data[['NameNormalized', 'TotalKg_formatted', 'BodyweightKg_formatted', 'Equipment', 'Country', 'Date_formatted']].copy()
        final_display.columns = ['Atleta', 'Total', 'Peso Corporal', 'Equipamiento', 'País', 'Fecha']

        col1_elite, col2_elite = st.columns([2, 1])

        with col1_elite:
            st.markdown("#### Top 20 Totales")
            st.dataframe(final_display.reset_index(drop=True), use_container_width=True, height=400)

        with col2_elite:
            top_10 = top_athletes.head(10)
            fig_top = px.bar(
                x=top_10['TotalKg'],
                y=top_10['NameNormalized'],
                orientation='h',
                title="Top 10 Atletas",
                color=top_10['TotalKg'],
                color_continuous_scale="reds"
            )
            fig_top.update_layout(height=400, yaxis={'categoryorder': 'total ascending'})
            fig_top.update_traces(hovertemplate='<b>%{y}</b><br>Total: %{x:.1f} kg<extra></extra>')
            st.plotly_chart(fig_top, use_container_width=True)

        # Nueva sección Elite por categoría
        st.markdown("#### 🏆 Mejores por Categoría de Edad y Peso")
        group_cols = ['AgeClass', 'WeightClass']
        if all(col in filtered_df.columns for col in group_cols):
            elite_df = filtered_df[
                filtered_df['AgeClass'].notna() &
                filtered_df['WeightClass'].notna() &
                filtered_df['TotalKg'].notna()
            ].copy()
            idx = elite_df.groupby(group_cols)['TotalKg'].idxmax()
            top_by_cat = elite_df.loc[idx, ['AgeClass', 'WeightClass', 'NameNormalized', 'TotalKg', 'Country', 'Date']]

            top_by_cat['TotalKg'] = top_by_cat['TotalKg'].apply(format_kg)
            top_by_cat['Date'] = pd.to_datetime(top_by_cat['Date'], errors='coerce').dt.strftime('%d/%m/%Y')
            top_by_cat = top_by_cat.rename(columns={
                'AgeClass': 'Edad',
                'WeightClass': 'Peso',
                'NameNormalized': 'Atleta',
                'TotalKg': 'Total',
                'Country': 'País',
                'Date': 'Fecha'
            })

            st.dataframe(top_by_cat.reset_index(drop=True), use_container_width=True, height=600)
        else:
            st.info("Faltan columnas 'AgeClass' o 'WeightClass' para mostrar los mejores por categoría.")
    else:
        st.info("Faltan columnas para mostrar el ranking elite.")

...

# -----------------------------
# Tab 5: Compararme
# -----------------------------
with tab5:
    st.markdown("### 🔬 Análisis Personal y Predictivo")
    st.markdown("Introduce tus datos para ver tu posición relativa y proyecciones de mejora")

    def _safe_unique_sorted(series):
        vals = series.dropna().astype(str).unique().tolist() if series is not None else []
        vals = [v for v in vals if v.strip() != ""]
        return sorted(vals)

    def _percentile_less_than(series, value):
        s = pd.to_numeric(series, errors='coerce').dropna()
        if len(s) == 0:
            return 0.0
        return float((s < value).mean() * 100)

    sex_opts = _safe_unique_sorted(df['Sex']) if 'Sex' in df.columns else []
    equip_opts = _safe_unique_sorted(df['Equipment']) if 'Equipment' in df.columns else []
    age_opts = _safe_unique_sorted(df['AgeClass']) if 'AgeClass' in df.columns else []
    country_opts = _safe_unique_sorted(df['Country']) if 'Country' in df.columns else []

    if not (sex_opts and equip_opts and age_opts and country_opts):
        st.warning("⚠️ El dataset no tiene valores suficientes en Sex/Equipment/AgeClass/Country para comparar.")
    else:
        with st.form("personal_data"):
            st.markdown("#### 📝 Tus Datos")
            c1, c2, c3 = st.columns(3)
            with c1:
                user_sex = st.selectbox("Sexo", sex_opts, index=sex_opts.index("M") if "M" in sex_opts else 0)
                user_equipment = st.selectbox("Equipamiento", equip_opts, index=0)
            with c2:
                user_age_class = st.selectbox("Categoría de Edad", age_opts, index=0)
                user_bodyweight = st.number_input("Peso Corporal (kg)", min_value=30.0, max_value=200.0, value=80.0, step=0.5)
            with c3:
                user_squat = st.number_input("Mejor Sentadilla (kg)", min_value=0.0, max_value=500.0, value=150.0, step=2.5)
                user_bench = st.number_input("Mejor Press Banca (kg)", min_value=0.0, max_value=300.0, value=100.0, step=2.5)

            user_deadlift = st.number_input("Mejor Peso Muerto (kg)", min_value=0.0, max_value=500.0, value=180.0, step=2.5)
            user_country = st.selectbox("País", country_opts, index=0)
            analyze_button = st.form_submit_button("🔍 Analizar mi Rendimiento")

        if analyze_button:
            user_total = float(user_squat) + float(user_bench) + float(user_deadlift)
            if user_bodyweight <= 0 or user_total <= 0:
                st.warning("⚠️ Revisa tus entradas (peso corporal y levantamientos deben ser > 0).")
                _switch_to_tab("Compararme")
                st.stop()

            must_cols = ['Sex', 'Equipment', 'AgeClass', 'TotalKg']
            if not all(c in df.columns for c in must_cols):
                st.warning("⚠️ El dataset no tiene columnas mínimas para comparar (Sex, Equipment, AgeClass, TotalKg).")
                _switch_to_tab("Compararme")
                st.stop()

            comparison_data = df[
                (df['Sex'].astype(str) == str(user_sex)) &
                (df['Equipment'].astype(str) == str(user_equipment)) &
                (df['AgeClass'].astype(str) == str(user_age_class)) &
                (df['TotalKg'].notna())
            ].copy()

            if len(comparison_data) <= 10:
                st.warning("⚠️ No hay suficientes datos para tu categoría específica (≤10). Prueba otra categoría.")
                _switch_to_tab("Compararme")
                st.stop()

            st.success(f"✅ Datos comparables encontrados: {format_count(len(comparison_data))} atletas en tu categoría")

            percentile = _percentile_less_than(comparison_data['TotalKg'], user_total)

            ca, cb = st.columns(2)
            with ca:
                st.markdown("#### 📊 Tu Posición")
                st.metric("Tu Total", format_kg(user_total))
                st.metric("Percentil", f"{percentile:.1f}%")
                st.metric("Atletas que superas", format_count(int((percentile/100)*len(comparison_data))))

                category_avg = comparison_data['TotalKg'].mean()
                category_top10 = comparison_data['TotalKg'].quantile(0.90)

                st.markdown("**Comparación:**")
                st.write(f"Promedio categoría: {format_kg(category_avg)}")
                st.write(f"Top 10% categoría: {format_kg(category_top10)}")
                st.write(f"Diferencia vs promedio: {format_kg(user_total - category_avg)}")
                st.write(f"Diferencia vs top 10%: {format_kg(user_total - category_top10)}")

            with cb:
                fig_distribution = go.Figure()
                fig_distribution.add_trace(go.Histogram(
                    x=comparison_data['TotalKg'],
                    nbinsx=30,
                    name='Distribución',
                    opacity=0.75
                ))
                fig_distribution.add_vline(
                    x=user_total,
                    line_dash="dash",
                    line_color="red",
                    annotation_text=f"Tu total: {format_kg(user_total)}",
                    annotation_position="top"
                )
                fig_distribution.update_layout(
                    title=f"Tu Posición en {user_sex}-{user_age_class}-{user_equipment}",
                    xaxis_title="Total (kg)",
                    yaxis_title="Frecuencia",
                    height=400
                )
                st.plotly_chart(fig_distribution, use_container_width=True)

            # --- Análisis predictivo simple (OLS con numpy.polyfit) ---
            st.markdown("#### 🎯 Análisis Predictivo")
            if 'BodyweightKg' in comparison_data.columns:
                valid_bw = comparison_data[comparison_data['BodyweightKg'].notna()].copy()
                if len(valid_bw) > 20:
                    x = pd.to_numeric(valid_bw['BodyweightKg'], errors='coerce').dropna().values
                    y = pd.to_numeric(valid_bw['TotalKg'], errors='coerce').dropna().values
                    n = min(len(x), len(y))
                    x, y = x[:n], y[:n]
                    try:
                        a, b = np.polyfit(x, y, 1)  # y = a*x + b
                        xr = np.linspace(x.min(), x.max(), 120)
                        yr = a * xr + b

                        cl, cr = st.columns(2)
                        with cl:
                            fig_corr = go.Figure()
                            fig_corr.add_trace(go.Scatter(x=x, y=y, mode="markers", name="Otros atletas", opacity=0.6, marker=dict(size=5)))
                            fig_corr.add_trace(go.Scatter(x=xr, y=yr, mode="lines", name="Tendencia (OLS)", line=dict(width=2)))
                            fig_corr.add_trace(go.Scatter(x=[user_bodyweight], y=[user_total], mode="markers", name="Tu posición", marker=dict(size=12, symbol="star", color="red")))
                            fig_corr.update_layout(
                                title="Relación Peso Corporal vs Total",
                                xaxis_title="Peso Corporal (kg)",
                                yaxis_title="Total (kg)",
                                height=400
                            )
                            st.plotly_chart(fig_corr, use_container_width=True)

                        with cr:
                            st.markdown("**🎯 Objetivo sugerido (escalonado):**")
                            objectives = [
                                ("Promedio de categoría", category_avg),
                                ("Top 50%", comparison_data["TotalKg"].quantile(0.50)),
                                ("Top 25%", comparison_data["TotalKg"].quantile(0.75)),
                                ("Top 10%", comparison_data["TotalKg"].quantile(0.90)),
                                ("Top 5%",  comparison_data["TotalKg"].quantile(0.95)),
                            ]
                            shown = False
                            for obj_name, obj_total in objectives:
                                if obj_total > user_total:
                                    improvement_needed = obj_total - user_total
                                    total_lifts = user_squat + user_bench + user_deadlift
                                    if total_lifts > 0:
                                        squat_impr = improvement_needed * (user_squat / total_lifts)
                                        bench_impr = improvement_needed * (user_bench / total_lifts)
                                        deadlift_impr = improvement_needed * (user_deadlift / total_lifts)

                                        st.write(f"**{obj_name}:** {format_kg(obj_total)}")
                                        st.write(f"Mejora necesaria total: {format_kg(improvement_needed)}")
                                        st.write("Distribución sugerida (proporcional a tus marcas):")
                                        st.write(f"- Sentadilla: +{format_kg(squat_impr)}")
                                        st.write(f"- Press Banca: +{format_kg(bench_impr)}")
                                        st.write(f"- Peso Muerto: +{format_kg(deadlift_impr)}")
                                        shown = True
                                        break
                            if not shown:
                                st.info("✅ Ya estás por sobre el objetivo Top 5% en esta categoría.")
                    except Exception:
                        st.warning("No se pudo ajustar la tendencia (datos insuficientes o atípicos).")
                else:
                    st.info("No hay suficientes datos con Peso Corporal para análisis predictivo (se requieren >20).")
            else:
                st.info("El dataset no incluye la columna 'BodyweightKg'.")

            # --- Fortalezas / oportunidades por % del total ---
            st.markdown("**💪 Análisis de Levantamientos (composición % del total):**")
            lifts_cols = ["Best3SquatKg", "Best3BenchKg", "Best3DeadliftKg", "TotalKg"]
            if all(c in comparison_data.columns for c in lifts_cols):
                category_lifts = comparison_data[lifts_cols].dropna()
                if not category_lifts.empty and user_total > 0:
                    avg_sq = (category_lifts["Best3SquatKg"]    / category_lifts["TotalKg"]).mean() * 100
                    avg_be = (category_lifts["Best3BenchKg"]    / category_lifts["TotalKg"]).mean() * 100
                    avg_dl = (category_lifts["Best3DeadliftKg"] / category_lifts["TotalKg"]).mean() * 100

                    user_sq = (user_squat   / user_total) * 100
                    user_be = (user_bench   / user_total) * 100
                    user_dl = (user_deadlift/ user_total) * 100

                    comp = [("Sentadilla", user_sq, avg_sq), ("Press Banca", user_be, avg_be), ("Peso Muerto", user_dl, avg_dl)]
                    for name, u, a in comp:
                        diff = u - a
                        if abs(diff) >= 2.0:
                            status = "🟢 Fortaleza" if diff > 0 else "🔴 Oportunidad"
                            st.write(f"{status} en **{name}**: {u:.1f}% vs {a:.1f}% promedio")
                else:
                    st.info("No hay datos suficientes de levantamientos detallados para esta categoría.")
            else:
                st.info("El dataset no incluye todas las columnas de levantamientos necesarios.")

            # Mantener foco en la pestaña Compararme después del submit
            _switch_to_tab("Compararme")

# -----------------------------
# FOOTER
# -----------------------------
st.markdown("---")
st.markdown(
    f"**Datos:** OpenPowerlifting | "
    f"**Registros mostrados:** {format_count(len(filtered_df))} de {format_count(len(df))} | "
    f"**Última actualización:** {datetime.now().strftime('%d/%m/%Y %H:%M')}"
)

# -----------------------------
# Nota de uso
# -----------------------------
st.caption("⚠️ Esta funcionalidad debe usarse como guía general y no reemplaza el asesoramiento de un entrenador profesional.")