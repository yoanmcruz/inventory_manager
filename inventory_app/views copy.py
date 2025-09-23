from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
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
    # Estadísticas para el dashboard
    total_equipment = Equipment.objects.count()
    available_equipment = Equipment.objects.filter(status='AVA').count()
    in_use_equipment = Equipment.objects.filter(status='INU').count()
    in_repair_equipment = Equipment.objects.filter(status='REP').count()
    
    # Equipos por tipo
    equipment_by_type = Equipment.objects.values('type').annotate(count=Count('id')).order_by('-count')
    
    # Mantenimientos recientes
    recent_maintenance = MaintenanceLog.objects.all().select_related('equipment', 'technician').order_by('-start_date')[:10]
    
    # Costos de mantenimiento por mes
    current_year = timezone.now().year
    maintenance_costs = MaintenanceLog.objects.filter(
        start_date__year=current_year
    ).values('start_date__month').annotate(total_cost=Sum('cost')).order_by('start_date__month')
    
    # Nuevas métricas de tickets
    open_tickets = SupportTicket.objects.filter(status='OPEN').count()
    in_progress_tickets = SupportTicket.objects.filter(status='IN_PROGRESS').count()
    critical_tickets = SupportTicket.objects.filter(priority='CRITICAL', status__in=['OPEN', 'IN_PROGRESS']).count()
    
    # Tickets recientes
    recent_tickets = SupportTicket.objects.all().select_related('created_by', 'assigned_to').order_by('-created_at')[:5]
    
    # Equipos con garantía próxima a vencer (30 días)
    warranty_warning = Equipment.objects.filter(
        warranty_expiry__isnull=False,
        warranty_expiry__range=[timezone.now().date(), timezone.now().date() + timedelta(days=30)]
    ).count()
    
    context = {
        'total_equipment': total_equipment,
        'available_equipment': available_equipment,
        'in_use_equipment': in_use_equipment,
        'in_repair_equipment': in_repair_equipment,
        'equipment_by_type': equipment_by_type,
        'recent_maintenance': recent_maintenance,
        'maintenance_costs': maintenance_costs,
        'open_tickets': open_tickets,
        'in_progress_tickets': in_progress_tickets,
        'critical_tickets': critical_tickets,
        'recent_tickets': recent_tickets,
        'warranty_warning': warranty_warning,
    }
    return render(request, 'dashboard.html', context)

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
        # Registrar en auditoría
        AuditLog.objects.create(
            user=self.request.user.companyuser,
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
        # Registrar en auditoría
        AuditLog.objects.create(
            user=self.request.user.companyuser,
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
        # Registrar en auditoría antes de eliminar
        AuditLog.objects.create(
            user=request.user.companyuser,
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
            maintenance.technician = request.user.companyuser
            maintenance.save()
            
            # Actualizar estado del equipo si es necesario
            if maintenance.maintenance_type == 'REP' and not maintenance.end_date:
                equipment.status = 'REP'
                equipment.save()
            
            # Registrar en auditoría
            AuditLog.objects.create(
                user=request.user.companyuser,
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
    return render(request, 'reports.html')

def register(request):
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
            messages.success(request, 'Account created successfully. You can now log in.')
            return redirect('login')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'registration/register.html', {'form': form})

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
            ticket.created_by = request.user.companyuser
            ticket.save()
            
            # Registrar en auditoría
            AuditLog.objects.create(
                user=request.user.companyuser,
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
@user_passes_test(is_admin)
def support_ticket_update(request, pk):
    ticket = get_object_or_404(SupportTicket, pk=pk)
    
    if request.method == 'POST':
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
            
            # Nombre del archivo de backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{timestamp}.zip"
            backup_path = os.path.join(settings.BACKUP_PATH, backup_filename)
            
            # Crear archivo ZIP
            with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Backup de la base de datos SQLite
                db_path = settings.DATABASES['default']['NAME']
                if os.path.exists(db_path):
                    zipf.write(db_path, os.path.basename(db_path))
            
            messages.success(request, f'Backup creado exitosamente: {backup_filename}')
            
        except Exception as e:
            messages.error(request, f'Error al crear backup: {str(e)}')
    
    return redirect('reports_dashboard')

@login_required
@user_passes_test(is_admin)
def backup_list(request):""" Vista para listar backups disponibles """
    backups = []
    if os.path.exists(settings.BACKUP_PATH):
        for filename in os.listdir(settings.BACKUP_PATH):
            if filename.endswith('.zip'):
                filepath = os.path.join(settings.BACKUP_PATH, filename)
                file_info = {
                    'name': filename,
                    'size': os.path.getsize(filepath),
                    'created': datetime.fromtimestamp(os.path.getctime(filepath)),
                    'path': filepath
                }
                backups.append(file_info)
    
    # Ordenar por fecha de creación (más reciente primero)
    backups.sort(key=lambda x: x['created'], reverse=True)
    
    return render(request, 'backup_list.html', {'backups': backups})