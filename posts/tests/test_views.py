import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from posts.models import Comment, Follow, Group, Post


class PostsViewTests(TestCase):

    AUTH_USER_NAME = 'TestUser'
    PAGE_TEXT = 'Тестовое сообщение1'
    PAGE_GROUP = 'Тестовая группа'
    GROUP_SLUG = 'test-group'
    GROUP_DESCR = 'Описание группы'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = get_user_model().objects.create(
            username=cls.AUTH_USER_NAME
        )
        Group.objects.bulk_create([
            Group(title=f'{cls.PAGE_GROUP}{i}',
                  slug=f'{cls.GROUP_SLUG}{i}',
                  description=f'{cls.GROUP_DESCR}{i}')
            for i in range(1, 3)]
        )

        cls.post = Post.objects.create(
            text=cls.PAGE_TEXT,
            author=cls.user,
            group=Group.objects.get(title=cls.PAGE_GROUP+'1')
        )

        cls.unfollower = get_user_model().objects.create(
            username='Unfoollowuser',
            email='testunfoll@gmail.com',
            password='unfolow',
        )

        cls.follower = get_user_model().objects.create(
            username='folow',
            email='testsfoll@gmail.com',
            password='follow',
        )

    def setUp(self):
        self.guest_user = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)
        self.authorized_unfollower = Client()
        self.authorized_unfollower.force_login(self.unfollower)

    def test_auth_user_can_unfollow(self):
        """Авторизированный пользователь может отписаться от автора поста"""
        Follow.objects.create(user=self.follower,
                              author=self.user)
        self.authorized_follower.get(
            reverse(
                'profile_unfollow',
                kwargs={'username': self.user}
            )
        )
        self.assertFalse(
            Follow.objects.filter(
                user=self.follower,
                author=self.user
            ),
        )

    def test_unfollower_follow_index(self):
        """Посты не появляются у неподписчика"""
        self.authorized_follower.get(reverse(
            'profile_follow',
            kwargs={
                'username': self.user
            }))

        posts = Post.objects.filter(
            author__following__user=self.follower)

        response_follower = self.authorized_follower.get(
            reverse('follow_index'))
        response_author = self.authorized_client.get(
            reverse('follow_index'))

        self.assertIn(
            posts.get(),
            response_follower.context['paginator'].object_list,
        )
        self.assertNotIn(
            posts.get(),
            response_author.context['paginator'].object_list,
        )

    def test_auth_user_can_comment(self):
        """Только авторизированный пользователь может комментировать посты"""
        form_data = {
            'post': self.post,
            'author': self.user,
            'text': 'TESTTESXT'
        }
        self.authorized_client.post(
            reverse('add_comment', args=(self.user, self.post.id)),
            data=form_data, follow=True
        )
        comment = Comment.objects.first()
        self.assertEqual(comment.text, form_data['text'])
        self.assertEqual(comment.author, self.user)
        self.assertEqual(self.post.comments.count(), 1)
        self.assertEqual(comment.post, self.post)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            'posts/index.html': reverse('index'),
            'posts/new_post.html': reverse('post_new'),
            'group.html': reverse('group_posts', kwargs={
                'slug': f'{self.GROUP_SLUG}1'}),
        }
        for template, url in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    def test_context_in_post_new_page(self):
        """Тестирование содержания context в post_new"""
        response = self.authorized_client.get(reverse('post_new'))

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
        }
        for value, expected in form_fields.items():
            form_field = response.context.get('form').fields.get(value)
            self.assertIsInstance(form_field, expected)

    def test_context_in_index_page(self):
        """Тестирование содержания context в index"""
        response = self.authorized_client.get(reverse('index'))
        all_post_count = Post.objects.count()
        resp_page = response.context['page'][0]

        context_post = {
            all_post_count: response.context['paginator'].count,
            self.PAGE_TEXT: resp_page.text,
            self.AUTH_USER_NAME: resp_page.author.username,
            f'{self.PAGE_GROUP}1': resp_page.group.title
        }

        for expected, value in context_post.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)

    def test_context_in_group_page(self):
        """Тестирование содержания context в group"""
        response = self.authorized_client.get(
            reverse('group_posts', kwargs={'slug': f'{self.GROUP_SLUG}1'})
        )

        resp_page = response.context['page'][0]
        resp_group = response.context['group']

        context_group = {
            self.PAGE_TEXT: resp_page.text,
            self.AUTH_USER_NAME: resp_page.author.username,
            f'{self.PAGE_GROUP}1': resp_group.title,
            f'{self.GROUP_SLUG}1': resp_group.slug,
            f'{self.GROUP_DESCR}1': resp_group.description
        }

        for expected, value in context_group.items():
            with self.subTest(value=value):
                self.assertEqual(value, expected)

    def test_context_in_edit_post_page(self):
        """Тестирование содержания context при редактировании поста"""
        response = self.authorized_client.get(
            reverse(
                'post_edit',
                kwargs={
                    'username': self.AUTH_USER_NAME,
                    'post_id': self.post.id
                }
            )
        )

        context_edit_page = {
            self.PAGE_TEXT: response.context.get('post').text,
            f'{self.PAGE_GROUP}1': response.context.get('post').group.title,
        }

        for expected, value in context_edit_page.items():
            with self.subTest():
                self.assertEqual(value, expected)

    def test_context_in_profile_page(self):
        """Тестирование содержания context для profile"""
        response = self.guest_user.get(
            reverse(
                'profile',
                kwargs={'username': self.AUTH_USER_NAME}
            )
        )
        resp_page = response.context['page'][0]

        context_edit_page = {
            self.PAGE_TEXT: resp_page.text,
            f'{self.PAGE_GROUP}1': resp_page.group.title,
            self.AUTH_USER_NAME: resp_page.author.username,
        }

        for expected, value in context_edit_page.items():
            with self.subTest():
                self.assertEqual(value, expected)

    def test_context_in_post_id_page(self):
        """Тестирование context для страницы индивидуального поста"""
        response = self.guest_user.get(
            reverse(
                'post',
                kwargs={
                    'username': self.AUTH_USER_NAME,
                    'post_id': self.post.id
                }
            )
        )

        context_edit_page = {
            self.PAGE_TEXT: response.context.get('post').text,
            f'{self.PAGE_GROUP}1': response.context.get('post').group.title,
            self.AUTH_USER_NAME: response.context.get('post').author.username,
        }

        for expected, value in context_edit_page.items():
            with self.subTest():
                self.assertEqual(value, expected)

    def test_post_added_in_index_page(self):
        """Тестирование наличия поста на главной странице сайта"""
        response = self.authorized_client.get(
            reverse('index'))
        post_id = response.context.get('page')[0].pk
        self.assertEqual(post_id, self.post.pk)

    def test_post_added_in_group_page(self):
        """Тестирование наличия поста присвоенного группе на странице группы"""
        post = Post.objects.first()
        response = self.authorized_client.get(
            reverse('group_posts', kwargs={'slug': f'{self.GROUP_SLUG}1'}))
        self.assertEqual(post.text, response.context.get('page')[0].text)

    def test_post_added_in_correct_group(self):
        """Тестирование на правильность назначения групп для постов"""
        group = Group.objects.first()
        posts_out_of_group = Post.objects.exclude(group=group)
        response = self.authorized_client.get(
            reverse('group_posts', kwargs={'slug': f'{self.GROUP_SLUG}1'}))
        group_list_posts_set = set(posts_out_of_group)
        all_posts_of_group_page = response.context.get(
            'paginator').object_list
        self.assertTrue(
            group_list_posts_set.isdisjoint(all_posts_of_group_page)
        )


class StaticViewsTests(TestCase):

    def test_templates_static_pages(self):
        """Тестирование шаблонов для статических страниц"""
        templates_url_names = {
            'about/author.html': reverse('about:author'),
            'about/tech.html': reverse('about:tech'),
        }

        for template, reverse_name in templates_url_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.client.get(reverse_name)
                self.assertTemplateUsed(response, template)


class PostImageViewTest(TestCase):
    AUTH_USER_NAME = 'TestUser'
    GROUP_SLUG = 'test-group'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

        cls.follower = get_user_model().objects.create(
            username='SecondFollow',
            email='teswes@gmail.com',
            password='Second',
        )

        cls.small_gif = (b'\x47\x49\x46\x38\x39\x61\x02\x00'
                         b'\x01\x00\x80\x00\x00\x00\x00\x00'
                         b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
                         b'\x00\x00\x00\x2C\x00\x00\x00\x00'
                         b'\x02\x00\x01\x00\x00\x02\x02\x0C'
                         b'\x0A\x00\x3B'
                         )

        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=cls.small_gif,
            content_type='image/gif'
        )
        cls.user = get_user_model().objects.create(
            username=cls.AUTH_USER_NAME
        )
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-group'
        )
        cls.post = Post.objects.create(
            text='Тестовая запись',
            group=cls.group,
            author=cls.user,
            image=cls.uploaded
        )

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_follower = Client()
        self.authorized_follower.force_login(self.follower)

    def test_follower_follow_user(self):
        """Посты появляются у подписчика"""
        self.authorized_follower.get(
            reverse('profile_follow',
                    kwargs={'username': self.user})
        )
        response = self.authorized_follower.get(
            reverse('follow_index')
        )
        self.assertContains(response, '<img ')
        self.assertEqual(response.context['page'][0], self.post)

    def test_context_index_page(self):
        """Проверяем context страницы index на наличие изображения"""
        response = self.guest_client.get(reverse('index'))
        response_data_image = response.context['page'][0].image
        expected = f'posts/{self.uploaded.name}'

        self.assertEqual(response_data_image, expected)

    def test_context_profile_page(self):
        """Проверяем context страницы profile на наличие изображения"""
        response = self.guest_client.get(
            reverse(
                'profile',
                kwargs={
                    'username': self.AUTH_USER_NAME
                }
            )
        )
        response_data_image = response.context['page'][0].image
        expected = f'posts/{self.uploaded.name}'

        self.assertEqual(response_data_image, expected)

    def test_context_group_page(self):
        """Проверяем context страницы group на наличие изображения"""
        response = self.guest_client.get(
            reverse(
                'group_posts',
                kwargs={
                    'slug': self.GROUP_SLUG
                }
            )
        )
        response_data_image = response.context['page'][0].image
        expected = f'posts/{self.uploaded.name}'

        self.assertEqual(response_data_image, expected)

    def test_context_post_page(self):
        """Проверяем context страницы post на наличие изображения"""
        response = self.guest_client.get(
            reverse(
                'post',
                kwargs={
                    'username': self.AUTH_USER_NAME,
                    'post_id': self.post.pk
                }
            )
        )
        response_data_image = response.context['post'].image
        expected = f'posts/{self.uploaded.name}'

        self.assertEqual(response_data_image, expected)


class PaginatorViewsTest(TestCase):
    """Тестируем Paginator. Страница должна быть разбита на 10 постов"""
    POSTS_IN_PAGE = 10
    POSTS_COUNT = 13

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = get_user_model().objects.create(username='TestUser')

        Post.objects.bulk_create([Post(
            text=f'Тестовое сообщение{i}',
            author=cls.user)
            for i in range(cls.POSTS_COUNT)])

    def test_first_page_contains_ten_records(self):
        """Тестируем Paginator.Первые 10 постов на первой странице"""
        response = self.client.get(reverse('index'))
        self.assertEqual(
            len(response.context.get('page').object_list), self.POSTS_IN_PAGE
        )

    def test_second_page_contains_three_records(self):
        """Тестируем Paginator.Последние 3 поста на второй странице"""
        response = self.client.get(reverse('index') + '?page=2')
        self.assertEqual(
            len(response.context.get('page').object_list),
            self.POSTS_COUNT - self.POSTS_IN_PAGE)


class CacheViewTest(TestCase):
    AUTHORIZED_USER_NAME = 'TestUser'

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user = get_user_model().objects.create(
            username=cls.AUTHORIZED_USER_NAME
        )

        Post.objects.bulk_create([Post(text=f'Test{i}', author=cls.user)
                                  for i in range(5)])
        cls.guest_user = Client()

    def test_index_cache(self):
        """Тестирование работоспособности кеширования на странице Index"""
        response = self.guest_user.get(reverse('index'))
        Post.objects.bulk_create([Post(text=f'Test{i}', author=self.user)
                                  for i in range(3)])

        context_cache_data_len = response.context['paginator'].count,
        post_context_cache_len = Post.objects.count()

        # длина кеша должна отличаться от колличества записанных постов в базе
        self.assertNotEqual(context_cache_data_len, post_context_cache_len)
        # очистим кеш и по новой запросим информацию с страницы
        cache.clear()
        response = self.guest_user.get(reverse('index'))
        # вычислим длину
        context_len = response.context['paginator'].count
        post_len = Post.objects.count()
        # колличество записей должно совпадать
        self.assertEqual(context_len, post_len)
