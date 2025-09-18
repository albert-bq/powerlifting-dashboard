#!/usr/bin/env python3
"""
Sistema de automatización para el dashboard de powerlifting
Ejecuta tareas programadas como actualizaciones de datos y backups
"""

import os
import sys
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import EVENT_JOB_EXECUTED, EVENT_JOB_ERROR
import psutil
import json

# Agregar el directorio raíz al path
sys.path.append(str(Path(__file__).parent))

from src.data.downloader import PowerliftingDataDownloader, check_data_updates
from src.data.cleaner import PowerliftingDataCleaner
from src.data.storage import OneDriveStorage, sync_with_onedrive, backup_to_onedrive
from config.settings import settings


class PowerliftingScheduler:
    """
    Sistema de automatización para el dashboard de powerlifting
    """
    
    def __init__(self):
        self.scheduler = BlockingScheduler()
        self.setup_logging()
        self.setup_signal_handlers()
        self.pid_file = settings.CACHE_DIR / "scheduler.pid"
        self.status_file = settings.CACHE_DIR / "scheduler_status.json"
        
        # Componentes del sistema
        self.downloader = PowerliftingDataDownloader()
        self.cleaner = PowerliftingDataCleaner()
        self.storage = OneDriveStorage()
        
        # Estadísticas
        self.stats = {
            'started_at': datetime.now().isoformat(),
            'jobs_executed': 0,
            'jobs_failed': 0,
            'last_update_check': None,
            'last_data_update': None,
            'last_backup': None,
            'last_sync': None
        }
        
        # Configurar eventos del scheduler
        self.scheduler.add_listener(self.job_executed, EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self.job_error, EVENT_JOB_ERROR)
    
    def setup_logging(self):
        """Configurar sistema de logging"""
        log_file = settings.LOG_FILE
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Configuración de loguru
        logger.remove()  # Remover handler por defecto
        
        # Log a archivo
        logger.add(
            log_file,
            rotation="1 week",
            retention="4 weeks",
            level=settings.LOG_LEVEL,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}",
            backtrace=True,
            diagnose=True
        )
        
        # Log a consola
        logger.add(
            sys.stdout,
            level=settings.LOG_LEVEL,
            format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | <level>{message}</level>",
            colorize=True
        )
        
        logger.info("Sistema de logging configurado")
    
    def setup_signal_handlers(self):
        """Configurar manejadores de señales para shutdown limpio"""
        def signal_handler(signum, frame):
            logger.info(f"Señal {signum} recibida. Cerrando scheduler...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def create_pid_file(self):
        """Crear archivo PID para control del proceso"""
        try:
            with open(self.pid_file, 'w') as f:
                f.write(str(os.getpid()))
            logger.info(f"Archivo PID creado: {self.pid_file}")
        except Exception as e:
            logger.error(f"Error creando archivo PID: {e}")
    
    def remove_pid_file(self):
        """Remover archivo PID"""
        try:
            if self.pid_file.exists():
                self.pid_file.unlink()
                logger.info("Archivo PID removido")
        except Exception as e:
            logger.error(f"Error removiendo archivo PID: {e}")
    
    def update_status(self):
        """Actualizar archivo de estado"""
        try:
            status = {
                **self.stats,
                'process_id': os.getpid(),
                'memory_usage_mb': psutil.Process().memory_info().rss / 1024 / 1024,
                'cpu_percent': psutil.Process().cpu_percent(),
                'update_timestamp': datetime.now().isoformat()
            }
            
            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error actualizando estado: {e}")
    
    def job_executed(self, event):
        """Callback cuando un job se ejecuta exitosamente"""
        self.stats['jobs_executed'] += 1
        logger.info(f"Job ejecutado exitosamente: {event.job_id}")
        self.update_status()
    
    def job_error(self, event):
        """Callback cuando un job falla"""
        self.stats['jobs_failed'] += 1
        logger.error(f"Job falló: {event.job_id} - {event.exception}")
        self.update_status()
    
    def check_and_update_data(self):
        """Tarea: Verificar y actualizar datos si es necesario"""
        logger.info("🔄 Iniciando verificación de datos...")
        
        try:
            self.stats['last_update_check'] = datetime.now().isoformat()
            
            # Verificar actualizaciones
            if check_data_updates():
                logger.info("📥 Nuevos datos disponibles. Descargando...")
                
                # Descargar datos
                if self.downloader.download_data():
                    logger.info("✅ Datos descargados exitosamente")
                    
                    # Procesar datos
                    logger.info("🔄 Procesando datos...")
                    if self.cleaner.process_and_save():
                        logger.info("✅ Datos procesados exitosamente")
                        self.stats['last_data_update'] = datetime.now().isoformat()
                        
                        # Sincronizar con OneDrive
                        if self.storage.enabled:
                            logger.info("☁️ Sincronizando con OneDrive...")
                            if sync_with_onedrive():
                                logger.info("✅ Sincronización exitosa")
                                self.stats['last_sync'] = datetime.now().isoformat()
                            else:
                                logger.warning("⚠️ Error en sincronización con OneDrive")
                        
                    else:
                        logger.error("❌ Error procesando datos")
                else:
                    logger.error("❌ Error descargando datos")
            else:
                logger.info("ℹ️ No hay actualizaciones disponibles")
                
        except Exception as e:
            logger.error(f"❌ Error en verificación de datos: {e}")
            raise
    
    def create_backup(self):
        """Tarea: Crear backup de datos"""
        logger.info("💾 Iniciando creación de backup...")
        
        try:
            if not self.storage.enabled:
                logger.warning("OneDrive no está configurado. Saltando backup.")
                return
            
            if backup_to_onedrive():
                logger.info("✅ Backup creado exitosamente")
                self.stats['last_backup'] = datetime.now().isoformat()
            else:
                logger.error("❌ Error creando backup")
                
        except Exception as e:
            logger.error(f"❌ Error en backup: {e}")
            raise
    
    def cleanup_old_files(self):
        """Tarea: Limpiar archivos antiguos"""
        logger.info("🧹 Iniciando limpieza de archivos...")
        
        try:
            # Limpiar logs antiguos (más de 30 días)
            log_dir = settings.LOG_FILE.parent
            if log_dir.exists():
                cutoff_date = datetime.now() - timedelta(days=30)
                for log_file in log_dir.glob("*.log*"):
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        log_file.unlink()
                        logger.info(f"Archivo de log eliminado: {log_file}")
            
            # Limpiar cache temporal (más de 7 días)
            cache_dir = settings.CACHE_DIR
            if cache_dir.exists():
                cutoff_date = datetime.now() - timedelta(days=7)
                for cache_file in cache_dir.glob("temp_*"):
                    if cache_file.stat().st_mtime < cutoff_date.timestamp():
                        cache_file.unlink()
                        logger.info(f"Archivo de cache eliminado: {cache_file}")
            
            # Limpiar datos raw antiguos (más de 14 días)
            raw_dir = settings.RAW_DATA_DIR
            if raw_dir.exists():
                cutoff_date = datetime.now() - timedelta(days=14)
                for raw_file in raw_dir.glob("openpowerlifting-*.zip"):
                    if raw_file.stat().st_mtime < cutoff_date.timestamp():
                        raw_file.unlink()
                        logger.info(f"Archivo raw eliminado: {raw_file}")
            
            logger.info("✅ Limpieza completada")
            
        except Exception as e:
            logger.error(f"❌ Error en limpieza: {e}")
            raise
    
    def health_check(self):
        """Tarea: Verificación de salud del sistema"""
        logger.info("🏥 Ejecutando verificación de salud...")
        
        try:
            # Verificar memoria
            process = psutil.Process()
            memory_mb = process.memory_info().rss / 1024 / 1024
            
            if memory_mb > 1000:  # Más de 1GB
                logger.warning(f"Alto uso de memoria: {memory_mb:.1f} MB")
            
            # Verificar espacio en disco
            disk_usage = psutil.disk_usage(str(settings.DATA_DIR))
            free_gb = disk_usage.free / 1024 / 1024 / 1024
            
            if free_gb < 1:  # Menos de 1GB libre
                logger.warning(f"Poco espacio en disco: {free_gb:.1f} GB libres")
            
            # Verificar base de datos
            try:
                summary = self.cleaner.get_data_summary()
                if summary and summary.get('total_records', 0) > 0:
                    logger.info(f"Base de datos OK: {summary['total_records']:,} registros")
                else:
                    logger.warning("Base de datos vacía o inaccesible")
            except Exception as e:
                logger.error(f"Error verificando base de datos: {e}")
            
            # Verificar OneDrive
            if self.storage.enabled:
                try:
                    if self.storage.authenticate():
                        storage_info = self.storage.get_storage_info()
                        logger.info(f"OneDrive OK: {storage_info.get('status', 'Unknown')}")
                    else:
                        logger.warning("Error conectando con OneDrive")
                except Exception as e:
                    logger.error(f"Error verificando OneDrive: {e}")
            
            logger.info("✅ Verificación de salud completada")
            
        except Exception as e:
            logger.error(f"❌ Error en verificación de salud: {e}")
            raise
    
    def setup_jobs(self):
        """Configurar trabajos programados"""
        logger.info("⚙️ Configurando trabajos programados...")
        
        # Verificación de datos cada 4 horas
        self.scheduler.add_job(
            func=self.check_and_update_data,
            trigger=CronTrigger(minute=0, second=0, hour='*/4'),
            id='data_update',
            name='Verificación de datos',
            max_instances=1,
            coalesce=True
        )
        
        # Backup diario a las 3:00 AM
        self.scheduler.add_job(
            func=self.create_backup,
            trigger=CronTrigger(hour=3, minute=0, second=0),
            id='daily_backup',
            name='Backup diario',
            max_instances=1,
            coalesce=True
        )
        
        # Limpieza semanal los domingos a las 4:00 AM
        self.scheduler.add_job(
            func=self.cleanup_old_files,
            trigger=CronTrigger(day_of_week=6, hour=4, minute=0, second=0),
            id='weekly_cleanup',
            name='Limpieza semanal',
            max_instances=1,
            coalesce=True
        )
        
        # Verificación de salud cada 30 minutos
        self.scheduler.add_job(
            func=self.health_check,
            trigger=CronTrigger(minute='*/30'),
            id='health_check',
            name='Verificación de salud',
            max_instances=1,
            coalesce=True
        )
        
        # Actualización de estado cada 5 minutos
        self.scheduler.add_job(
            func=self.update_status,
            trigger=CronTrigger(minute='*/5'),
            id='status_update',
            name='Actualización de estado',
            max_instances=1,
            coalesce=True
        )
        
        logger.info(f"✅ {len(self.scheduler.get_jobs())} trabajos configurados")
        
        # Mostrar próximas ejecuciones
        for job in self.scheduler.get_jobs():
            next_run = job.next_run_time
            logger.info(f"📅 {job.name}: próxima ejecución {next_run}")
    
    def start(self):
        """Iniciar el scheduler"""
        logger.info("🚀 Iniciando sistema de automatización...")
        
        try:
            # Verificar si ya hay otro proceso ejecutándose
            if self.is_running():
                logger.error("❌ El scheduler ya está ejecutándose")
                sys.exit(1)
            
            # Crear archivo PID
            self.create_pid_file()
            
            # Configurar trabajos
            self.setup_jobs()
            
            # Actualizar estado inicial
            self.update_status()
            
            # Ejecutar verificación inicial
            logger.info("🔄 Ejecutando verificación inicial de datos...")
            self.check_and_update_data()
            
            logger.info("✅ Sistema de automatización iniciado")
            logger.info("🎯 Presiona Ctrl+C para detener")
            
            # Iniciar scheduler
            self.scheduler.start()
            
        except (KeyboardInterrupt, SystemExit):
            logger.info("🛑 Deteniendo sistema...")
            self.shutdown()
        except Exception as e:
            logger.error(f"❌ Error iniciando scheduler: {e}")
            self.shutdown()
            sys.exit(1)
    
    def shutdown(self):
        """Detener el scheduler limpiamente"""
        logger.info("🛑 Deteniendo scheduler...")
        
        try:
            if self.scheduler.running:
                self.scheduler.shutdown(wait=False)
            
            self.remove_pid_file()
            logger.info("✅ Scheduler detenido correctamente")
            
        except Exception as e:
            logger.error(f"❌ Error deteniendo scheduler: {e}")
    
    def is_running(self):
        """Verificar si el scheduler ya está ejecutándose"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Verificar si el proceso existe
            return psutil.pid_exists(pid)
            
        except (ValueError, OSError):
            # Archivo PID corrupto o no accesible
            self.remove_pid_file()
            return False
    
    def get_status(self):
        """Obtener estado actual del scheduler"""
        try:
            if self.status_file.exists():
                with open(self.status_file, 'r') as f:
                    return json.load(f)
            return {"status": "No ejecutándose"}
        except Exception as e:
            logger.error(f"Error obteniendo estado: {e}")
            return {"status": "Error"}


def main():
    """Función principal"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Sistema de automatización para dashboard de powerlifting")
    parser.add_argument("action", choices=["start", "stop", "status", "restart"], help="Acción a ejecutar")
    parser.add_argument("--force", action="store_true", help="Forzar acción")
    
    args = parser.parse_args()
    
    scheduler = PowerliftingScheduler()
    
    if args.action == "start":
        scheduler.start()
    
    elif args.action == "stop":
        if scheduler.is_running():
            try:
                with open(scheduler.pid_file, 'r') as f:
                    pid = int(f.read().strip())
                
                os.kill(pid, signal.SIGTERM)
                time.sleep(2)
                
                if psutil.pid_exists(pid):
                    if args.force:
                        os.kill(pid, signal.SIGKILL)
                        print("✅ Scheduler detenido forzosamente")
                    else:
                        print("⚠️ El scheduler no respondió. Usa --force para detener forzosamente")
                else:
                    print("✅ Scheduler detenido")
                    
            except Exception as e:
                print(f"❌ Error deteniendo scheduler: {e}")
        else:
            print("ℹ️ El scheduler no está ejecutándose")
    
    elif args.action == "status":
        if scheduler.is_running():
            status = scheduler.get_status()
            print("✅ Scheduler ejecutándose")
            print(f"📊 Estado: {json.dumps(status, indent=2)}")
        else:
            print("❌ Scheduler no está ejecutándose")
    
    elif args.action == "restart":
        print("🔄 Reiniciando scheduler...")
        if scheduler.is_running():
            # Detener
            args.action = "stop"
            main()
            time.sleep(3)
        
        # Iniciar
        scheduler.start()


if __name__ == "__main__":
    main()