from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, Client
from ..models import Group, Post
from django.urls import reverse
from http import HTTPStatus


User = get_user_model()


class PostURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='Author')
        cls.user_user = User.objects.create_user(username='Somebody')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user_author,
            text='Тестовый пост',
        )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_user)

    def test_urls_exists_at_desired_location(self):
        """Страницы
            '/',
            '/group/<slug>/',
            '/profile/<username>/',
            '/posts/<post_id>/'
         доступны любому пользователю."""
        url_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user_author}),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        ]
        for address in url_names:
            with self.subTest(address=address):
                response = self.guest_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_create_redirect_anonymous(self):
        """Страница по адресу /create/ перенаправит анонимного
            пользователя на страницу логина.
        """
        response = self.guest_client.get(
            reverse('posts:post_create'), follow=True
        )
        self.assertRedirects(response, '/auth/login/?next=/create/')

    def test_post_edit_redirect_anonymous(self):
        """Страница по адресу /posts/<post_id>/ перенаправит анонимного
            пользователя на страницу логина.
        """
        response = self.guest_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            follow=True
        )
        self.assertRedirects(
            response,
            f'/auth/login/?next=/posts/{str(self.post.id)}/edit/'
        )

    def test_unexisting_page_for_anonymous(self):
        """Страница по адресу /unexisting_page/ сообщит анонимному
            пользователю, что такой страницы не существует.
        """
        response = self.guest_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_unexisting_page_for_authorized(self):
        """Страница по адресу /unexisting_page/ сообщит авторизованному
            пользователю, что такой страницы не существует.
        """
        response = self.authorized_client.get('/unexisting_page/')
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')

    def test_urls_exists_at_desired_location_authorized(self):
        """Страницы
            '/',
            '/group/<slug>/',
            '/profile/<username>/',
            '/posts/<post_id>/',
            '/create/'
         доступны авторизованному пользователю."""
        url_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user_author}),
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}),
            reverse('posts:post_create')
        ]
        for address in url_names:
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post_edit_for_authorized(self):
        """Страница posts/<int:post_id>/edit/ перенаправляет авторизованного
        пользователя на страницу posts/<int:post_id>/
        """
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )

    def test_post_edit_for_author(self):
        """Страница posts/<int:post_id>/edit/ доступна только автору"""
        self.authorized_client.force_login(self.post.author)
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            reverse('posts:index'):
                'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.user_author}):
                'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
                'posts/create_post.html',
            reverse('posts:post_create'):
                'posts/create_post.html'
        }
        self.authorized_client.force_login(self.user_author)
        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
