from .models import CompanyUser

class CompanyUserMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Asegurar que cada usuario autenticado tenga un CompanyUser
        if request.user.is_authenticated:
            try:
                # Intentar acceder al companyuser para forzar la creación si no existe
                request.user.companyuser
            except CompanyUser.DoesNotExist:
                # Crear CompanyUser por defecto
                CompanyUser.objects.create(
                    user=request.user,
                    department='IT',
                    phone='000-000-0000',
                    email=f'{request.user.username}@tuempresa.com'
                )
        
        response = self.get_response(request)
        return response
    
class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        # Headers de seguridad
        response['X-Content-Type-Options'] = 'nosniff'
        response['X-Frame-Options'] = 'DENY'
        response['X-XSS-Protection'] = '1; mode=block'
        response['Referrer-Policy'] = 'same-origin'
        
        return response
