from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.contrib import messages
from django.db.models import Count, Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from .models import Equipment, MaintenanceLog, CompanyUser, AuditLog, SupportTicket, Component

# =============================================================================
# FILTROS PERSONALIZADOS
# =============================================================================

class WarrantyStatusFilter(admin.SimpleListFilter):
    title = 'Estado de Garantía'
    parameter_name = 'warranty_status'

    def lookups(self, request, model_admin):
        return (
            ('active', 'Garantía Activa'),
            ('expiring', 'Por Expirar (30 días)'),
            ('expired', 'Garantía Expirada'),
            ('none', 'Sin Garantía'),
        )

    def queryset(self, request, queryset):
        today = timezone.now().date()
        if self.value() == 'active':
            return queryset.filter(warranty_expiry__gt=today)
        elif self.value() == 'expiring':
            return queryset.filter(
                warranty_expiry__gt=today,
                warranty_expiry__lte=today + timedelta(days=30)
            )
        elif self.value() == 'expired':
            return queryset.filter(warranty_expiry__lt=today)
        elif self.value() == 'none':
            return queryset.filter(warranty_expiry__isnull=True)

class MaintenanceStatusFilter(admin.SimpleListFilter):
    title = 'Estado de Mantenimiento'
    parameter_name = 'maintenance_status'

    def lookups(self, request, model_admin):
        return (
            ('needs_maintenance', 'Necesita Mantenimiento'),
            ('under_maintenance', 'En Mantenimiento'),
            ('recently_maintained', 'Mantenimiento Reciente'),
        )

    def queryset(self, request, queryset):
        six_months_ago = timezone.now() - timedelta(days=180)
        if self.value() == 'needs_maintenance':
            # Equipos sin mantenimiento en los últimos 6 meses
            return queryset.exclude(
                maintenance_logs__start_date__gt=six_months_ago
            )
        elif self.value() == 'under_maintenance':
            return queryset.filter(
                maintenance_logs__end_date__isnull=True,
                maintenance_logs__start_date__isnull=False
            ).distinct()
        elif self.value() == 'recently_maintained':
            return queryset.filter(
                maintenance_logs__start_date__gt=timezone.now() - timedelta(days=30)
            ).distinct()

# =============================================================================
# ACTION PERSONALIZADAS
# =============================================================================

def export_to_excel(modeladmin, request, queryset):
    """Exportar equipos seleccionados a Excel"""
    import pandas as pd
    from io import BytesIO
    from django.http import HttpResponse
    
    data = []
    for equipment in queryset:
        data.append({
            'Tipo': equipment.get_type_display(),
            'Marca': equipment.brand,
            'Modelo': equipment.model,
            'Número de Serie': equipment.serial_number,
            'Ubicación': equipment.location,
            'Estado': equipment.get_status_display(),
            'Fecha Compra': equipment.purchase_date,
            'Garantía Hasta': equipment.warranty_expiry,
            'Asignado a': str(equipment.assigned_to) if equipment.assigned_to else 'No asignado',
            'Notas': equipment.notes
        })
    
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Equipos', index=False)
    
    output.seek(0)
    response = HttpResponse(
        output.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=equipos_export_{datetime.now().strftime("%Y%m%d_%H%M")}.xlsx'
    return response

export_to_excel.short_description = "Exportar equipos seleccionados a Excel"

def mark_for_maintenance(modeladmin, request, queryset):
    """Marcar equipos para mantenimiento preventivo"""
    for equipment in queryset:
        MaintenanceLog.objects.create(
            equipment=equipment,
            maintenance_type='PRE',
            title='Mantenimiento Preventivo Programado',
            description='Mantenimiento preventivo marcado desde el panel administrativo',
            technician=CompanyUser.objects.first(),  # Técnico por defecto
            start_date=timezone.now(),
            priority='MED'
        )
    messages.success(request, f'{queryset.count()} equipos marcados para mantenimiento preventivo')

mark_for_maintenance.short_description = "Marcar para mantenimiento preventivo"

def bulk_status_update(modeladmin, request, queryset):
    """Actualización masiva de estado de equipos"""
    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        if new_status:
            updated = queryset.update(status=new_status)
            messages.success(request, f'{updated} equipos actualizados al estado: {new_status}')
            return HttpResponseRedirect(request.get_full_path())
    
    return render(request, 'admin/bulk_status_update.html', {
        'equipments': queryset,
        'status_choices': Equipment.STATUS_CHOICES
    })

bulk_status_update.short_description = "Actualizar estado de equipos seleccionados"

# =============================================================================
# ADMINISTRADORES PERSONALIZADOS
# =============================================================================

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = [
        'serial_number', 'brand_model', 'type_display', 'location', 
        'status_badge', 'assigned_to_display', 'warranty_status', 
        'last_maintenance', 'created_ago'
    ]
    list_filter = [
        'type', 'status', 'location', 'purchase_date', 
        WarrantyStatusFilter, MaintenanceStatusFilter
    ]
    search_fields = ['serial_number', 'brand', 'model', 'location', 'notes']
    readonly_fields = ['created_at', 'updated_at', 'equipment_qr']
    list_per_page = 50
    actions = [export_to_excel, mark_for_maintenance, bulk_status_update]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('type', 'brand', 'model', 'serial_number', 'equipment_qr')
        }),
        ('Fechas y Ubicación', {
            'fields': ('purchase_date', 'warranty_expiry', 'location')
        }),
        ('Estado y Asignación', {
            'fields': ('status', 'assigned_to')
        }),
        ('Información Adicional', {
            'fields': ('notes', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    # Campos personalizados para display
    def brand_model(self, obj):
        return f"{obj.brand} {obj.model}"
    brand_model.short_description = 'Equipo'
    brand_model.admin_order_field = 'brand'
    
    def type_display(self, obj):
        return obj.get_type_display()
    type_display.short_description = 'Tipo'
    
    def status_badge(self, obj):
        color_map = {
            'AVA': 'success',
            'INU': 'primary', 
            'REP': 'warning',
            'RET': 'secondary',
            'LOS': 'danger'
        }
        color = color_map.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    status_badge.admin_order_field = 'status'
    
    def assigned_to_display(self, obj):
        return obj.assigned_to if obj.assigned_to else '—'
    assigned_to_display.short_description = 'Asignado a'
    
    def warranty_status(self, obj):
        if obj.warranty_expiry:
            today = timezone.now().date()
            if obj.warranty_expiry < today:
                return format_html('<span style="color: red;">⏰ Expirada</span>')
            elif (obj.warranty_expiry - today).days <= 30:
                return format_html('<span style="color: orange;">⚠️ Por expirar</span>')
            else:
                return format_html('<span style="color: green;">✅ Vigente</span>')
        return '—'
    warranty_status.short_description = 'Garantía'
    
    def last_maintenance(self, obj):
        last = obj.maintenance_logs.order_by('-start_date').first()
        return last.start_date.strftime('%d/%m/%Y') if last else '—'
    last_maintenance.short_description = 'Último Mantenimiento'
    
    def created_ago(self, obj):
        delta = timezone.now() - obj.created_at
        if delta.days > 365:
            return f"{delta.days // 365} años"
        elif delta.days > 30:
            return f"{delta.days // 30} meses"
        else:
            return f"{delta.days} días"
    created_ago.short_description = 'Antigüedad'
    
    def equipment_qr(self, obj):
        # Generar código QR (implementar después)
        return "QR Code will be implemented"
    equipment_qr.short_description = 'Código QR'

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = [
        'equipment_display', 'maintenance_type_badge', 'title_short', 
        'technician_display', 'start_date', 'duration', 'cost_display', 
        'priority_badge'
    ]
    list_filter = ['maintenance_type', 'priority', 'start_date', 'technician']
    search_fields = ['title', 'description', 'equipment__serial_number']
    readonly_fields = ['created_at']
    date_hierarchy = 'start_date'
    
    def equipment_display(self, obj):
        return f"{obj.equipment.brand} {obj.equipment.model} ({obj.equipment.serial_number})"
    equipment_display.short_description = 'Equipo'
    
    def maintenance_type_badge(self, obj):
        color_map = {'REP': 'danger', 'PRE': 'success', 'INC': 'warning'}
        color = color_map.get(obj.maintenance_type, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_maintenance_type_display()
        )
    maintenance_type_badge.short_description = 'Tipo'
    
    def title_short(self, obj):
        return obj.title[:50] + '...' if len(obj.title) > 50 else obj.title
    title_short.short_description = 'Descripción'
    
    def technician_display(self, obj):
        return str(obj.technician)
    technician_display.short_description = 'Técnico'
    
    def duration(self, obj):
        if obj.end_date:
            delta = obj.end_date - obj.start_date
            return str(delta).split('.')[0]  # Remover microsegundos
        return 'En progreso'
    duration.short_description = 'Duración'
    
    def cost_display(self, obj):
        return f"${obj.cost:.2f}" if obj.cost else '—'
    cost_display.short_description = 'Costo'
    
    def priority_badge(self, obj):
        color_map = {'LOW': 'info', 'MED': 'warning', 'HIGH': 'danger'}
        color = color_map.get(obj.priority, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Prioridad'

@admin.register(SupportTicket)
class SupportTicketAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'title_short', 'priority_badge', 'status_badge', 
        'created_by_display', 'assigned_to_display', 'created_ago', 
        'equipment_link'
    ]
    list_filter = ['status', 'priority', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    
    def title_short(self, obj):
        return obj.title[:30] + '...' if len(obj.title) > 30 else obj.title
    title_short.short_description = 'Título'
    
    def priority_badge(self, obj):
        color_map = {'LOW': 'info', 'MED': 'warning', 'HIGH': 'danger', 'CRITICAL': 'dark'}
        color = color_map.get(obj.priority, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_priority_display()
        )
    priority_badge.short_description = 'Prioridad'
    
    def status_badge(self, obj):
        color_map = {
            'OPEN': 'primary', 'IN_PROGRESS': 'warning', 
            'RESOLVED': 'success', 'CLOSED': 'secondary'
        }
        color = color_map.get(obj.status, 'secondary')
        return format_html(
            '<span class="badge bg-{}">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Estado'
    
    def created_by_display(self, obj):
        return str(obj.created_by)
    created_by_display.short_description = 'Creado por'
    
    def assigned_to_display(self, obj):
        return str(obj.assigned_to) if obj.assigned_to else '—'
    assigned_to_display.short_description = 'Asignado a'
    
    def created_ago(self, obj):
        delta = timezone.now() - obj.created_at
        if delta.days == 0:
            return "Hoy"
        elif delta.days == 1:
            return "Ayer"
        else:
            return f"{delta.days} días"
    created_ago.short_description = 'Creado'
    
    def equipment_link(self, obj):
        if obj.equipment:
            url = f"/admin/inventory_app/equipment/{obj.equipment.id}/change/"
            return format_html('<a href="{}">{}</a>', url, obj.equipment)
        return '—'
    equipment_link.short_description = 'Equipo'

# =============================================================================
# DASHBOARD ADMINISTRATIVO PERSONALIZADO
# =============================================================================

class CustomAdminSite(admin.AdminSite):
    site_header = "Sistema de Gestión de Inventario IT"
    site_title = "Admin Inventory IT"
    index_title = "Dashboard de Administración"
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.custom_dashboard), name='custom_dashboard'),
            path('reports/', self.admin_view(self.custom_reports), name='custom_reports'),
            path('analytics/', self.admin_view(self.analytics_dashboard), name='analytics_dashboard'),
        ]
        return custom_urls + urls
    
    def custom_dashboard(self, request):
        # Estadísticas para el dashboard
        stats = {
            'total_equipment': Equipment.objects.count(),
            'equipment_by_status': dict(Equipment.objects.values_list('status').annotate(count=Count('id'))),
            'total_maintenance': MaintenanceLog.objects.count(),
            'open_tickets': SupportTicket.objects.filter(status='OPEN').count(),
            'critical_tickets': SupportTicket.objects.filter(priority='CRITICAL').count(),
        }
        
        # Actividad reciente
        recent_activity = {
            'maintenance_logs': MaintenanceLog.objects.select_related('equipment', 'technician').order_by('-start_date')[:10],
            'recent_tickets': SupportTicket.objects.select_related('created_by', 'equipment').order_by('-created_at')[:10],
            'audit_logs': AuditLog.objects.select_related('user').order_by('-timestamp')[:10],
        }
        
        # Alertas
        alerts = self.generate_alerts()
        
        context = {
            **stats,
            **recent_activity,
            'alerts': alerts,
            'title': 'Dashboard de Administración'
        }
        return render(request, 'admin/custom_dashboard.html', context)
    
    def custom_reports(self, request):
        # Lógica para reportes personalizados
        context = {
            'title': 'Reportes Avanzados'
        }
        return render(request, 'admin/custom_reports.html', context)
    
    def analytics_dashboard(self, request):
        # Lógica para analytics
        context = {
            'title': 'Analítica Avanzada'
        }
        return render(request, 'admin/analytics_dashboard.html', context)
    
    def generate_alerts(self):
        alerts = []
        today = timezone.now().date()
        
        # Equipos con garantía por expirar
        expiring_warranty = Equipment.objects.filter(
            warranty_expiry__isnull=False,
            warranty_expiry__range=[today, today + timedelta(days=30)]
        )
        if expiring_warranty.exists():
            alerts.append({
                'type': 'warning',
                'message': f'{expiring_warranty.count()} equipos con garantía por expirar en 30 días',
                'count': expiring_warranty.count()
            })
        
        # Tickets críticos sin asignar
        critical_unassigned = SupportTicket.objects.filter(
            priority='CRITICAL', 
            assigned_to__isnull=True
        )
        if critical_unassigned.exists():
            alerts.append({
                'type': 'danger',
                'message': f'{critical_unassigned.count()} tickets críticos sin asignar',
                'count': critical_unassigned.count()
            })
        
        # Mantenimientos atrasados
        overdue_maintenance = MaintenanceLog.objects.filter(
            end_date__isnull=True,
            start_date__lt=timezone.now() - timedelta(days=7)
        )
        if overdue_maintenance.exists():
            alerts.append({
                'type': 'info',
                'message': f'{overdue_maintenance.count()} mantenimientos atrasados',
                'count': overdue_maintenance.count()
            })
        
        return alerts

# Reemplazar el admin site por defecto
custom_admin_site = CustomAdminSite(name='custom_admin')

# Re-registrar los modelos con el custom admin
custom_admin_site.register(Equipment, EquipmentAdmin)
custom_admin_site.register(MaintenanceLog, MaintenanceLogAdmin)
custom_admin_site.register(SupportTicket, SupportTicketAdmin)
custom_admin_site.register(CompanyUser)
custom_admin_site.register(AuditLog)
custom_admin_site.register(Component)