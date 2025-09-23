"""
WSGI config for inventory_manager project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application

# Establece el módulo de configuración de Django por defecto
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Obtiene la aplicación WSGI para el proyecto
application = get_wsgi_application()

# Configuración adicional para producción
# Puedes agregar middleware adicional aquí si es necesario

# Ejemplo: Middleware para manejar errores en producción
try:
    from whitenoise import WhiteNoise
    application = WhiteNoise(application, root=os.path.join(os.path.dirname(__file__), '..', 'staticfiles'))
    application.add_files(os.path.join(os.path.dirname(__file__), '..', 'media'), prefix='media/')
except ImportError:
    # WhiteNoise no está instalado, continuar sin él
    pass

# Ejemplo: Configuración para servir archivos estáticos en producción
# Asegúrate de que los archivos estáticos estén recogidos con: python manage.py collectstatic

# Para entornos de producción, considera usar:
# - Gunicorn como servidor WSGI
# - Nginx como proxy inverso
# - WhiteNoise para servir archivos estáticos

# Instrucciones de despliegue:
# 1. Instalar dependencias: pip install -r requirements.txt
# 2. Configurar variables de entorno para producción
# 3. Configurar base de datos PostgreSQL para producción
# 4. Configurar archivos estáticos: python manage.py collectstatic
# 5. Configurar Gunicorn: pip install gunicorn
# 6. Ejecutar con: gunicorn config.wsgi:application

# Nota: Para desarrollo, usa el servidor integrado de Django:
# python manage.py runserver