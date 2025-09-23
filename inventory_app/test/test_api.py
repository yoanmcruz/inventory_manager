 from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth.models import User
from django.urls import reverse
from ..models import CompanyUser, Equipment

class APITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
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
        
        self.equipment = Equipment.objects.create(
            type='LAP', brand='Dell', model='XPS 13',
            serial_number='TEST123', purchase_date='2023-01-01',
            location='Office 101', status='AVA'
        )
    
    def test_api_equipment_list(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get('/api/v1/equipment/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)
    
    def test_api_equipment_detail(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(f'/api/v1/equipment/{self.equipment.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['brand'], 'Dell')
