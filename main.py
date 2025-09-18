#!/usr/bin/env python3
"""
Archivo principal para ejecutar el dashboard de powerlifting
Proporciona diferentes modos de ejecución: dashboard, procesamiento, etc.
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path
from loguru import logger

# Agregar el directorio actual al path
sys.path.append(str(Path(__file__).parent))

from config.settings import settings
from src.data.downloader import PowerliftingDataDownloader, check_data_updates
from src.data.cleaner import PowerliftingDataCleaner
from src.data.storage import OneDriveStorage, sync_with_onedrive


def setup_logging():
    """Configurar logging básico"""
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True
    )


def check_dependencies():
    """Verificar que las dependencias estén instaladas"""
    logger.info("🔍 Verificando dependencias...")
    
    required_packages = [
        'streamlit', 'pandas', 'plotly', 'requests', 
        'sqlalchemy', 'apscheduler', 'loguru'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"❌ Paquetes faltantes: {', '.join(missing_packages)}")
        logger.info("💡 Instala con: pip install -r requirements.txt")
        return False
    
    logger.info("✅ Todas las dependencias están instaladas")
    return True


def init_project():
    """Inicializar proyecto: crear directorios y configuración inicial"""
    logger.info("🚀 Inicializando proyecto...")
    
    try:
        # Crear directorios
        settings.create_directories()
        logger.info("📁 Directorios creados")
        
        # Crear archivo .env si no existe
        env_file = Path('.env')
        if not env_file.exists():
            env_content = """# Configuración del Dashboard de Powerlifting

# Configuración general
DEBUG=False
LOG_LEVEL=INFO

# OneDrive (opcional - configurar para backup automático)
# ONEDRIVE_CLIENT_ID=your_client_id
# ONEDRIVE_CLIENT_SECRET=your_client_secret
# ONEDRIVE_TENANT_ID=your_tenant_id

# Dashboard
DASHBOARD_HOST=localhost
DASHBOARD_PORT=8501

# Automatización
UPDATE_INTERVAL_HOURS=24
UPDATE_TIME=02:00

# Base de datos
# DATABASE_URL=sqlite:///data/powerlifting.db

# Procesamiento
CHUNK_SIZE=10000
MAX_WORKERS=4
CACHE_EXPIRY_HOURS=6
"""
            with open(env_file, 'w') as f:
                f.write(env_content)
            logger.info("📄 Archivo .env creado")
        
        logger.info("✅ Proyecto inicializado correctamente")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error inicializando proyecto: {e}")
        return False


def download_and_process_data():
    """Descargar y procesar datos iniciales"""
    logger.info("📥 Descargando y procesando datos...")
    
    try:
        # Descargar datos
        downloader = PowerliftingDataDownloader()
        logger.info("🔄 Verificando actualizaciones...")
        
        if downloader.download_data(force=True):
            logger.info("✅ Datos descargados exitosamente")
            
            # Procesar datos
            logger.info("🔄 Procesando datos...")
            cleaner = PowerliftingDataCleaner()
            
            if cleaner.process_and_save():
                logger.info("✅ Datos procesados exitosamente")
                
                # Mostrar resumen
                summary = cleaner.get_data_summary()
                logger.info("📊 Resumen de datos:")
                for key, value in summary.items():
                    logger.info(f"  • {key}: {value}")
                
                # Sincronizar con OneDrive si está configurado
                storage = OneDriveStorage()
                if storage.enabled:
                    logger.info("☁️ Sincronizando con OneDrive...")
                    if sync_with_onedrive():
                        logger.info("✅ Sincronización exitosa")
                    else:
                        logger.warning("⚠️ Error en sincronización")
                
                return True
            else:
                logger.error("❌ Error procesando datos")
                return False
        else:
            logger.error("❌ Error descargando datos")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error en descarga y procesamiento: {e}")
        return False


def run_dashboard():
    """Ejecutar el dashboard de Streamlit"""
    logger.info("🚀 Iniciando dashboard...")
    
    try:
        # Verificar que los datos existan
        cleaner = PowerliftingDataCleaner()
        summary = cleaner.get_data_summary()
        
        if not summary or summary.get('total_records', 0) == 0:
            logger.warning("⚠️ No hay datos procesados. Ejecutando procesamiento inicial...")
            if not download_and_process_data():
                logger.error("❌ No se pudieron procesar los datos")
                return False
        
        # Ejecutar Streamlit
        dashboard_path = Path("src/dashboard/app.py")
        if not dashboard_path.exists():
            logger.error(f"❌ No se encuentra el archivo del dashboard: {dashboard_path}")
            return False
        
        cmd = [
            "streamlit", "run", str(dashboard_path),
            "--server.address", settings.DASHBOARD_HOST,
            "--server.port", str(settings.DASHBOARD_PORT),
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false"
        ]
        
        logger.info(f"🌐 Dashboard disponible en: http://{settings.DASHBOARD_HOST}:{settings.DASHBOARD_PORT}")
        logger.info("🛑 Presiona Ctrl+C para detener")
        
        subprocess.run(cmd)
        return True
        
    except KeyboardInterrupt:
        logger.info("🛑 Dashboard detenido por el usuario")
        return True
    except Exception as e:
        logger.error(f"❌ Error ejecutando dashboard: {e}")
        return False


def run_scheduler():
    """Ejecutar el sistema de automatización"""
    logger.info("⏰ Iniciando sistema de automatización...")
    
    try:
        from scheduler import PowerliftingScheduler
        
        scheduler = PowerliftingScheduler()
        scheduler.start()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error ejecutando scheduler: {e}")
        return False


def show_status():
    """Mostrar estado del sistema"""
    logger.info("📊 Estado del sistema:")
    
    try:
        # Estado de los datos
        downloader = PowerliftingDataDownloader()
        data_info = downloader.get_data_info()
        
        logger.info("📥 Datos:")
        for key, value in data_info.items():
            logger.info(f"  • {key}: {value}")
        
        # Estado de la base de datos
        cleaner = PowerliftingDataCleaner()
        summary = cleaner.get_data_summary()
        
        logger.info("🗄️ Base de datos:")
        for key, value in summary.items():
            logger.info(f"  • {key}: {value}")
        
        # Estado de OneDrive
        storage = OneDriveStorage()
        if storage.enabled:
            try:
                if storage.authenticate():
                    storage_info = storage.get_storage_info()
                    logger.info("☁️ OneDrive:")
                    for key, value in storage_info.items():
                        logger.info(f"  • {key}: {value}")
                else:
                    logger.warning("⚠️ OneDrive: No conectado")
            except Exception as e:
                logger.error(f"❌ OneDrive: Error - {e}")
        else:
            logger.info("☁️ OneDrive: No configurado")
        
        # Estado del scheduler
        try:
            from scheduler import PowerliftingScheduler
            scheduler_instance = PowerliftingScheduler()
            
            if scheduler_instance.is_running():
                status = scheduler_instance.get_status()
                logger.info("⏰ Scheduler: Ejecutándose")
                logger.info(f"  • PID: {status.get('process_id', 'N/A')}")
                logger.info(f"  • Iniciado: {status.get('started_at', 'N/A')}")
                logger.info(f"  • Jobs ejecutados: {status.get('jobs_executed', 0)}")
                logger.info(f"  • Jobs fallidos: {status.get('jobs_failed', 0)}")
            else:
                logger.info("⏰ Scheduler: No ejecutándose")
                
        except Exception as e:
            logger.error(f"❌ Error verificando scheduler: {e}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo estado: {e}")
        return False


def create_setup_guide():
    """Crear guía de configuración"""
    guide_content = """# 🏋️‍♂️ Dashboard de Powerlifting - Guía de Configuración

## 📋 Requisitos Previos

1. **Python 3.8+**
2. **Git** (para clonar el repositorio)
3. **Cuenta de OneDrive** (opcional, para backup automático)

## 🚀 Instalación Rápida

### 1. Clonar o descargar el proyecto
```bash
git clone <url-del-repositorio>
cd powerlifting_dashboard
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
```

### 3. Inicializar proyecto
```bash
python main.py init
```

### 4. Descargar y procesar datos iniciales
```bash
python main.py process
```

### 5. Ejecutar dashboard
```bash
python main.py dashboard
```

## ⚙️ Configuración de OneDrive (Opcional)

Para habilitar backup automático en OneDrive:

1. **Registrar aplicación en Azure AD:**
   - Ve a [Azure Portal](https://portal.azure.com)
   - Registra una nueva aplicación
   - Configura permisos para Microsoft Graph
   - Anota: Client ID, Client Secret, Tenant ID

2. **Configurar variables de entorno:**
   Edita el archivo `.env`:
   ```
   ONEDRIVE_CLIENT_ID=tu_client_id
   ONEDRIVE_CLIENT_SECRET=tu_client_secret
   ONEDRIVE_TENANT_ID=tu_tenant_id
   ```

## 🔄 Automatización

### Ejecutar sistema de automatización:
```bash
python main.py scheduler
```

### Controlar scheduler:
```bash
python scheduler.py start    # Iniciar
python scheduler.py stop     # Detener
python scheduler.py status   # Ver estado
python scheduler.py restart  # Reiniciar
```

## 📊 Comandos Disponibles

| Comando | Descripción |
|---------|-------------|
| `python main.py init` | Inicializar proyecto |
| `python main.py process` | Procesar datos |
| `python main.py dashboard` | Ejecutar dashboard |
| `python main.py scheduler` | Ejecutar automatización |
| `python main.py status` | Ver estado del sistema |
| `python main.py update` | Actualizar datos manualmente |

## 🐛 Solución de Problemas

### Problema: Error de dependencias
**Solución:** `pip install -r requirements.txt`

### Problema: No hay datos
**Solución:** `python main.py process`

### Problema: Error de OneDrive
**Solución:** Verificar configuración en `.env`

### Problema: Dashboard no inicia
**Solución:** Verificar que el puerto 8501 esté libre

## 📁 Estructura del Proyecto

```
powerlifting_dashboard/
├── src/
│   ├── data/           # Módulos de datos
│   └── dashboard/      # Dashboard Streamlit
├── data/
│   ├── raw/           # Datos sin procesar
│   ├── processed/     # Datos limpios
│   └── cache/         # Cache temporal
├── config/            # Configuración
├── main.py           # Archivo principal
├── scheduler.py      # Sistema de automatización
└── requirements.txt  # Dependencias
```

## 🔧 Personalización

### Cambiar puerto del dashboard:
Edita `DASHBOARD_PORT` en `.env`

### Cambiar frecuencia de actualización:
Edita `UPDATE_INTERVAL_HOURS` en `.env`

### Cambiar hora de backup:
Modifica el scheduler en `scheduler.py`

## 📞 Soporte

Para reportar problemas o sugerencias:
- Crear issue en el repositorio
- Revisar logs en `data/logs/`
- Verificar estado con `python main.py status`
"""

    guide_path = Path("SETUP_GUIDE.md")
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    logger.info(f"📖 Guía de configuración creada: {guide_path}")
    return True


def main():
    """Función principal"""
    setup_logging()
    
    parser = argparse.ArgumentParser(
        description="🏋️‍♂️ Dashboard de Powerlifting - Sistema completo de análisis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py init                 # Inicializar proyecto
  python main.py process              # Procesar datos
  python main.py dashboard            # Ejecutar dashboard
  python main.py scheduler            # Ejecutar automatización
  python main.py status               # Ver estado
  python main.py update               # Actualizar datos
  python main.py --help               # Mostrar ayuda
        """
    )
    
    parser.add_argument(
        "command",
        choices=[
            "init", "process", "dashboard", "scheduler", 
            "status", "update", "guide", "check"
        ],
        help="Comando a ejecutar"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Forzar ejecución (para update y process)"
    )
    
    parser.add_argument(
        "--no-onedrive",
        action="store_true",
        help="Deshabilitar OneDrive para esta ejecución"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=settings.DASHBOARD_PORT,
        help=f"Puerto para el dashboard (default: {settings.DASHBOARD_PORT})"
    )
    
    args = parser.parse_args()
    
    # Deshabilitar OneDrive si se solicita
    if args.no_onedrive:
        os.environ['ONEDRIVE_CLIENT_ID'] = ''
        logger.info("☁️ OneDrive deshabilitado para esta ejecución")
    
    # Actualizar puerto si se especifica
    if args.port != settings.DASHBOARD_PORT:
        settings.DASHBOARD_PORT = args.port
        logger.info(f"🌐 Puerto del dashboard cambiado a: {args.port}")
    
    # Banner de bienvenida
    logger.info("🏋️‍♂️ Dashboard de Powerlifting")
    logger.info("="*50)
    
    # Ejecutar comando
    success = False
    
    if args.command == "check":
        success = check_dependencies()
    
    elif args.command == "init":
        logger.info("🚀 Inicializando proyecto...")
        success = check_dependencies() and init_project()
        if success:
            logger.info("✅ Proyecto inicializado correctamente")
            logger.info("💡 Siguiente paso: python main.py process")
    
    elif args.command == "process":
        logger.info("🔄 Procesando datos...")
        success = check_dependencies() and download_and_process_data()
        if success:
            logger.info("✅ Datos procesados correctamente")
            logger.info("💡 Siguiente paso: python main.py dashboard")
    
    elif args.command == "dashboard":
        logger.info("📊 Iniciando dashboard...")
        success = check_dependencies() and run_dashboard()
    
    elif args.command == "scheduler":
        logger.info("⏰ Iniciando automatización...")
        success = check_dependencies() and run_scheduler()
    
    elif args.command == "status":
        logger.info("📊 Obteniendo estado del sistema...")
        success = show_status()
    
    elif args.command == "update":
        logger.info("🔄 Actualizando datos...")
        try:
            # Verificar actualizaciones
            if args.force or check_data_updates():
                success = download_and_process_data()
                if success:
                    logger.info("✅ Datos actualizados correctamente")
            else:
                logger.info("ℹ️ No hay actualizaciones disponibles")
                success = True
        except Exception as e:
            logger.error(f"❌ Error actualizando datos: {e}")
            success = False
    
    elif args.command == "guide":
        logger.info("📖 Creando guía de configuración...")
        success = create_setup_guide()
        if success:
            logger.info("✅ Guía creada: SETUP_GUIDE.md")
    
    # Resultado final
    if success:
        logger.info("🎉 Operación completada exitosamente")
        sys.exit(0)
    else:
        logger.error("❌ Operación falló")
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Operación cancelada por el usuario")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        sys.exit(1)