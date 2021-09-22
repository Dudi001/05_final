from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from posts.models import Group, Post


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.guest_client = Client()
        cls.user = get_user_model().objects.create(
            username='testuser',
            email='xnjnsd@mail.ru',
            password='Paruul',
        )
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)
        cls.group = Group.objects.create(
            slug='test-group',
            title='Тестовый заголовок',
            description='тестовое описание'
        )
        cls.post = Post.objects.create(
            text='Тестотовый пост для проверки',
            author=cls.user,
            group=cls.group,
        )

    def test_verbose_name(self):
        '''verbose_name в полях совпадает с ожидаемым.'''
        post = PostModelTest.post
        field_verbos = {
            'text': 'Текст',
            'group': 'Группа',
            'pub_date': 'Дата публикации',
            'author': 'Автор',
        }
        for value, expected in field_verbos.items():
            with self.subTest(value=value):
                self.assertEqual(
                    post._meta.get_field(value).verbose_name, expected
                )

    def test_help_text(self):
        '''help_text в полях совпадает с ожидаемым.'''
        post = PostModelTest.post
        field_help_texts = {
            'text': 'Заполнить*',
            'group': 'Выберите группу',
        }
        for value, expected in field_help_texts.items():
            with self.subTest(value=value):
                self.assertEqual(
                    post._meta.get_field(value).help_text, expected
                )

    def test_str_post(self):
        '''Тестируем длину __str__ значения в модели Post'''
        post = PostModelTest.post
        self.assertEqual(post.__str__(), post.text[:15])

    def test_str_group(self):
        '''Тестируем длину __str__ значения в модели Group'''
        group = PostModelTest.group
        group = self.group.title
        self.assertEqual(group.__str__(), group)
