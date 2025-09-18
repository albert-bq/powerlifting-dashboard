# Powerlifting Analytics Dashboard 🏋️‍♂️📊

Dashboard interactivo (Streamlit + Plotly) para explorar y analizar resultados de powerlifting a gran escala (OpenPowerlifting).
La app permite **filtrar, comparar, proyectar y contextualizar** el rendimiento por atleta, país, categoría y movimiento (S/B/D).

## ✨ Características

* **5 pestañas principales**

  1. **Información General**: participación en el tiempo, evolución M/F y evolución de S/B/D por año (con promedios anuales).
  2. **Geográfico**: mapa mundial por país con métricas (promedios por total y por movimiento) + panel lateral con detalle.
  3. **Análisis por Categorías**: distribución por **categoría de edad** (box/violin) y relación **peso corporal vs rendimiento** (scatter + media por rangos). Usa **filtros globales**.
  4. **Ficha del Atleta**: PRs, evolución S/B/D, **proyección a 6 meses** y tabla de competencias (solo filtra por **año** en esta pestaña).
  5. **Simulador de Nivel**: ingresa tus datos (peso, edad, S/B/D) y obtén **percentil**, histograma de posición, comparativa con promedio y con el **atleta superior más cercano**.

* **Conexión a BigQuery**: lectura directa de la tabla limpia `results_clean`.

* **Tema visual unificado** (*dark*, verde lima & turquesa), configurable en `theme.py`.

* **Caché de datos** para mejorar tiempos de respuesta.

* **Muestra controlada** (por defecto 100.000 filas) para **desarrollo** y **costos predecibles**.

---

## 🗂 Estructura del proyecto

```
powerlifting_dashboard/
├── app.py                     # aplicación principal (Streamlit)
├── theme.py                   # paleta y estilos de Plotly centralizados
├── requirements.txt           # dependencias
├── .env.example               # ejemplo de variables de entorno
├── LICENSE                    # Licencia de uso
├── notebooks/
│   └── powerlifting_analysis.ipynb  # notebook para descargar/preparar/limpiar/cargar data
└── .gitignore
```

> 🔒 **Importante**: las **credenciales** y la **data** **NO se suben** al repo. Usa `.env` local y tu JSON de servicio **fuera del control de versiones**.

---

## ✅ Requisitos

* **Python** 3.11+ (3.13 compatible).
* Cuenta de **Google Cloud** con BigQuery habilitado.
* Tabla en BigQuery con resultados de OpenPowerlifting (ver esquema esperado abajo).

Instala dependencias:

```bash
pip install -r requirements.txt
```

---

## 🔧 Configuración (variables de entorno)

Crea un archivo `.env` a partir de `.env.example`:

```env
PROJECT_ID=tu-proyecto-gcp
DATASET_ID=powerlifting_star
CREDENTIALS_PATH=/ruta/absoluta/a/tu-service-account.json
```

* `PROJECT_ID`: ID de tu proyecto en GCP.
* `DATASET_ID`: dataset donde está la tabla.
* `CREDENTIALS_PATH`: ruta local al **JSON de Service Account** con permisos de lectura a BigQuery.

> **Permisos mínimos recomendados** para el Service Account:
>
> * **BigQuery Data Viewer** (lectura de tablas)
> * *(Opcional)* **BigQuery Read Session User** si quieres usar BigQuery Storage (no es obligatorio; la app funciona con REST).

---

## 🗃️ Tu data en BigQuery (dos caminos)

### Opción A — Ya tienes la tabla

Si ya cargaste la data a BigQuery, asegúrate de que la tabla exista:

```
{PROJECT_ID}.{DATASET_ID}.results_clean
```

### Opción B — Quieres construir la tabla con el notebook

1. Abre `notebooks/powerlifting_analysis.ipynb`.
2. Ejecuta las celdas para:

   * Descargar data de OpenPowerlifting (CSV).
   * Limpiar/transformar.
   * Subir a BigQuery como **`results_clean`** (en tu `PROJECT_ID` y `DATASET_ID`).
3. Verifica en BigQuery que la tabla **`results_clean`** quedó creada.

> 💡 Si usas otra ruta/nombre, ajusta el **SQL del `app.py`** donde se forma la consulta.

---

## 📑 Esquema mínimo esperado de `results_clean`

La app usa (al menos) estas columnas:

* **Identidad**: `NameNormalized`, `Country`, `Federation`
* **Demografía**: `Sex`, `AgeClass`, `WeightClass`, `BodyweightKg`
* **Tiempo**: `Date` (timestamp/fecha), `Year` (numérico)
* **Performance (PRs/mejores)**: `Best3SquatKg`, `Best3BenchKg`, `Best3DeadliftKg`, `TotalKg`
* **Scores**: `Wilks`, `Dots`, `Glossbrenner`, `Goodlift`
* **Intentos**: `Squat1Kg..3Kg`, `Bench1Kg..3Kg`, `Deadlift1Kg..3Kg` *(opcionales pero útiles)*

> Si faltan algunas, la app **se adapta** y omite gráficos dependientes de esas columnas.

---

## 🚀 Ejecutar el dashboard

```bash
streamlit run app.py
```

La app se abrirá en `http://localhost:8501`.

---

## 🧭 Uso de la app (visión general)

1. **Configura filtros** en el sidebar (sexo, equipamiento, país, rango de años, etc.).
2. Explora las pestañas:

   * **Información General**: visión macro; compara participación y evolución por sexo y movimientos.
   * **Geográfico**: mapa por países con promedios y panel lateral con métricas (elige la métrica a pintar).
   * **Categorías**: edad vs rendimiento (box/violin) y peso corporal vs rendimiento (scatter con media por rangos).
   * **Ficha del Atleta**: elige un atleta, analiza su evolución y **proyección** a 6 meses.
   * **Simulador de Nivel**: ingresa tus S/B/D y peso → obtén tu **percentil** y cuánto falta para llegar al siguiente nivel.
3. **Personaliza colores/estilo** en `theme.py`.

---

## ⚙️ Modo muestra vs. dataset completo

Por defecto, el `app.py` trae una **muestra** para acelerar el desarrollo y controlar costos:

```python
# 🚀 Cambia a False para usar todo el dataset
df = load_data(sample=True)
```

* `sample=True` → la consulta agrega `LIMIT 100000` (o 10k, según dejaste configurado)
* **Para usar TODO el dataset**, edita esa línea a:

```python
df = load_data(sample=False)
```

> También puedes cambiar el **límite** directamente en la función `load_data()` si deseas un tope distinto para pruebas.

---

## 🎨 Personalización visual

Edita `theme.py` para cambiar la paleta (por defecto estilo **dark**):

```python
# theme.py (extracto)
CUSTOM_COLORS = ["#C6D92D", "#00C2C7", "#6E6E6E", "#2B2B2B"]
SEX_COLORS = {"M": "#00C2C7", "F": "#C6D92D"}
DEFAULT_LAYOUT = dict(
    plot_bgcolor="#2B2B2B",
    paper_bgcolor="#121212",
    font=dict(color="#EAEAEA"),
    title_font=dict(size=18, color="#C6D92D"),
    legend=dict(orientation="h", y=1.02, x=1)
)
```

Todos los gráficos heredan este estilo con `fig.update_layout(**DEFAULT_LAYOUT)`.

---

## 💰 Rendimiento y costos (tips)

* **Trabaja en muestra** (`sample=True`) durante el desarrollo.
* **Reduce columnas** en el SELECT si no necesitas todas.
* **Filtra por año** en el SQL para explorar periodos concretos.
* La app ya usa `@st.cache_data` para evitar recargar innecesariamente.
* Si habilitas **BigQuery Storage API** y permisos (*Read Session User*), puedes acelerar descargas con `to_dataframe(create_bqstorage_client=True)`.

---

## 🧩 Dependencias

Vienen en `requirements.txt`:

* Core: `streamlit`, `pandas`, `numpy`
* Visualización: `plotly`
* GCP: `google-cloud-bigquery`, `google-cloud-bigquery-storage`, `google-auth*`, `db-dtypes`
* Utilidad: `python-dotenv`
* (Opcional) `statsmodels` si quieres `trendline="ols"` en algunos gráficos

Instala con:

```bash
pip install -r requirements.txt
```

---

## 🔒 Seguridad (muy importante)

* **NO subas** tu `.env` ni el JSON de credenciales (`*.json`).
* El repositorio incluye un `.gitignore` que ya ignora credenciales y datos locales.
* Sube **solo** `.env.example` para documentar las variables necesarias.
* Si despliegas en **Streamlit Cloud**, guarda credenciales en **Secrets** (no en el repo).

---

## 🧪 Solución de problemas (FAQ)

* **`❌ Please install the 'db-dtypes' package`**
  → `pip install db-dtypes`

* **`UserWarning: BigQuery Storage module not found, fetch data with REST`**
  → Instala `google-cloud-bigquery-storage` **y** asigna rol *BigQuery Read Session User*
  (o ignora el warning; la app funciona con REST).

* **`403 bigquery.readsessions.create`**
  → Falta permiso *BigQuery Read Session User* para usar BQ Storage.
  Alternativa: mantener `create_bqstorage_client=False` (ya está así por defecto).

* **`404 Table ... was not found in location US`**
  → Verifica **nombre completo** `project.dataset.table` y **ubicación** del dataset.
  Ajusta `PROJECT_ID`, `DATASET_ID`, o crea la tabla en la **misma región**.

* **Gráfico muestra “undefined”**
  → Forzar título o quitarlo:

  ```python
  fig.update_layout(title="Mi título", **DEFAULT_LAYOUT)
  # o
  fig.update_layout(title=None, **DEFAULT_LAYOUT)
  ```

---

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Para más detalles, consulta el archivo LICENSE

---

## 🙌 Contribuciones

Sugerencias y PRs son bienvenidos. Ideas futuras:

* Vistas materializadas/ETL para acelerar consultas
* Benchmarks por federación
* Análisis de intentos (acierto por 1°, 2°, 3°)
* Modelos de proyección no lineales

---

## 🚀 ¡Listo!

1. Crea tu `.env` (con `PROJECT_ID`, `DATASET_ID`, `CREDENTIALS_PATH`).
2. Asegura que la tabla **`results_clean`** exista en BigQuery (usa el notebook si hace falta).
3. Instala dependencias y ejecuta:

```bash
streamlit run app.py
```

4. ¿Quieres toda la data? Cambia en `app.py`:

```python
df = load_data(sample=False)
```

Disfruta explorando y compartiendo tu dashboard de powerlifting 💪
Luis Bustos Q. - Data Analyst