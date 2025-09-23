 
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q

class CompanyEmailBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = User.objects.get(
                Q(username=username) | 
                Q(email=username) |
                Q(companyuser__email=username)
            )
            
            if user.check_password(password):
                # Verificar que el email sea del dominio empresarial
                email = getattr(user, 'email', '')
                if hasattr(user, 'companyuser'):
                    email = user.companyuser.email
                
                if email.endswith('@tuempresa.com'):
                    return user
        except User.DoesNotExist:
            return None
        except Exception as e:
            return None
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None