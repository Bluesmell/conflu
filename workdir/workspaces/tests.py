from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .models import Space

User = get_user_model()

class SpaceAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123', email='test@example.com')
        self.client.login(username='testuser', password='testpassword123')
        self.space_data = {'key': 'TEST', 'name': 'Test Space', 'description': 'A test space.'}
        self.space_list_url = reverse('space-list')

    def test_create_space(self):
        response = self.client.post(self.space_list_url, self.space_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertEqual(Space.objects.count(), 1)
        created_space = Space.objects.get()
        self.assertEqual(created_space.name, self.space_data['name'])
        self.assertEqual(created_space.owner, self.user)

    def test_list_spaces(self):
        Space.objects.create(key='TEST1', name='Test Space 1', owner=self.user)
        Space.objects.create(key='TEST2', name='Test Space 2', owner=self.user)
        response = self.client.get(self.space_list_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data.get('results', [])), 2)

    def test_retrieve_space(self):
        space = Space.objects.create(key='TESTRET', name='Test Retrieve Space', owner=self.user)
        detail_url = reverse('space-detail', kwargs={'key': space.key})
        response = self.client.get(detail_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], space.name)

    def test_update_space(self):
        space = Space.objects.create(key='TESTUPD', name='Test Update Space', owner=self.user)
        detail_url = reverse('space-detail', kwargs={'key': space.key})
        updated_data = {'name': 'Updated Space Name', 'description': 'Updated description.'}
        response = self.client.patch(detail_url, updated_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        space.refresh_from_db()
        self.assertEqual(space.name, updated_data['name'])

    def test_soft_delete_space(self):
        space = Space.objects.create(key='TESTDEL', name='Test Delete Space', owner=self.user)
        detail_url = reverse('space-detail', kwargs={'key': space.key})
        response = self.client.delete(detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Space.objects.get(pk=space.pk).is_deleted)
        list_response = self.client.get(self.space_list_url)
        self.assertEqual(len(list_response.data.get('results', [])), 0)

    def test_unauthenticated_access_to_create_space(self):
        self.client.logout()
        response = self.client.post(self.space_list_url, self.space_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
