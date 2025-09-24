from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db import models
from django.db.models import Q, Count, Sum
from django.utils import timezone
from datetime import timedelta
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Equipment, MaintenanceLog, CompanyUser, AuditLog, SupportTicket
from .forms import EquipmentForm, MaintenanceForm, UserRegistrationForm, SupportTicketForm, SupportTicketUpdateForm
from django.http import HttpResponse
import os
import zipfile
from datetime import datetime
from django.conf import settings

# Función helper para obtener o crear CompanyUser
def get_or_create_companyuser(user):
    """
    Obtener el CompanyUser asociado a un usuario, o crearlo si no existe
    """
    try:
        return user.companyuser
    except CompanyUser.DoesNotExist:
        # Crear un CompanyUser por defecto
        company_user = CompanyUser.objects.create(
            user=user,
            department='IT',
            phone='000-000-0000',
            email=f'{user.username}@tuempresa.com'
        )
        return company_user
    
def is_admin(user):
    return user.is_superuser or user.is_staff

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

@login_required
def dashboard(request):
    # Estadísticas en tiempo real
    total_equipment = Equipment.objects.count()
    available_equipment = Equipment.objects.filter(status='AVA').count()
    in_use_equipment = Equipment.objects.filter(status='INU').count()
    in_repair_equipment = Equipment.objects.filter(status='REP').count()
    
    # Nuevas métricas dinámicas
    open_tickets = SupportTicket.objects.filter(status='OPEN').count()
    in_progress_tickets = SupportTicket.objects.filter(status='IN_PROGRESS').count()
    critical_tickets = SupportTicket.objects.filter(priority='CRITICAL', status__in=['OPEN', 'IN_PROGRESS']).count()
    
    # Equipos que necesitan atención
    warranty_expiring_soon = Equipment.objects.filter(
        warranty_expiry__isnull=False,
        warranty_expiry__range=[timezone.now().date(), timezone.now().date() + timedelta(days=30)]
    ).count()
    
    maintenance_pending = MaintenanceLog.objects.filter(end_date__isnull=True).count()
    
    # CORRECCIÓN: Simplificar la consulta sin usar models.F
    equipment_by_type = list(Equipment.objects.values('type').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    # Convertir códigos a nombres legibles
    type_display_map = dict(Equipment.EQUIPMENT_TYPES)
    for item in equipment_by_type:
        item['display_name'] = type_display_map.get(item['type'], item['type'])
        item['name'] = item['type']  # Agregar campo name sin usar models.F
    
    equipment_by_status = list(Equipment.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    status_display_map = dict(Equipment.STATUS_CHOICES)
    for item in equipment_by_status:
        item['display_name'] = status_display_map.get(item['status'], item['status'])
        item['name'] = item['status']  # Agregar campo name sin usar models.F
    
    # Mantenimientos recientes para la tabla
    recent_maintenance = MaintenanceLog.objects.all().select_related(
        'equipment', 'technician'
    ).order_by('-start_date')[:10]
    
    # Tickets recientes
    recent_tickets = SupportTicket.objects.all().select_related(
        'created_by', 'assigned_to', 'equipment'
    ).order_by('-created_at')[:5]
    
    context = {
        # Tarjetas principales
        'total_equipment': total_equipment,
        'available_equipment': available_equipment,
        'in_use_equipment': in_use_equipment,
        'in_repair_equipment': in_repair_equipment,
        'open_tickets': open_tickets,
        'in_progress_tickets': in_progress_tickets,
        'critical_tickets': critical_tickets,
        'warranty_expiring_soon': warranty_expiring_soon,
        'maintenance_pending': maintenance_pending,
        
        # Datos para gráficos (CORREGIDO)
        'equipment_by_type': equipment_by_type,
        'equipment_by_status': equipment_by_status,
        
        # Tablas
        'recent_maintenance': recent_maintenance,
        'recent_tickets': recent_tickets,
    }
    return render(request, 'dashboard.html', context)

@login_required
def dashboard_stats_api(request):
    """
    API para obtener estadísticas actualizadas del dashboard
    """
    stats = {
        'equipment': {
            'total': Equipment.objects.count(),
            'available': Equipment.objects.filter(status='AVA').count(),
            'in_use': Equipment.objects.filter(status='INU').count(),
            'in_repair': Equipment.objects.filter(status='REP').count(),
        },
        'tickets': {
            'open': SupportTicket.objects.filter(status='OPEN').count(),
            'in_progress': SupportTicket.objects.filter(status='IN_PROGRESS').count(),
            'critical': SupportTicket.objects.filter(priority='CRITICAL', status__in=['OPEN', 'IN_PROGRESS']).count(),
        },
        'alerts': {
            'warranty_expiring': Equipment.objects.filter(
                warranty_expiry__isnull=False,
                warranty_expiry__range=[timezone.now().date(), timezone.now().date() + timedelta(days=30)]
            ).count(),
            'maintenance_pending': MaintenanceLog.objects.filter(end_date__isnull=True).count(),
        },
        'timestamp': timezone.now().isoformat()
    }
    return JsonResponse(stats)

@login_required
def equipment_chart_data_api(request):
    """
    API para datos de gráficos de equipos (CORREGIDO)
    """
    equipment_by_type = list(Equipment.objects.values('type').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    type_display_map = dict(Equipment.EQUIPMENT_TYPES)
    for item in equipment_by_type:
        item['label'] = type_display_map.get(item['type'], item['type'])
    
    equipment_by_status = list(Equipment.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count'))
    
    status_display_map = dict(Equipment.STATUS_CHOICES)
    for item in equipment_by_status:
        item['label'] = status_display_map.get(item['status'], item['status'])
    
    return JsonResponse({
        'by_type': equipment_by_type,
        'by_status': equipment_by_status
    })

@login_required
def recent_activity_api(request):
    """
    API para actividad reciente (CORREGIDO - alternativa sin models.F)
    """
    # Usar una alternativa a models.F para evitar el error
    recent_maintenance = []
    maintenance_logs = MaintenanceLog.objects.select_related('equipment', 'technician').order_by('-start_date')[:5]
    
    for maintenance in maintenance_logs:
        recent_maintenance.append({
            'id': maintenance.id,
            'title': maintenance.title,
            'start_date': maintenance.start_date.isoformat(),
            'maintenance_type': maintenance.maintenance_type,
            'equipment_brand': maintenance.equipment.brand if maintenance.equipment else 'N/A',
            'equipment_model': maintenance.equipment.model if maintenance.equipment else 'N/A',
            'technician_name': maintenance.technician.user.get_full_name() if maintenance.technician else 'N/A'
        })
    
    recent_tickets = []
    tickets = SupportTicket.objects.select_related('created_by', 'equipment').order_by('-created_at')[:5]
    
    for ticket in tickets:
        recent_tickets.append({
            'id': ticket.id,
            'title': ticket.title,
            'created_at': ticket.created_at.isoformat(),
            'priority': ticket.priority,
            'status': ticket.status,
            'created_by_name': ticket.created_by.user.get_full_name() if ticket.created_by else 'N/A',
            'equipment_model': ticket.equipment.model if ticket.equipment else 'N/A'
        })
    
    return JsonResponse({
        'maintenance': recent_maintenance,
        'tickets': recent_tickets
    })
    
class EquipmentListView(LoginRequiredMixin, ListView):
    model = Equipment
    template_name = 'equipment_list.html'
    context_object_name = 'equipment_list'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('assigned_to')
        
        # Filtros
        query = self.request.GET.get('q')
        status_filter = self.request.GET.get('status')
        type_filter = self.request.GET.get('type')
        location_filter = self.request.GET.get('location')
        
        if query:
            queryset = queryset.filter(
                Q(brand__icontains=query) | 
                Q(model__icontains=query) | 
                Q(serial_number__icontains=query) |
                Q(location__icontains=query)
            )
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        if type_filter:
            queryset = queryset.filter(type=type_filter)
            
        if location_filter:
            queryset = queryset.filter(location__icontains=location_filter)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        context['status_filter'] = self.request.GET.get('status', '')
        context['type_filter'] = self.request.GET.get('type', '')
        context['location_filter'] = self.request.GET.get('location', '')
        return context

class EquipmentDetailView(LoginRequiredMixin, DetailView):
    model = Equipment
    template_name = 'equipment_detail.html'
    context_object_name = 'equipment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        equipment = self.get_object()
        context['maintenance_logs'] = MaintenanceLog.objects.filter(
            equipment=equipment
        ).select_related('technician').order_by('-start_date')
        context['components'] = equipment.components.all()
        return context

class EquipmentCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'equipment_form.html'
    success_url = reverse_lazy('equipment_list')
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Obtener o crear CompanyUser para el usuario actual
        company_user = get_or_create_companyuser(self.request.user)
        
        # Registrar en auditoría
        AuditLog.objects.create(
            user=company_user,
            action='CRE',
            model_name='Equipment',
            object_id=self.object.id,
            details=f"Equipment created: {self.object}",
            ip_address=self.get_client_ip()
        )
        messages.success(self.request, 'Equipment added successfully.')
        return response
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

class EquipmentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Equipment
    form_class = EquipmentForm
    template_name = 'equipment_form.html'
    
    def test_func(self):
        return is_admin(self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Obtener o crear CompanyUser para el usuario actual
        company_user = get_or_create_companyuser(self.request.user)
        
        # Registrar en auditoría
        AuditLog.objects.create(
            user=company_user,
            action='UPD',
            model_name='Equipment',
            object_id=self.object.id,
            details=f"Equipment updated: {self.object}",
            ip_address=self.get_client_ip()
        )
        messages.success(self.request, 'Equipment updated successfully.')
        return response
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

@login_required
@user_passes_test(is_admin)
def equipment_delete(request, pk):
    equipment = get_object_or_404(Equipment, pk=pk)
    if request.method == 'POST':
        # Obtener o crear CompanyUser para el usuario actual
        company_user = get_or_create_companyuser(request.user)
        
        # Registrar en auditoría antes de eliminar
        AuditLog.objects.create(
            user=company_user,
            action='DEL',
            model_name='Equipment',
            object_id=equipment.id,
            details=f"Equipment deleted: {equipment}",
            ip_address=get_client_ip(request)
        )
        equipment.delete()
        messages.success(request, 'Equipment deleted successfully.')
        return redirect('equipment_list')
    
    return render(request, 'equipment_confirm_delete.html', {'equipment': equipment})

@login_required
def maintenance_create(request, equipment_id):
    equipment = get_object_or_404(Equipment, pk=equipment_id)
    
    if request.method == 'POST':
        form = MaintenanceForm(request.POST)
        if form.is_valid():
            maintenance = form.save(commit=False)
            maintenance.equipment = equipment
            
            # CORREGIDO: Usar la función helper
            company_user = get_or_create_companyuser(request.user)
            maintenance.technician = company_user
            
            maintenance.save()
            
            # Actualizar estado del equipo si es necesario
            if maintenance.maintenance_type == 'REP' and not maintenance.end_date:
                equipment.status = 'REP'
                equipment.save()
            
            # Registrar en auditoría
            AuditLog.objects.create(
                user=company_user,
                action='REP',
                model_name='MaintenanceLog',
                object_id=maintenance.id,
                details=f"Maintenance created for {equipment}: {maintenance.title}",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'Maintenance log created successfully.')
            return redirect('equipment_detail', pk=equipment_id)
    else:
        form = MaintenanceForm(initial={'start_date': timezone.now()})
    
    return render(request, 'maintenance_form.html', {'form': form, 'equipment': equipment})

@login_required
def export_report(request, report_type):
    if report_type == 'equipment_excel':
        equipment = Equipment.objects.all().select_related('assigned_to')
        from .utils.exporters import export_equipment_to_excel
        response = export_equipment_to_excel(equipment)
        filename = f"equipment_report_{timezone.now().strftime('%Y-%m-%d')}.xlsx"
    elif report_type == 'equipment_pdf':
        equipment = Equipment.objects.all().select_related('assigned_to')
        from .utils.exporters import export_equipment_to_pdf
        response = export_equipment_to_pdf(equipment)
        filename = f"equipment_report_{timezone.now().strftime('%Y-%m-%d')}.pdf"
    elif report_type == 'maintenance_excel':
        maintenance = MaintenanceLog.objects.all().select_related('equipment', 'technician')
        from .utils.exporters import export_maintenance_to_excel
        response = export_maintenance_to_excel(maintenance)
        filename = f"maintenance_report_{timezone.now().strftime('%Y-%m-%d')}.xlsx"
    else:
        messages.error(request, 'Invalid report type.')
        return redirect('dashboard')
    
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required
def reports_dashboard(request):
    # Obtener información de backups
    backup_count = 0
    latest_backup = None
    backup_dir = settings.BACKUP_PATH
    
    if os.path.exists(backup_dir):
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.zip') and f.startswith('backup_')]
        backup_count = len(backup_files)
        
        if backup_files:
            # Obtener el backup más reciente
            backup_files.sort(key=lambda x: os.path.getctime(os.path.join(backup_dir, x)), reverse=True)
            latest_file = backup_files[0]
            latest_path = os.path.join(backup_dir, latest_file)
            latest_backup = {
                'name': latest_file,
                'size': os.path.getsize(latest_path),
                'size_mb': round(os.path.getsize(latest_path) / (1024 * 1024), 2),
                'created': datetime.fromtimestamp(os.path.getctime(latest_path))
            }
    
    context = {
        'backup_count': backup_count,
        'latest_backup': latest_backup,
        'BACKUP_PATH': backup_dir,
        'DATABASE_NAME': os.path.basename(settings.DATABASES['default']['NAME'])
    }
    return render(request, 'reports.html', context)

# API views for dashboard charts
@login_required
def equipment_stats_api(request):
    stats = Equipment.objects.values('type').annotate(count=Count('id'))
    return JsonResponse(list(stats), safe=False)

@login_required
def maintenance_stats_api(request):
    current_year = timezone.now().year
    stats = MaintenanceLog.objects.filter(
        start_date__year=current_year
    ).values('start_date__month').annotate(total_cost=Sum('cost')).order_by('start_date__month')
    
    data = [{'month': item['start_date__month'], 'cost': float(item['total_cost'] or 0)} for item in stats]
    return JsonResponse(data, safe=False)

# Support Ticket Views
@login_required
def support_ticket_list(request):
    tickets = SupportTicket.objects.all().select_related('created_by', 'assigned_to', 'equipment')
    
    status_filter = request.GET.get('status')
    priority_filter = request.GET.get('priority')
    
    if status_filter:
        tickets = tickets.filter(status=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority=priority_filter)
    
    context = {
        'tickets': tickets,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
    }
    return render(request, 'support_ticket_list.html', context)

@login_required
def support_ticket_create(request):
    if request.method == 'POST':
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            ticket = form.save(commit=False)
            
            # Obtener o crear CompanyUser para el usuario actual
            company_user = get_or_create_companyuser(request.user)
            ticket.created_by = company_user
            
            ticket.save()
            
            # Registrar en auditoría
            AuditLog.objects.create(
                user=company_user,
                action='CRE',
                model_name='SupportTicket',
                object_id=ticket.id,
                details=f"Support ticket created: {ticket.title}",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'Ticket creado exitosamente.')
            return redirect('support_ticket_list')
    else:
        form = SupportTicketForm()
    
    return render(request, 'support_ticket_form.html', {'form': form})

@login_required
def support_ticket_detail(request, pk):
    ticket = get_object_or_404(SupportTicket, pk=pk)
    technicians = CompanyUser.objects.all()
    
    if request.method == 'POST' and request.user.is_superuser:
        form = SupportTicketUpdateForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            
            # Registrar en auditoría
            AuditLog.objects.create(
                user=request.user.companyuser,
                action='UPD',
                model_name='SupportTicket',
                object_id=ticket.id,
                details=f"Support ticket updated: {ticket.title}",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'Ticket actualizado exitosamente.')
            return redirect('support_ticket_detail', pk=ticket.pk)
    else:
        form = SupportTicketUpdateForm(instance=ticket)
    
    context = {
        'ticket': ticket,
        'technicians': technicians,
        'form': form,
    }
    return render(request, 'support_ticket_detail.html', context)

@login_required
def support_ticket_update(request, pk):
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    if request.method == 'POST':
        form = SupportTicketUpdateForm(request.POST, instance=ticket)
        if form.is_valid():
            form.save()
            
            # Obtener o crear CompanyUser para el usuario actual
            company_user = get_or_create_companyuser(request.user)
            
            # Registrar en auditoría
            AuditLog.objects.create(
                user=company_user,
                action='UPD',
                model_name='SupportTicket',
                object_id=ticket.id,
                details=f"Support ticket updated: {ticket.title}",
                ip_address=get_client_ip(request)
            )
            
            messages.success(request, 'Ticket actualizado exitosamente.')
    
    return redirect('support_ticket_detail', pk=ticket.pk)

@login_required
@user_passes_test(is_admin)
def backup_database(request):
    """
    Vista para crear backup manual de la base de datos
    """
    if request.method == 'POST':
        try:
            # Crear directorio de backups si no existe
            if not os.path.exists(settings.BACKUP_PATH):
                os.makedirs(settings.BACKUP_PATH)
                print(f"Directorio de backups creado: {settings.BACKUP_PATH}")
            
            # Nombre del archivo de backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{timestamp}.zip"
            backup_path = os.path.join(settings.BACKUP_PATH, backup_filename)
            
            print(f"Creando backup en: {backup_path}")
            
            # Crear archivo ZIP
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Backup de la base de datos SQLite
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path):
                    # Usar el nombre de archivo correcto para la base de datos
                    zipf.write(db_path, 'db.sqlite3')
                    print(f"Base de datos agregada al backup: {db_path}")
                else:
                    print(f"Advertencia: No se encontró la base de datos en {db_path}")
                
                # Backup de archivos media si existen
                if hasattr(settings, 'MEDIA_ROOT') and os.path.exists(settings.MEDIA_ROOT):
                    for root, dirs, files in os.walk(settings.MEDIA_ROOT):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Crear una ruta relativa para el archivo en el ZIP
                            arcname = os.path.join('media', os.path.relpath(file_path, settings.MEDIA_ROOT))
                            zipf.write(file_path, arcname)
                    print("Archivos media agregados al backup")
            
            # Verificar que el backup se creó correctamente
            if os.path.exists(backup_path):
                file_size = os.path.getsize(backup_path)
                messages.success(request, f'Backup creado exitosamente: {backup_filename} ({file_size} bytes)')
                print(f"Backup creado exitosamente: {backup_path} ({file_size} bytes)")
            else:
                messages.error(request, 'Error: El archivo de backup no se creó')
                print("Error: El archivo de backup no se creó")
            
        except Exception as e:
            error_msg = f'Error al crear backup: {str(e)}'
            messages.error(request, error_msg)
            print(f"Error en backup: {error_msg}")
            import traceback
            print(traceback.format_exc())
    
    # Redirigir de vuelta a la página de reportes
    return redirect('reports_dashboard')

@login_required
@user_passes_test(is_admin)
def backup_list(request):
    """
    Vista para listar backups disponibles
    """
    backups = []
    backup_dir = settings.BACKUP_PATH
    
    # Verificar que el directorio existe
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
        messages.info(request, f'Directorio de backups creado: {backup_dir}')
    
    try:
        # Listar archivos de backup
        for filename in os.listdir(backup_dir):
            if filename.endswith('.zip') and filename.startswith('backup_'):
                filepath = os.path.join(backup_dir, filename)
                file_info = {
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'size_mb': round(os.path.getsize(filepath) / (1024 * 1024), 2),
                    'created': datetime.fromtimestamp(os.path.getctime(filepath)),
                    'path': filepath,
                    'url': f'/media/backups/{filename}'  # Para descarga futura
                }
                backups.append(file_info)
        
        # Ordenar por fecha de creación (más reciente primero)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
    except Exception as e:
        messages.error(request, f'Error al listar backups: {str(e)}')
        backups = []
    
    context = {
        'backups': backups,
        'backup_dir': backup_dir,
        'backup_count': len(backups)
    }
    return render(request, 'backup_list.html', context)

@login_required
@user_passes_test(is_admin)
def download_backup(request, filename):
    """
    Vista para descargar un backup específico
    """
    try:
        # Validar el nombre del archivo por seguridad
        if not filename.endswith('.zip') or not filename.startswith('backup_'):
            messages.error(request, 'Nombre de archivo inválido')
            return redirect('backup_list')
        
        backup_path = os.path.join(settings.BACKUP_PATH, filename)
        
        if not os.path.exists(backup_path):
            messages.error(request, f'Backup no encontrado: {filename}')
            return redirect('backup_list')
        
        # Crear respuesta de descarga
        with open(backup_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            return response
            
    except Exception as e:
        messages.error(request, f'Error al descargar backup: {str(e)}')
        return redirect('backup_list')

@login_required
@user_passes_test(is_admin)
def delete_backup(request, filename):
    """
    Vista para eliminar un backup específico
    """
    if request.method == 'POST':
        try:
            # Validar el nombre del archivo por seguridad
            if not filename.endswith('.zip') or not filename.startswith('backup_'):
                messages.error(request, 'Nombre de archivo inválido')
                return redirect('backup_list')
            
            backup_path = os.path.join(settings.BACKUP_PATH, filename)
            
            if not os.path.exists(backup_path):
                messages.error(request, f'Backup no encontrado: {filename}')
                return redirect('backup_list')
            
            # Eliminar el archivo
            os.remove(backup_path)
            messages.success(request, f'Backup eliminado: {filename}')
            
        except Exception as e:
            messages.error(request, f'Error al eliminar backup: {str(e)}')
    
    return redirect('backup_list')

def get_or_create_companyuser(user):
    """
    Obtener el CompanyUser asociado a un usuario, o crearlo si no existe
    """
    try:
        return user.companyuser
    except CompanyUser.DoesNotExist:
        # Crear un CompanyUser por defecto
        company_user = CompanyUser.objects.create(
            user=user,
            department='IT',  # Departamento por defecto
            phone='000-000-0000',  # Teléfono por defecto
            email=f'{user.username}@tuempresa.com'  # Email por defecto
        )
        return company_user
    
def register(request):
    """
    Vista para registro de nuevos usuarios
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            
            # Crear CompanyUser asociado
            CompanyUser.objects.create(
                user=user,
                department=form.cleaned_data['department'],
                phone=form.cleaned_data['phone'],
                email=form.cleaned_data['email']
            )
            
            messages.success(request, '¡Cuenta creada exitosamente! Ya puedes iniciar sesión.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})