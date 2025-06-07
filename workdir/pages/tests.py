from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase
from django.urls import reverse
from .models import Page, PageVersion, Tag
from workspaces.models import Space

User = get_user_model()

class PageAPITests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpassword123', email='test@example.com')
        self.client.login(username='testuser', password='testpassword123')

        self.space = Space.objects.create(key='TESTSPACE', name='Test Space for Pages', owner=self.user)
        self.page_list_url = reverse('page-list')
        self.raw_content_v1 = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Version 1 content"}]}]}
        self.raw_content_v2 = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Version 2 content"}]}]}
        self.raw_content_v3 = {"type": "doc", "content": [{"type": "paragraph", "content": [{"type": "text", "text": "Version 3 DIFFERENT content"}]}]}

        self.page_data_v1 = {
            'space': self.space.pk,
            'title': 'My Test Page V1',
            'raw_content': self.raw_content_v1,
            'schema_version': 1
        }

    def test_create_page(self):
        response = self.client.post(self.page_list_url, self.page_data_v1, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        # ... (rest of test_create_page unchanged) ...
        created_page = Page.objects.get()
        self.assertEqual(created_page.title, self.page_data_v1['title'])
        self.assertEqual(created_page.author, self.user)
        self.assertEqual(created_page.version, 1)
        self.assertEqual(PageVersion.objects.filter(page=created_page).count(), 1)
        first_version = PageVersion.objects.get(page=created_page, version_number=1)
        self.assertEqual(first_version.raw_content, self.raw_content_v1)
        self.assertEqual(first_version.author, self.user)


    def test_update_page_creates_new_version(self):
        create_response = self.client.post(self.page_list_url, self.page_data_v1, format='json')
        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        page_id = create_response.data['id']
        page_detail_url = reverse('page-detail', kwargs={'pk': page_id})

        update_data = {
            'space': self.space.pk, # Added space to PUT data
            'title': 'My Updated Page Title',
            'raw_content': self.raw_content_v2,
            'commit_message': 'Updated content.'
            # schema_version defaults or can be added if changed
        }
        response = self.client.put(page_detail_url, update_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        updated_page = Page.objects.get(pk=page_id)
        self.assertEqual(updated_page.title, update_data['title'])
        self.assertEqual(updated_page.version, 2)
        self.assertEqual(updated_page.raw_content, self.raw_content_v2)

        self.assertEqual(PageVersion.objects.filter(page=updated_page).count(), 2)
        second_version = PageVersion.objects.get(page=updated_page, version_number=2)
        self.assertEqual(second_version.raw_content, self.raw_content_v2)
        self.assertEqual(second_version.author, self.user)
        self.assertEqual(second_version.commit_message, update_data['commit_message'])

        first_version = PageVersion.objects.get(page=updated_page, version_number=1)
        self.assertEqual(first_version.raw_content, self.raw_content_v1)

    def test_soft_delete_page(self):
        create_response = self.client.post(self.page_list_url, self.page_data_v1, format='json')
        page_id = create_response.data['id']
        page_detail_url = reverse('page-detail', kwargs={'pk': page_id})
        response = self.client.delete(page_detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertTrue(Page.objects.get(pk=page_id).is_deleted)
        list_response = self.client.get(self.page_list_url)
        self.assertEqual(len(list_response.data.get('results', [])), 0)

    def test_add_and_remove_tag_from_page(self):
        create_response = self.client.post(self.page_list_url, self.page_data_v1, format='json')
        page_id = create_response.data['id']

        add_tag_url = reverse('page-manage-tags-add', kwargs={'pk': page_id})
        response_add = self.client.post(add_tag_url, {'tag': 'newtag'}, format='json')
        self.assertEqual(response_add.status_code, status.HTTP_200_OK, response_add.data)
        self.assertEqual(Tag.objects.count(), 1)
        self.assertEqual(Page.objects.get(pk=page_id).tags.count(), 1)

        remove_tag_url = reverse('page-manage-tags-remove', kwargs={'pk': page_id, 'tag_identifier': 'newtag'})
        response_remove = self.client.delete(remove_tag_url)
        self.assertEqual(response_remove.status_code, status.HTTP_200_OK, response_remove.data)
        self.assertEqual(Page.objects.get(pk=page_id).tags.count(), 0)

    def test_revert_page_to_version(self):
        create_response = self.client.post(self.page_list_url, self.page_data_v1, format='json') #v1
        page_id = create_response.data['id']

        page_detail_url = reverse('page-detail', kwargs={'pk': page_id})
        update_data_v2 = {'space': self.space.pk, 'title': 'Page V2 Title', 'raw_content': self.raw_content_v2, 'commit_message': 'Second version'}
        self.client.put(page_detail_url, update_data_v2, format='json') #v2

        update_data_v3 = {'space': self.space.pk, 'title': 'Page V3 Title', 'raw_content': self.raw_content_v3, 'commit_message': 'Third version'}
        self.client.put(page_detail_url, update_data_v3, format='json') #v3
        current_page = Page.objects.get(pk=page_id)
        self.assertEqual(current_page.version, 3)
        self.assertEqual(current_page.raw_content, self.raw_content_v3)

        revert_url = reverse('page-revert', kwargs={'pk': page_id, 'version_number_str': '1'})
        revert_commit_msg = "Reverting to content of v1."
        response_revert = self.client.post(revert_url, {'commit_message': revert_commit_msg}, format='json')
        self.assertEqual(response_revert.status_code, status.HTTP_200_OK, response_revert.data)

        reverted_page = Page.objects.get(pk=page_id)
        self.assertEqual(reverted_page.version, 4)
        self.assertEqual(reverted_page.raw_content, self.raw_content_v1)

        v4 = PageVersion.objects.get(page=reverted_page, version_number=4)
        self.assertEqual(v4.raw_content, self.raw_content_v1)
        self.assertEqual(v4.commit_message, revert_commit_msg)
        self.assertEqual(v4.author, self.user)

    def test_revert_to_current_content_returns_400(self):
        create_response = self.client.post(self.page_list_url, self.page_data_v1, format='json') #v1
        page_id = create_response.data['id']

        revert_url = reverse('page-revert', kwargs={'pk': page_id, 'version_number_str': '1'})
        response_revert = self.client.post(revert_url, {'commit_message': "Trying to revert to current"}, format='json')
        self.assertEqual(response_revert.status_code, status.HTTP_400_BAD_REQUEST, response_revert.data)
        self.assertIn('Page content is already identical to this version', response_revert.data.get('message', ''))
