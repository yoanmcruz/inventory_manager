from rest_framework import serializers
from .models import Equipment, MaintenanceLog, CompanyUser, SupportTicket

class CompanyUserSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source='user.get_full_name', read_only=True)
    email = serializers.CharField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = CompanyUser
        fields = ['id', 'full_name', 'username', 'email', 'department', 'phone']
        read_only_fields = fields

class EquipmentSerializer(serializers.ModelSerializer):
    assigned_to_detail = CompanyUserSerializer(source='assigned_to', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    type_display = serializers.CharField(source='get_type_display', read_only=True)
    
    class Meta:
        model = Equipment
        fields = [
            'id', 'type', 'type_display', 'brand', 'model', 'serial_number',
            'purchase_date', 'warranty_expiry', 'location', 'status', 'status_display',
            'assigned_to', 'assigned_to_detail', 'notes', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class MaintenanceLogSerializer(serializers.ModelSerializer):
    equipment_detail = EquipmentSerializer(source='equipment', read_only=True)
    technician_detail = CompanyUserSerializer(source='technician', read_only=True)
    maintenance_type_display = serializers.CharField(source='get_maintenance_type_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    
    class Meta:
        model = MaintenanceLog
        fields = [
            'id', 'equipment', 'equipment_detail', 'maintenance_type', 'maintenance_type_display',
            'title', 'description', 'technician', 'technician_detail', 'start_date', 'end_date',
            'parts_used', 'cost', 'priority', 'priority_display', 'resolution', 'created_at'
        ]
        read_only_fields = ['created_at']

class SupportTicketSerializer(serializers.ModelSerializer):
    created_by_detail = CompanyUserSerializer(source='created_by', read_only=True)
    assigned_to_detail = CompanyUserSerializer(source='assigned_to', read_only=True)
    equipment_detail = EquipmentSerializer(source='equipment', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    
    class Meta:
        model = SupportTicket
        fields = [
            'id', 'title', 'description', 'priority', 'priority_display', 
            'status', 'status_display', 'created_by', 'created_by_detail',
            'assigned_to', 'assigned_to_detail', 'equipment', 'equipment_detail',
            'resolution', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']