 
from django.core.management.base import BaseCommand
from django.conf import settings
import os
import shutil
from datetime import datetime
import zipfile

class Command(BaseCommand):
    help = 'Creates a backup of the database and media files'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--compress',
            action='store_true',
            help='Compress the backup into a ZIP file',
        )
    
    def handle(self, *args, **options):
        self.stdout.write('Starting backup process...')
        
        # Crear directorio de backups si no existe
        if not os.path.exists(settings.BACKUP_PATH):
            os.makedirs(settings.BACKUP_PATH)
            self.stdout.write(f'Created backup directory: {settings.BACKUP_PATH}')
        
        # Nombre del archivo de backup con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if options['compress']:
            backup_filename = f"backup_{timestamp}.zip"
            backup_path = os.path.join(settings.BACKUP_PATH, backup_filename)
            
            # Crear archivo ZIP
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Backup de la base de datos SQLite
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path):
                    zipf.write(db_path, os.path.basename(db_path))
                    self.stdout.write(f'Added database to backup: {os.path.basename(db_path)}')
                
                # Backup de archivos media si existen
                if hasattr(settings, 'MEDIA_ROOT') and os.path.exists(settings.MEDIA_ROOT):
                    for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, settings.BASE_DIR)
                            zipf.write(file_path, arcname)
                    self.stdout.write(f'Added media files to backup')
            
            self.stdout.write(
                self.style.SUCCESS(f'Backup created successfully: {backup_path}')
            )
        else:
            # Crear directorio con la fecha para backup sin comprimir
            backup_dir = os.path.join(settings.BACKUP_PATH, f"backup_{timestamp}")
            os.makedirs(backup_dir)
            
            # Copiar base de datos
            db_path = settings.DATABASES['default']['NAME']
            if os.path.exists(db_path):
                shutil.copy2(db_path, backup_dir)
                self.stdout.write(f'Copied database to: {backup_dir}')
            
            # Copiar archivos media si existen
            if hasattr(settings, 'MEDIA_ROOT') and os.path.exists(settings.MEDIA_ROOT):
                media_backup_dir = os.path.join(backup_dir, 'media')
                shutil.copytree(settings.MEDIA_ROOT, media_backup_dir)
                self.stdout.write(f'Copied media files to: {media_backup_dir}')
            
            self.stdout.write(
                self.style.SUCCESS(f'Backup created successfully: {backup_dir}')
            )
        
        # Limpiar backups antiguos (mantener solo los últimos 30 días)
        self.clean_old_backups()
    
    def clean_old_backups(self):
        """Elimina backups con más de 30 días de antigüedad"""
        import time
        now = time.time()
        backup_age = 30 * 24 * 60 * 60  # 30 días en segundos
        
        for filename in os.listdir(settings.BACKUP_PATH):
            filepath = os.path.join(settings.BACKUP_PATH, filename)
            if os.path.isfile(filepath) or os.path.islink(filepath):
                if now - os.path.getctime(filepath) > backup_age:
                    os.remove(filepath)
                    self.stdout.write(f'Removed old backup: {filename}')
            elif os.path.isdir(filepath) and filename.startswith('backup_'):
                if now - os.path.getctime(filepath) > backup_age:
                    shutil.rmtree(filepath)
                    self.stdout.write(f'Removed old backup directory: {filename}')