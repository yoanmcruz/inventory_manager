 from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from ..models import Equipment, CompanyUser, MaintenanceLog

class ModelTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@tuempresa.com',
            password='Testpass123!'
        )
        self.company_user = CompanyUser.objects.create(
            user=self.user,
            department='IT',
            phone='1234567890',
            email='test@tuempresa.com'
        )
    
    def test_equipment_creation(self):
        equipment = Equipment.objects.create(
            type='LAP',
            brand='Dell',
            model='XPS 13',
            serial_number='TEST123456',
            purchase_date=timezone.now().date(),
            location='Office 101',
            status='AVA'
        )
        self.assertEqual(equipment.brand, 'Dell')
        self.assertEqual(equipment.get_status_display(), 'Available')
    
    def test_maintenance_log_creation(self):
        equipment = Equipment.objects.create(
            type='LAP', brand='Dell', model='XPS 13',
            serial_number='TEST123', purchase_date=timezone.now().date(),
            location='Office 101', status='AVA'
        )
        
        maintenance = MaintenanceLog.objects.create(
            equipment=equipment,
            maintenance_type='REP',
            title='Screen replacement',
            description='Replaced broken screen',
            technician=self.company_user,
            start_date=timezone.now(),
            priority='HIGH'
        )
        
        self.assertEqual(maintenance.title, 'Screen replacement')
        self.assertEqual(maintenance.get_priority_display(), 'High')
