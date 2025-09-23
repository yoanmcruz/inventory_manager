from django.urls import path
from . import views
from .views import EquipmentListView, EquipmentDetailView, EquipmentCreateView, EquipmentUpdateView

urlpatterns = [
    path('equipment/', EquipmentListView.as_view(), name='equipment_list'),
    path('equipment/<int:pk>/', EquipmentDetailView.as_view(), name='equipment_detail'),
    path('equipment/new/', EquipmentCreateView.as_view(), name='equipment_create'),
    path('equipment/<int:pk>/edit/', EquipmentUpdateView.as_view(), name='equipment_edit'),
    path('equipment/<int:pk>/delete/', views.equipment_delete, name='equipment_delete'),
    path('equipment/<int:equipment_id>/maintenance/', views.maintenance_create, name='maintenance_create'),
    path('reports/export/<str:report_type>/', views.export_report, name='export_report'),
    path('reports/', views.reports_dashboard, name='reports_dashboard'),
    path('api/equipment-stats/', views.equipment_stats_api, name='equipment_stats_api'),
    path('api/maintenance-stats/', views.maintenance_stats_api, name='maintenance_stats_api'),
    
    # URLs para tickets de soporte
    path('support/tickets/', views.support_ticket_list, name='support_ticket_list'),
    path('support/tickets/new/', views.support_ticket_create, name='support_ticket_create'),
    path('support/tickets/<int:pk>/', views.support_ticket_detail, name='support_ticket_detail'),
    path('support/tickets/<int:pk>/update/', views.support_ticket_update, name='support_ticket_update'),

    # URLs para backup (NUEVAS)
    path('backup/create/', views.backup_database, name='backup_database'),
    path('backup/list/', views.backup_list, name='backup_list'),
]