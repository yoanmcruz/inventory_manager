from django.db import models
from django.contrib.auth.models import User
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.utils import timezone

def validate_company_email(value):
    if not value.endswith('@tuempresa.com'):
        raise ValidationError('Solo se permiten emails del dominio @tuempresa.com')

class CompanyUser(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100)
    phone = models.CharField(max_length=20)
    email = models.EmailField(unique=True, validators=[validate_company_email])
    
    def __str__(self):
        return f"{self.user.first_name} {self.user.last_name} ({self.department})"

class Equipment(models.Model):
    EQUIPMENT_TYPES = (
        ('LAP', 'Laptop'),
        ('DES', 'Desktop'),
        ('MON', 'Monitor'),
        ('PRI', 'Printer'),
        ('NET', 'Network Device'),
        ('SER', 'Server'),
        ('PHO', 'Phone'),
        ('TAB', 'Tablet'),
        ('OTH', 'Other'),
    )
    
    STATUS_CHOICES = (
        ('AVA', 'Available'),
        ('INU', 'In Use'),
        ('REP', 'In Repair'),
        ('RET', 'Retired'),
        ('LOS', 'Lost'),
        ('DIS', 'Disposed'),
    )
    
    type = models.CharField(max_length=3, choices=EQUIPMENT_TYPES)
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    serial_number = models.CharField(max_length=100, unique=True)
    purchase_date = models.DateField()
    warranty_expiry = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=100)
    status = models.CharField(max_length=3, choices=STATUS_CHOICES, default='AVA')
    assigned_to = models.ForeignKey(CompanyUser, on_delete=models.SET_NULL, null=True, blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.brand} {self.model} ({self.serial_number})"

class Component(models.Model):
    equipment = models.ForeignKey(Equipment, related_name='components', on_delete=models.CASCADE)
    component_type = models.CharField(max_length=50)
    brand = models.CharField(max_length=50)
    model = models.CharField(max_length=50)
    serial_number = models.CharField(max_length=100, blank=True)
    specifications = models.TextField(blank=True)
    installed_date = models.DateField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.component_type} - {self.brand} {self.model}"

class MaintenanceLog(models.Model):
    MAINTENANCE_TYPES = (
        ('REP', 'Repair'),
        ('PRE', 'Preventive Maintenance'),
        ('INC', 'Incident'),
        ('UPD', 'Update/Upgrade'),
        ('INS', 'Installation'),
        ('CON', 'Configuration'),
    )
    
    PRIORITY_CHOICES = (
        ('HIG', 'High'),
        ('MED', 'Medium'),
        ('LOW', 'Low'),
    )
    
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, related_name='maintenance_logs')
    maintenance_type = models.CharField(max_length=3, choices=MAINTENANCE_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    technician = models.ForeignKey(CompanyUser, on_delete=models.CASCADE)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    parts_used = models.TextField(blank=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    priority = models.CharField(max_length=3, choices=PRIORITY_CHOICES, default='MED')
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-start_date']
    
    def __str__(self):
        return f"{self.get_maintenance_type_display()} - {self.equipment} - {self.title}"

class AuditLog(models.Model):
    ACTION_CHOICES = (
        ('CRE', 'Created'),
        ('UPD', 'Updated'),
        ('DEL', 'Deleted'),
        ('ASS', 'Assigned'),
        ('UNS', 'Unassigned'),
        ('REP', 'Repaired'),
        ('MOV', 'Moved'),
        ('STA', 'Status Changed'),
    )
    
    user = models.ForeignKey(CompanyUser, on_delete=models.CASCADE)
    action = models.CharField(max_length=3, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=50)
    object_id = models.PositiveIntegerField()
    details = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.user} - {self.get_action_display()} - {self.model_name} at {self.timestamp}"

class SupportTicket(models.Model):
    PRIORITY_CHOICES = (
        ('LOW', 'Baja'),
        ('MED', 'Media'),
        ('HIGH', 'Alta'),
        ('CRITICAL', 'Crítica'),
    )
    
    STATUS_CHOICES = (
        ('OPEN', 'Abierto'),
        ('IN_PROGRESS', 'En Progreso'),
        ('RESOLVED', 'Resuelto'),
        ('CLOSED', 'Cerrado'),
    )
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    created_by = models.ForeignKey(CompanyUser, on_delete=models.CASCADE, related_name='created_tickets')
    assigned_to = models.ForeignKey(CompanyUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='MED')
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='OPEN')
    equipment = models.ForeignKey(Equipment, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolution = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {self.get_status_display()}"