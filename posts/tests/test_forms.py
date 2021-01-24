from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.create(
            username='testuser',
            email='xnjnsd@mail.ru',
            password='Paruul',
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group',
            description='Тестовая групппа',
        )

        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group,
        )

    def test_forms_views(self): 
        count = Post.objects.count()
 
        form_data = { 
            'group': self.group.id, 
            'text': 'Тестовая запись', 
        } 
        self.authorized_client.post( 
            reverse('post_new'), 
            data=form_data, 
            follow=True 
        ) 
        post_view = Post.objects.first() 
        self.assertEqual(Post.objects.count(), count + 1) 
        self.assertEqual(post_view.text, form_data['text']) 
        self.assertEqual(post_view.author, self.user) 
        self.assertEqual(post_view.group, self.group) 

    def test_edit_post(self):
        '''Тестируем изменение поста.'''
        group_havent_post = Group.objects.create(
            title='test-group-2',
            slug='test_group_2',
        )
        post_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': group_havent_post.id,
        }
        self.authorized_client.post(
            reverse(
                'post_edit',
                args=(self.user.username, self.post.id)
            ),
            data=form_data,
            follow=True
        )

        post_edit = Post.objects.first()
        self.assertEqual(Post.objects.count(), post_count)
        self.assertEqual(post_edit.text, form_data['text'])
        self.assertEqual(post_edit.author, self.user)
        self.assertEqual(post_edit.group, group_havent_post)
