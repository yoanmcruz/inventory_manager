from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.authtoken import views as authtoken_views
from .api_views import EquipmentViewSet, MaintenanceLogViewSet, SupportTicketViewSet

router = DefaultRouter()
router.register(r'equipment', EquipmentViewSet, basename='equipment')
router.register(r'maintenance', MaintenanceLogViewSet, basename='maintenance')
router.register(r'support-tickets', SupportTicketViewSet, basename='supportticket')

# URLs de API con namespace único
urlpatterns = [
    # Endpoints principales
    path('api/v1/', include((router.urls, 'api'), namespace='api_v1')),
    
    # Autenticación por tokens (opcional)
    path('api/v1/auth-token/', authtoken_views.obtain_auth_token, name='api_token_auth'),
    
    # Documentación (futura)
    # path('api/v1/docs/', include_docs_urls(title='Inventory API')),
]