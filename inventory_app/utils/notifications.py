 
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

def send_maintenance_notification(maintenance, recipients):
    """Envía notificación por email sobre un mantenimiento"""
    subject = f"Nuevo mantenimiento registrado: {maintenance.title}"
    
    html_message = render_to_string('emails/maintenance_notification.html', {
        'maintenance': maintenance,
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,
        recipients,
        html_message=html_message,
        fail_silently=False,
    )

def send_equipment_assignment_notification(equipment, recipient):
    """Envía notificación por email sobre asignación de equipo"""
    subject = f"Has sido asignado al equipo: {equipment}"
    
    html_message = render_to_string('emails/equipment_assignment.html', {
        'equipment': equipment,
        'recipient': recipient,
    })
    plain_message = strip_tags(html_message)
    
    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,
        [recipient.email],
        html_message=html_message,
        fail_silently=False,
    )

def send_backup_notification(backup_path, success=True):
    """Envía notificación por email sobre el resultado del backup"""
    subject = f"Backup {'completado' if success else 'fallido'}: {backup_path}"
    
    html_message = render_to_string('emails/backup_notification.html', {
        'backup_path': backup_path,
        'success': success,
    })
    plain_message = strip_tags(html_message)
    
    # Enviar a administradores
    admin_emails = ['admin@tuempresa.com']  # Reemplazar con emails reales
    
    send_mail(
        subject,
        plain_message,
        settings.EMAIL_HOST_USER,
        admin_emails,
        html_message=html_message,
        fail_silently=False,
    )