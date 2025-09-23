# inventory_app/management/commands/create_companyusers.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from inventory_app.models import CompanyUser

class Command(BaseCommand):
    help = 'Create CompanyUser for all existing users without one'
    
    def handle(self, *args, **options):
        users_without_companyuser = User.objects.filter(companyuser__isnull=True)
        
        for user in users_without_companyuser:
            CompanyUser.objects.create(
                user=user,
                department='IT',
                phone='000-000-0000',
                email=f'{user.username}@tuempresa.com'
            )
            self.stdout.write(
                self.style.SUCCESS(f'Created CompanyUser for {user.username}')
            )
        
        self.stdout.write(
            self.style.SUCCESS(f'Created CompanyUser for {users_without_companyuser.count()} users')
        )