Perfecto 🙌, vamos a dejar todo redondito.

---

## 📌 1. `README.md` (actualizado con uso de `secrets.toml`)

```markdown
# Powerlifting Analytics Dashboard 🏋️‍♂️📊

Dashboard interactivo (Streamlit + Plotly) conectado a **BigQuery (Google Cloud)** para analizar millones de registros de competencias de OpenPowerlifting.  

La app permite filtrar, comparar, proyectar y contextualizar el rendimiento por atleta, país, categoría y movimiento (S/B/D).

---

## ✨ Características

- **5 pestañas principales**:
  1. **Información General** → participación en el tiempo, evolución por sexo y movimientos.
  2. **Geográfico** → mapa mundial con métricas por país.
  3. **Categorías** → análisis por rango de edad y peso corporal.
  4. **Ficha del Atleta** → evolución individual y proyecciones.
  5. **Simulador de Nivel** → compara tus marcas personales con la base de datos.

- **Conexión directa a BigQuery**.  
- **Visualizaciones con Plotly** (tema oscuro personalizable en `theme.py`).  
- **Caché de datos** para reducir tiempos de carga.  
- **Muestra controlada** (`LIMIT 100000`) por defecto para desarrollo rápido y control de costos.  

---

## 🗂 Estructura del proyecto

```

powerlifting\_dashboard/
├── app.py                     # aplicación principal
├── theme.py                   # paleta y estilos centralizados
├── requirements.txt           # dependencias
├── .gitignore                 # exclusiones (env, credenciales, data local)
├── .streamlit/
│   └── secrets.example.toml   # ejemplo de credenciales
├── notebooks/
│   └── powerlifting\_analysis.ipynb  # notebook para preparar la data
└── README.md

````

---

## ✅ Requisitos

- **Python** 3.11+  
- Cuenta de **Google Cloud** con BigQuery habilitado  
- Haber creado la tabla `results_clean` en tu proyecto/dataset de BigQuery (puedes hacerlo ejecutando el notebook `notebooks/powerlifting_analysis.ipynb`)

---

## 🔧 Configuración de credenciales

La app usa **`secrets.toml`** (en local y en Streamlit Cloud).  
Crea un archivo `.streamlit/secrets.toml` en tu máquina, copiando el ejemplo que viene en `secrets.example.toml`.

Ejemplo:

```toml
[gcp_service_account]
type = "service_account"
project_id = "openpowerlifting-XXXXXX"
private_key_id = "xxxx..."
private_key = "-----BEGIN PRIVATE KEY-----\nABC123...\n-----END PRIVATE KEY-----\n"
client_email = "xxxx@xxxx.iam.gserviceaccount.com"
client_id = "1234567890"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/xxxx"
universe_domain = "googleapis.com"

[general]
PROJECT_ID = "openpowerlifting-XXXXXX"
DATASET_ID = "powerlifting_star"
````

> 🔒 **Nota**: el campo `private_key` debe tener los saltos de línea escapados con `\n`.

---

## 🚀 Ejecutar el dashboard en local

```bash
pip install -r requirements.txt
streamlit run app.py
```

La app se abrirá en [http://localhost:8501](http://localhost:8501).

---

## 🌐 Desplegar en Streamlit Cloud

1. Haz fork o conecta tu repo en [Streamlit Cloud](https://streamlit.io/cloud).
2. Configura los **Secrets** en Settings → Secrets, copiando el contenido de tu `.streamlit/secrets.toml`.
3. Selecciona el archivo principal `app.py` y despliega 🚀.

---

## ⚙️ Modo muestra vs dataset completo

En `app.py`:

```python
# 🚀 Cambia a False para usar todo el dataset
df = load_data(sample=True)
```

* `sample=True` → consulta con `LIMIT 100000` (rápido y barato).
* `sample=False` → consulta toda la tabla en BigQuery.

---

## 🧩 Dependencias

En `requirements.txt`:

* streamlit
* pandas
* numpy
* plotly
* google-cloud-bigquery
* google-cloud-bigquery-storage
* google-auth
* db-dtypes
* python-dotenv (si quieres compatibilidad extendida)
* statsmodels (para trendlines opcionales en gráficos)

---

## 🔒 Seguridad

* No subas tus credenciales (`secrets.toml`) a GitHub.
* Usa solo `secrets.example.toml` para documentar el formato.
* En Streamlit Cloud, configura los Secrets desde la interfaz web.

---

## 🎯 Próximos pasos

* Agregar benchmarks por federación
* Análisis de intentos (éxito por levantamiento)
* Proyecciones avanzadas (modelos no lineales)
