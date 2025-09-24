from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from inventory_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),
    
    # URLs de autenticación estándar
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/register/', views.register, name='register'),
    path('accounts/password-reset/', 
         auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'), 
         name='password_reset'),
    
    # URLs de la aplicación
    path('inventory/', include('inventory_app.urls')),
    
    # URLs de API - incluir solo una vez
    path('', include('inventory_app.api_urls')),
    
    # URLs de autenticación API (solo si es necesario)
    # path('api-auth/', include('rest_framework.urls', namespace='rest_framework')),
]