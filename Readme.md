# 🖥️ Bitácora IT - Sistema de Gestión con Autenticación

Sistema profesional de gestión de inventario informático con autenticación y auditoría completa de actividades.

## 🚀 Características Principales
### 🔐 Seguridad y Autenticación
 - ✅ Login únicamente con email corporativo (@tuempresa.com)
 - ✅ Gestión de usuarios con roles (Admin/Técnico)
 - ✅ Auditoría completa de todas las actividades
 - ✅ Sesiones seguras 
 - ✅ Contraseñas hasheadas 
### 📊 Gestión de Inventario
 - ✅ Registro de equipos con componentes
 - ✅ Bitácora de reparaciones con trazabilidad completa
 - ✅ Estados de equipos (Disponible, En taller, etc.)
 - ✅ Búsqueda y filtros avanzados
### 📈 Reportes y Estadísticas
 - ✅ Dashboard con métricas en tiempo real
 - ✅ Exportación a Excel y PDF con formato profesional
 - ✅ Reportes personalizados por fecha y técnico
 - ✅ Estadísticas por tipo de equipo
### 💾 Backup y Mantenimiento
 - ✅ Backup automático
 - ✅ Exportación de reportes
 - ✅ Limpieza automática de archivos antiguos
### 📋 Requisitos Previos
Python 3.8 o superior
pip (gestor de paquetes de Python)
Dominio empresarial configurado (para emails)
🛠️ Instalación Paso a Paso
1. Clonar el repositorio
git clone https://github.com/yoanmcruz/inventario_it.git

2. Instalar las dependencias 
pip install -r requeriments.txt

3. Instalar Weasyprint
https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation

4. Migración a PostgreSQL 🐘
El uso de SQLite es ideal para el desarrollo local, pero no es recomendable para un entorno de producción con múltiples usuarios.
 - ¿Qué cambiar?
    - Base de datos: Migra a PostgreSQL. Es más robusta, segura y ofrece características avanzadas como los índices de búsqueda de texto completo, que te ayudarán a implementar la búsqueda avanzada. El cambio solo implica modificar el settings.py y el conector de la base de datos.