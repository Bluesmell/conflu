
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from .models import Space
# from guardian.shortcuts import assign_perm, remove_perm # Not directly used in these tests

class SpaceAPITests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(username='user1', password='password123')
        cls.user2 = User.objects.create_user(username='user2', password='password123')

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType
        # from .models import Space as WorkspaceSpace # Alias not needed if Space is clear

        content_type = ContentType.objects.get_for_model(Space)
        permissions_to_add = []
        for codename in ['add_space', 'change_space', 'delete_space']:
            try:
                perm = Permission.objects.get(content_type=content_type, codename=codename)
                permissions_to_add.append(perm)
            except Permission.DoesNotExist:
                print(f"DEBUG: Warning: {{codename}} permission for Space not found.")

        if permissions_to_add:
            cls.user1.user_permissions.add(*permissions_to_add)

    def setUp(self):
        # Users are created in setUpTestData
        self.client = APIClient()
        self.client.force_authenticate(user=self.user1)
        self.space1_data = dict(key='SPACE1', name='Space One') # Using dict()

        response = self.client.post(reverse('space-list'), self.space1_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED,
                         f"Failed to create space in setUp. User: {{self.user1.username}}. Response: {{response.data}}")
        self.space1 = Space.objects.get(key='SPACE1')
        self.space1_detail_url = reverse('space-detail', kwargs=dict(key=self.space1.key)) # Using dict()

    def test_owner_can_update_space(self):
        self.client.force_authenticate(user=self.user1)
        update_data = dict(name='Space One Updated') # Using dict()
        response = self.client.patch(self.space1_detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.space1.refresh_from_db()
        self.assertEqual(self.space1.name, 'Space One Updated')

    def test_non_owner_cannot_update_space(self):
        self.client.force_authenticate(user=self.user2)
        update_data = dict(name='Space One Attempted Update by User2') # Using dict()
        response = self.client.patch(self.space1_detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_owner_can_delete_space(self):
        self.client.force_authenticate(user=self.user1)
        response = self.client.delete(self.space1_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.space1.refresh_from_db()
        self.assertTrue(self.space1.is_deleted)

    def test_non_owner_cannot_delete_space(self):
        self.client.force_authenticate(user=self.user2)
        response = self.client.delete(self.space1_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anon_can_list_spaces(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(reverse('space-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anon_can_retrieve_space(self):
        self.client.force_authenticate(user=None)
        response = self.client.get(self.space1_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['key'], self.space1.key)

    def test_unauthenticated_cannot_create_space(self):
        self.client.force_authenticate(user=None)
        response = self.client.post(reverse('space-list'), dict(key='ANON', name='Anon Space'), format='json') # Using dict()
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED) # Expect 401 for unauthenticated POST
