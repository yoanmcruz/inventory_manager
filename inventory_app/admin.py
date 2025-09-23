from django.contrib import admin
from .models import Equipment, MaintenanceLog, CompanyUser, AuditLog, Component

@admin.register(CompanyUser)
class CompanyUserAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'email', 'phone']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'department', 'email']
    list_filter = ['department']

@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ['type', 'brand', 'model', 'serial_number', 'location', 'status', 'assigned_to']
    list_filter = ['type', 'status', 'location', 'purchase_date']
    search_fields = ['brand', 'model', 'serial_number', 'location']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'purchase_date'

@admin.register(Component)
class ComponentAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'component_type', 'brand', 'model', 'serial_number']
    list_filter = ['component_type', 'brand']
    search_fields = ['brand', 'model', 'serial_number', 'equipment__serial_number']
    raw_id_fields = ['equipment']

@admin.register(MaintenanceLog)
class MaintenanceLogAdmin(admin.ModelAdmin):
    list_display = ['equipment', 'maintenance_type', 'title', 'technician', 'start_date', 'priority']
    list_filter = ['maintenance_type', 'priority', 'start_date']
    search_fields = ['equipment__brand', 'equipment__model', 'title', 'technician__user__username']
    readonly_fields = ['created_at']
    date_hierarchy = 'start_date'
    raw_id_fields = ['equipment', 'technician']

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['user', 'action', 'model_name', 'object_id', 'timestamp']
    list_filter = ['action', 'model_name', 'timestamp']
    search_fields = ['user__user__username', 'model_name', 'details']
    readonly_fields = ['user', 'action', 'model_name', 'object_id', 'details', 'timestamp', 'ip_address']
    date_hierarchy = 'timestamp'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
