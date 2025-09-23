 from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import CompanyUser, Equipment

class ViewTestCase(TestCase):
    def setUp(self):
        self.client = Client()
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
        
        # Crear equipo de prueba
        self.equipment = Equipment.objects.create(
            type='LAP',
            brand='Dell',
            model='XPS 13',
            serial_number='TEST123456',
            purchase_date='2023-01-01',
            location='Office 101',
            status='AVA'
        )
    
    def test_dashboard_access(self):
        self.client.login(username='testuser', password='Testpass123!')
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Dashboard')
    
    def test_equipment_list_access(self):
        self.client.login(username='testuser', password='Testpass123!')
        response = self.client.get(reverse('equipment_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Gestión de Equipos')
    
    def test_api_authentication(self):
        # Test que la API requiere autenticación
        response = self.client.get('/api/v1/equipment/')
        self.assertEqual(response.status_code, 403)  # Forbidden
