from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.urls import reverse
from .models import Page, PageVersion, Tag
from workspaces.models import Space
from guardian.shortcuts import assign_perm, get_perms
from guardian.utils import get_anonymous_user # For assigning perms to anonymous user

class PageAPIPermissionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create_user(username='pageowner', password='password123')
        cls.user2 = User.objects.create_user(username='otheruser', password='password123')

        from django.contrib.auth.models import Permission
        from django.contrib.contenttypes.models import ContentType

        space_content_type = ContentType.objects.get_for_model(Space)
        try:
            add_space_perm = Permission.objects.get(content_type=space_content_type, codename='add_space')
            cls.user1.user_permissions.add(add_space_perm)
        except Permission.DoesNotExist:
            print(f"DEBUG: Warning: add_space permission for Space model not found.")

        cls.space = Space.objects.create(key='PAGESPACE', name='Page Test Space', owner=cls.user1)

        page_model_content_type = ContentType.objects.get_for_model(Page)
        page_perms_to_add = []
        for codename in ['add_page', 'change_page', 'delete_page', 'view_page']: # Ensure view_page model perm for owner too
            try:
                perm = Permission.objects.get(content_type=page_model_content_type, codename=codename)
                page_perms_to_add.append(perm)
            except Permission.DoesNotExist:
                print(f"DEBUG: Warning: {codename} permission for Page not found.")
        if page_perms_to_add:
            cls.user1.user_permissions.add(*page_perms_to_add)

    def setUp(self):
        self.client_user1 = APIClient()
        self.client_user1.force_authenticate(user=self.user1)

        self.client_user2 = APIClient()
        self.client_user2.force_authenticate(user=self.user2)

        self.anon_client = APIClient()

        self.page_data_v1 = {
            'space': self.space.pk, 'title': 'User1 Page V1',
            'raw_content': {'type': 'doc', 'content': [{'type': 'paragraph', 'text': 'Content V1'}]}
        }
        response_create = self.client_user1.post(reverse('page-list'), self.page_data_v1, format='json')

        error_message = ""
        if response_create.status_code != status.HTTP_201_CREATED:
            try:
                error_message = response_create.json()
            except Exception:
                error_message = response_create.content
        self.assertEqual(response_create.status_code, status.HTTP_201_CREATED,
                         f"Failed to create page in setUp. User: {self.user1.username}. Response: {error_message}")
        self.page1 = Page.objects.get(pk=response_create.data['id'])
        self.page1_detail_url = reverse('page-detail', kwargs={'pk': self.page1.pk})

    def test_author_can_update_page(self):
        update_data = {
            'title': 'User1 Page V1 Updated',
            'raw_content': {'type': 'doc', 'content': [{'type': 'paragraph', 'text': 'Content V1 Updated'}]},
            'space': self.space.pk
        }
        response = self.client_user1.put(self.page1_detail_url, update_data, format='json')
        if response.status_code != status.HTTP_200_OK:
            try:
                print(f"DEBUG: test_author_can_update_page failed. Status: {response.status_code}. Data: {response.json()}")
            except Exception as e_print:
                print(f"DEBUG: test_author_can_update_page failed. Status: {response.status_code}. Error printing response.json(): {e_print}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_author_cannot_update_page(self):
        update_data = {'title': 'Attempted Update by User2'}
        response = self.client_user2.patch(self.page1_detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_delete_page(self):
        response = self.client_user1.delete(self.page1_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_non_author_cannot_delete_page(self):
        response = self.client_user2.delete(self.page1_detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_add_tag_to_page(self):
        # print(f"DEBUG (add_tag): User {self.user1.username} model-level 'pages.change_page': {self.user1.has_perm('pages.change_page')}")
        # print(f"DEBUG (add_tag): User {self.user1.username} object-level 'pages.change_page' for page {self.page1.pk}: {self.user1.has_perm('pages.change_page', self.page1)}")
        # print(f"DEBUG (add_tag): All object perms for user {self.user1.username} on page {self.page1.pk}: {get_perms(self.user1, self.page1)}")
        add_tag_url = reverse('page-add-page-tag', kwargs={'pk': self.page1.pk})
        response = self.client_user1.post(add_tag_url, {'tag': 'authortag'}, format='json')
        if response.status_code != status.HTTP_200_OK:
            try:
                print(f"DEBUG: test_author_can_add_tag_to_page failed. Status: {response.status_code}. Data: {response.json()}")
            except Exception as e_print:
                print(f"DEBUG: test_author_can_add_tag_to_page failed. Status: {response.status_code}. Error printing response.json(): {e_print}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_author_cannot_add_tag_to_page(self):
        add_tag_url = reverse('page-add-page-tag', kwargs={'pk': self.page1.pk})
        response = self.client_user2.post(add_tag_url, {'tag': 'nonauthortag'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_remove_tag_from_page(self):
        tag = Tag.objects.create(name='testremovetag')
        self.page1.tags.add(tag)
        remove_tag_url = reverse('page-remove-page-tag', kwargs={'pk': self.page1.pk, 'tag_pk_or_name': tag.name})
        response = self.client_user1.delete(remove_tag_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_author_cannot_remove_tag_from_page(self):
        tag = Tag.objects.create(name='testremovetag2')
        self.page1.tags.add(tag)
        remove_tag_url = reverse('page-remove-page-tag', kwargs={'pk': self.page1.pk, 'tag_pk_or_name': tag.name})
        response = self.client_user2.delete(remove_tag_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_author_can_revert_page(self):
        response_v2_data = {'title': 'User1 Page V2',
                            'raw_content': {'type': 'doc', 'text': 'V2'},
                            'space': self.space.pk}
        response_v2 = self.client_user1.put(self.page1_detail_url, response_v2_data, format='json')

        v2_creation_error_message = ""
        if response_v2.status_code != status.HTTP_200_OK:
            try:
                v2_creation_error_message = response_v2.json()
            except:
                v2_creation_error_message = response_v2.content
        self.assertEqual(response_v2.status_code, status.HTTP_200_OK,
                         f"Failed to create V2 for revert test. Status: {response_v2.status_code}. Data: {v2_creation_error_message}")

        # print(f"DEBUG (revert): User {self.user1.username} model-level 'pages.change_page': {self.user1.has_perm('pages.change_page')}")
        # print(f"DEBUG (revert): User {self.user1.username} object-level 'pages.change_page' for page {self.page1.pk}: {self.user1.has_perm('pages.change_page', self.page1)}")
        # print(f"DEBUG (revert): All object perms for user {self.user1.username} on page {self.page1.pk}: {get_perms(self.user1, self.page1)}")
        revert_url = reverse('page-revert', kwargs={'pk': self.page1.pk, 'version_number_str': '1'})
        response = self.client_user1.post(revert_url, format='json')
        if response.status_code != status.HTTP_200_OK:
            try:
                print(f"DEBUG: test_author_can_revert_page (revert action) failed. Status: {response.status_code}. Data: {response.json()}")
            except Exception as e_print:
                print(f"DEBUG: test_author_can_revert_page (revert action) failed. Status: {response.status_code}. Error printing response.json(): {e_print}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_non_author_cannot_revert_page(self):
        response_v2_data = {'title': 'User1 Page V2 again',
                            'raw_content': {'type': 'doc', 'text': 'V2 again'},
                            'space': self.space.pk}
        response_v2 = self.client_user1.put(self.page1_detail_url, response_v2_data, format='json')

        v2_creation_error_message = ""
        if response_v2.status_code != status.HTTP_200_OK:
            try:
                v2_creation_error_message = response_v2.json()
            except:
                v2_creation_error_message = response_v2.content
        self.assertEqual(response_v2.status_code, status.HTTP_200_OK,
                         f"Failed to create V2 for non-author revert test. Status: {response_v2.status_code}. Data: {v2_creation_error_message}")
        revert_url = reverse('page-revert', kwargs={'pk': self.page1.pk, 'version_number_str': '1'})
        response = self.client_user2.post(revert_url, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anon_can_list_pages(self):
        response = self.anon_client.get(reverse('page-list'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_anon_can_retrieve_page(self):
        # To allow anonymous to view this specific page, assign permission
        anonymous_user = get_anonymous_user()
        assign_perm('pages.view_page', anonymous_user, self.page1)

        response = self.anon_client.get(self.page1_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_unauthenticated_cannot_create_page(self):
        response = self.anon_client.post(reverse('page-list'), self.page_data_v1, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
