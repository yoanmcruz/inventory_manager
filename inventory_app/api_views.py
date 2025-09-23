from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db import models
from django.utils import timezone
from .models import Equipment, MaintenanceLog, CompanyUser, SupportTicket
from .serializers import EquipmentSerializer, MaintenanceLogSerializer, SupportTicketSerializer

# Definir la función helper FUERA de las clases
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

class EquipmentViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar equipos
    """
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type', 'status', 'location']
    search_fields = ['brand', 'model', 'serial_number', 'location']
    ordering_fields = ['purchase_date', 'created_at', 'updated_at']
    ordering = ['-created_at']
    
    def get_queryset(self):
        queryset = super().get_queryset().select_related('assigned_to')
        
        query = self.request.query_params.get('q')
        if query:
            queryset = queryset.filter(
                models.Q(brand__icontains=query) | 
                models.Q(model__icontains=query) | 
                models.Q(serial_number__icontains=query) |
                models.Q(location__icontains=query)
            )
            
        return queryset
    
    def perform_create(self, serializer):
        equipment = serializer.save()
        
        # Obtener o crear CompanyUser para el usuario actual
        company_user = get_or_create_companyuser(self.request.user)
        
        # Registrar en auditoría
        try:
            from .models import AuditLog
            AuditLog.objects.create(
                user=company_user,
                action='CRE',
                model_name='Equipment',
                object_id=equipment.id,
                details=f"Equipment created via API: {equipment}",
            )
        except:
            pass
    
    @action(detail=True, methods=['get'])
    def maintenance_logs(self, request, pk=None):
        equipment = self.get_object()
        logs = equipment.maintenance_logs.all().select_related('technician')
        page = self.paginate_queryset(logs)
        
        if page is not None:
            serializer = MaintenanceLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
            
        serializer = MaintenanceLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        from django.db.models import Count
        stats = {
            'total': self.get_queryset().count(),
            'by_status': dict(self.get_queryset().values_list('status').annotate(count=Count('id'))),
            'by_type': dict(self.get_queryset().values_list('type').annotate(count=Count('id'))),
        }
        return Response(stats)

class MaintenanceLogViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar registros de mantenimiento
    """
    queryset = MaintenanceLog.objects.all()
    serializer_class = MaintenanceLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['maintenance_type', 'priority', 'technician']
    search_fields = ['title', 'description', 'equipment__serial_number']
    ordering_fields = ['start_date', 'end_date', 'created_at']
    ordering = ['-start_date']
    
    def get_queryset(self):
        return super().get_queryset().select_related('equipment', 'technician')
    
    def perform_create(self, serializer):
        # Obtener o crear CompanyUser para el usuario actual
        company_user = get_or_create_companyuser(self.request.user)
        maintenance = serializer.save(technician=company_user)
        
        # Registrar en auditoría
        try:
            from .models import AuditLog
            AuditLog.objects.create(
                user=company_user,
                action='CRE',
                model_name='MaintenanceLog',
                object_id=maintenance.id,
                details=f"Maintenance created via API: {maintenance.title}",
            )
        except:
            pass
    
    @action(detail=False, methods=['get'])
    def recent(self, request):
        recent_logs = self.get_queryset()[:10]
        serializer = self.get_serializer(recent_logs, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        maintenance = self.get_object()
        maintenance.end_date = timezone.now()
        maintenance.save()
        
        serializer = self.get_serializer(maintenance)
        return Response(serializer.data)

class SupportTicketViewSet(viewsets.ModelViewSet):
    """
    API endpoint para gestionar tickets de soporte
    """
    queryset = SupportTicket.objects.all()
    serializer_class = SupportTicketSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'priority', 'assigned_to']
    search_fields = ['title', 'description']
    ordering_fields = ['created_at', 'updated_at', 'priority']
    ordering = ['-created_at']
    
    def get_queryset(self):
        return super().get_queryset().select_related('created_by', 'assigned_to', 'equipment')
    
    def perform_create(self, serializer):
        # Obtener o crear CompanyUser para el usuario actual
        company_user = get_or_create_companyuser(self.request.user)
        ticket = serializer.save(created_by=company_user)
        
        # Registrar en auditoría
        try:
            from .models import AuditLog
            AuditLog.objects.create(
                user=company_user,
                action='CRE',
                model_name='SupportTicket',
                object_id=ticket.id,
                details=f"Support ticket created via API: {ticket.title}",
            )
        except:
            pass
    
    @action(detail=True, methods=['post'])
    def assign(self, request, pk=None):
        ticket = self.get_object()
        technician_id = request.data.get('technician_id')
        
        if technician_id:
            try:
                technician = CompanyUser.objects.get(id=technician_id)
                ticket.assigned_to = technician
                ticket.save()
                
                # Registrar en auditoría
                try:
                    from .models import AuditLog
                    AuditLog.objects.create(
                        user=get_or_create_companyuser(self.request.user),
                        action='ASS',
                        model_name='SupportTicket',
                        object_id=ticket.id,
                        details=f"Ticket assigned to {technician}",
                    )
                except:
                    pass
                    
                return Response({'status': 'ticket assigned'})
            except CompanyUser.DoesNotExist:
                return Response({'error': 'Technician not found'}, status=400)
        
        return Response({'error': 'technician_id required'}, status=400)
    
    @action(detail=True, methods=['post'])
    def close(self, request, pk=None):
        ticket = self.get_object()
        resolution = request.data.get('resolution', '')
        
        ticket.status = 'CLOSED'
        ticket.resolution = resolution
        ticket.save()
        
        return Response({'status': 'ticket closed'})