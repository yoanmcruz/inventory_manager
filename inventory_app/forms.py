from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Equipment, MaintenanceLog, CompanyUser, SupportTicket  # Agregar SupportTicket

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        label="Company Email",
        help_text="Must be a @tuempresa.com email address",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'usuario@tuempresa.com'})
    )
    department = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department'})
    )
    phone = forms.CharField(
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone number'})
    )
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'})
    )
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'department', 'phone', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email.endswith('@tuempresa.com'):
            raise forms.ValidationError("Only company email addresses (@tuempresa.com) are allowed.")
        
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
            
        return email

class EquipmentForm(forms.ModelForm):
    class Meta:
        model = Equipment
        fields = ['type', 'brand', 'model', 'serial_number', 'purchase_date', 
                 'warranty_expiry', 'location', 'status', 'assigned_to', 'notes']
        widgets = {
            'type': forms.Select(attrs={'class': 'form-control'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'model': forms.TextInput(attrs={'class': 'form-control'}),
            'serial_number': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'warranty_expiry': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = MaintenanceLog
        fields = ['maintenance_type', 'title', 'description', 'start_date', 'end_date', 
                 'parts_used', 'cost', 'priority', 'resolution']
        widgets = {
            'maintenance_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'start_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'end_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'parts_used': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'cost': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'resolution': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['title', 'description', 'priority', 'equipment']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Título del ticket'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Describe el problema...'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'equipment': forms.Select(attrs={'class': 'form-control'}),
        }

class SupportTicketUpdateForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['assigned_to', 'status', 'resolution']
        widgets = {
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'resolution': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Describe la resolución del problema...'}),
        }
        
class AdvancedReportForm(forms.Form):
    REPORT_TYPES = (
        ('equipment_summary', 'Resumen de Equipos'),
        ('maintenance_costs', 'Costos de Mantenimiento'),
        ('ticket_analysis', 'Análisis de Tickets'),
        ('warranty_status', 'Estado de Garantías'),
        ('performance_metrics', 'Métricas de Performance'),
    )
    
    DATE_RANGES = (
        ('last_7_days', 'Últimos 7 días'),
        ('last_30_days', 'Últimos 30 días'),
        ('last_90_days', 'Últimos 90 días'),
        ('last_year', 'Último año'),
        ('custom', 'Rango Personalizado'),
    )
    
    report_type = forms.ChoiceField(
        choices=REPORT_TYPES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'report_type'})
    )
    
    date_range = forms.ChoiceField(
        choices=DATE_RANGES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'date_range'})
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'start_date'
        })
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control', 
            'type': 'date',
            'id': 'end_date'
        })
    )
    
    equipment_type = forms.MultipleChoiceField(
        choices=Equipment.EQUIPMENT_TYPES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    status_filter = forms.MultipleChoiceField(
        choices=Equipment.STATUS_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    export_format = forms.ChoiceField(
        choices=[('html', 'HTML'), ('pdf', 'PDF'), ('excel', 'Excel'), ('csv', 'CSV')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        date_range = cleaned_data.get('date_range')
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        
        if date_range == 'custom' and (not start_date or not end_date):
            raise forms.ValidationError("Para rango personalizado, debe especificar fecha inicio y fin.")
        
        if start_date and end_date and start_date > end_date:
            raise forms.ValidationError("La fecha de inicio no puede ser mayor a la fecha de fin.")
        
        return cleaned_data