from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Group, Post


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаем двух пользователей
        cls.author = get_user_model().objects.create(
            username='Authorposta'
        )
        cls.not_author = get_user_model().objects.create(
            username='not-author'
        )

        # Создаем тестовую группу в БД
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group',
            description='Тестовая групппа',
        )
        # Создаем тестовый пост в БД
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.author,
            group=cls.group
        )

    def setUp(self):
        # Зарегестрированный пользователь не автор поста
        self.authorized_author = Client()
        self.authorized_author.force_login(self.author)

        # Зарегестрированный пользователь не автор поста
        self.authorized_not_author = Client()
        self.authorized_not_author.force_login(self.not_author)

        self.reverse_name_group = reverse(
            'group_posts',
            kwargs={'slug': self.group.slug}
        )
        self.reverse_name_profile = reverse(
            'profile',
            kwargs={'username': self.author}
        )
        self.reverse_name_post = reverse(
            'post',
            kwargs={'username': self.author, 'post_id': self.post.id}
        )
        self.reverse_name_post_edit = reverse(
            'post_edit',
            kwargs={'username': self.author, 'post_id': self.post.id}
        )

        self.templates_url_names = {
            'posts/post.html': self.reverse_name_post,
            'posts/index.html': reverse('index'),
            'group.html': self.reverse_name_group,
            'posts/profile.html': self.reverse_name_profile,
            'posts/new_post.html': self.reverse_name_post_edit
        }

        self.auth_users_resp_st_code = {
            reverse('index'): 200,
            self.reverse_name_group: 200,
            reverse('post_new'): 200,
            self.reverse_name_profile: 200,
            self.reverse_name_post: 200,
            self.reverse_name_post_edit: 200,
        }

    def test_urls_authorized_users(self):
        """Тестирование URL для авторизованных пользователей."""
        for reverse_name, status_code in self.auth_users_resp_st_code.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertEqual(status_code, response.status_code)

    def test_profile_post_edit_by_creator(self):
        """Проверка доступности адреса '/<username>/<post_id>/edit/'
        для авторизированного пользователя(автора поста)."""
        response = self.authorized_author.get(
            reverse(
                'post_edit',
                kwargs={'username': self.author, 'post_id': self.post.id}
            )
        )
        self.assertEqual(response.status_code, 200)

    def test_post_edit_new_post_redirect_anonymous(self):
        """Страница редактирования и создания поста
         перенаправляет неавторизированного пользователя."""
        rev_name = [
            reverse('post_new'),
            reverse(
                'post_edit',
                args=(self.author, self.post.id)
            )
        ]

        rev_name_rev_name_exp = {
            rev_name[0]: reverse('login') + '?next=' + rev_name[0],
            rev_name[1]: reverse('login') + '?next=' + rev_name[1],
        }
        for reverse_name, reverse_name_exp in rev_name_rev_name_exp.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(
                    reverse_name, follow=False
                )
                self.assertRedirects(response, reverse_name_exp, 302)

    def test_url_correct_templates(self):
        """Тестирование доступности шаблонов по reverse name"""

        for template, reverse_name in self.templates_url_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_author.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_url_edit_post_not_owner(self):
        """Тестирование URL:
        Edit Post для авторизованного невладельца поста"""
        response = self.authorized_not_author.get(
            reverse('post_edit', kwargs={
                'username': self.not_author,
                'post_id': self.post.id})
        )
        self.assertEqual(response.status_code, 404)


class StaticURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.static_pages = {
            reverse('about:author'): 200,
            reverse('about:tech'): 200,
        }

    def setUp(self):
        self.guest_client = Client()

    def test_urls_static_pages(self):
        """Тестируем статические страницы на доступность"""
        for reverse_name, status_code in self.static_pages.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.guest_client.get(reverse_name)
                self.assertEqual(status_code, response.status_code)
