import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from ..models import Group, Post, Follow, Comment
from django import forms


User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Author')
        cls.group = Group.objects.create(
            title='Тестовая группа один',
            slug='test-slug',
            description='Тестовое описание',
        )
        cls.posts_list = [
            Post.objects.create(
                author=cls.user,
                text=f'Тестовый пост №{num}',
                group=cls.group
            ) for num in range(1, 14)
        ]

    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_paginator(self):
        """Страницы:
        '/',
        '/group/<slug>/',
        '/profile/<username>/'
        содержат 10 постов на первой странице
        и 3 поста на второй"""
        reverse_page_names = [
            reverse('posts:index'),
            reverse('posts:group_list', kwargs={'slug': self.group.slug}),
            reverse('posts:profile', kwargs={'username': self.user})
        ]
        for reverse_name in reverse_page_names:
            with self.subTest(reverse_name=reverse_name):
                response_first = self.client.get(reverse_name)
                response_second = self.client.get(reverse_name + '?page=2')
                self.assertEqual(len(response_first.context['page_obj']), 10)
                self.assertEqual(len(response_second.context['page_obj']), 3)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(username='Author')
        cls.user_user = User.objects.create_user(username='Noname')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание',
        )
        small_gif = (
             b'\x47\x49\x46\x38\x39\x61\x02\x00'
             b'\x01\x00\x80\x00\x00\x00\x00\x00'
             b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
             b'\x00\x00\x00\x2C\x00\x00\x00\x00'
             b'\x02\x00\x01\x00\x00\x02\x02\x0C'
             b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.posts_list = [
            Post.objects.create(
                author=cls.user_author,
                text='Тестовый пост № 1',
                group=cls.group
            ),
            Post.objects.create(
                author=cls.user_author,
                text='Тестовый пост № 2'
            ),
            Post.objects.create(
                author=cls.user_author,
                text='Тестовый пост № 3',
                group=cls.group,
                image=uploaded
            )
        ]
        cls.comment = Comment.objects.create(
            post=cls.posts_list[1],
            author=cls.user_user,
            text='Тестовый комменатрий',
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user_user)
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        for post in self.posts_list:
            post_id = post.id
            user = post.author
            if post.group:
                slug = post.group.slug

            templates_pages_names = {
                'posts/index.html':
                    reverse('posts:index'),
                'posts/group_list.html':
                    reverse('posts:group_list', kwargs={'slug': slug}),
                'posts/profile.html':
                    reverse('posts:profile', kwargs={'username': user}),
                'posts/post_detail.html':
                    reverse('posts:post_detail', kwargs={'post_id': post_id}),
                'posts/create_post.html':
                    reverse('posts:post_create'),
            }
            for template, reverse_name in templates_pages_names.items():
                with self.subTest(reverse_name=reverse_name):
                    cache.clear()
                    response = self.authorized_client.get(reverse_name)
                    self.assertTemplateUsed(response, template)

    def test_post_edit_uses_correct_template(self):
        """URL-адрес использует шаблон posts/create_post.html,
         чтобы отредактировать пост."""
        post_id = self.posts_list[0].id
        self.authorized_client.force_login(self.user_author)
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': post_id})
        )
        self.assertTemplateUsed(response, 'posts/create_post.html')

    def test_post_index_page_show_correct_context(self):
        """Шаблон posts/index.html сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(
            len(response.context['page_obj']),
            len(self.posts_list)
        )
        for post in self.posts_list:
            self.assertIn(post, response.context['page_obj'])
        self.assertEqual(
            self.posts_list[-1].image,
            response.context['page_obj'][2].image
        )

    def test_group_list_page_show_correct_context(self):
        """Шаблон posts/group_list.html
        сформирован с правильным контекстом."""
        response = self.client.get(
            reverse(
                'posts:group_list',
                kwargs={'slug': self.group.slug}
            )
        )
        self.assertEqual(response.context['group'].slug, self.group.slug)
        self.assertEqual(
            len(response.context['page_obj']),
            self.group.posts.count()
        )
        for post in self.posts_list:
            if post.group == self.group:
                self.assertIn(post, response.context['page_obj'])
        self.assertEqual(
            self.posts_list[-1].image,
            response.context['page_obj'][1].image
        )

    def test_profile_page_show_correct_context(self):
        """Шаблон posts/profile.html
        сформирован с правильным контекстом."""
        response = self.client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.user_author}
            )
        )
        self.assertEqual(
            len(response.context['page_obj']),
            self.user_author.posts.count()
        )
        self.assertEqual(
            response.context['count'],
            self.user_author.posts.count()
        )
        self.assertEqual(
            response.context['author'].username,
            self.user_author.username
        )
        for post in self.posts_list:
            if post.author == self.user_author.username:
                self.assertIn(post, response.context['page_obj'])
        self.assertEqual(
            self.posts_list[-1].image,
            response.context['page_obj'][2].image
        )

    def test_post_detail_page_show_correct_context(self):
        """Шаблон post_detail.html сформирован с правильным контекстом."""
        for post in self.posts_list:
            response = self.authorized_client.get(
                reverse('posts:post_detail', kwargs={'post_id': post.id})
            )
            self.assertEqual(
                response.context.get('post').text,
                post.text
            )
            self.assertEqual(
                response.context.get('post').author,
                post.author
            )
            self.assertEqual(
                response.context.get('post_count'),
                post.author.posts.count()
            )
            if post.image:
                self.assertEqual(post.image, response.context['post'].image)
            if post.comments:
                self.assertEqual(
                    post.comments,
                    response.context['post'].comments
                )
            self.assertTrue(response.context['form'])

    def test_create_page_edit_show_correct_context(self):
        """Шаблон creat_post.html сформирован с правильным контекстом
         для редактирования поста"""
        for post in self.posts_list:
            self.authorized_client.force_login(post.author)
            response = self.authorized_client.get(
                reverse('posts:post_edit', kwargs={'post_id': post.id})
            )
            self.assertEqual(
                response.context['form'].instance.text,
                post.text
            )

    def test_create_page_show_correct_context(self):
        """Шаблон creat_post.html сформирован с правильным контекстом
        для создания поста"""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_in_correct_placement(self):
        """Если у поста указана группа, он появляется
        на странице posts/profile.html и не попадает в группу,
         для которой не был предназначен."""
        reverse_page_names = {
            group.slug: reverse(
                'posts:group_list',
                kwargs={'slug': group.slug}
            ) for group in Group.objects.all()
        }
        for post in self.posts_list:
            if post.group:
                for slug in reverse_page_names:
                    if post.group.slug != slug:
                        response = self.client.get(reverse_page_names[slug])
                        self.assertNotIn(post, response.context['page_obj'])
                response = self.client.get(
                    reverse(
                        'posts:profile',
                        kwargs={'username': post.author})
                )
                self.assertIn(post, response.context['page_obj'])

    def test_cache_index_page(self):
        """Тестирование кэширования"""
        post = Post.objects.create(
            text='Пост для кеширования',
            author=self.user_author
        )
        response = self.authorized_client.get(
            reverse('posts:index')
        )
        post.delete()
        response_cache = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertEqual(response.content, response_cache.content)
        cache.clear()
        response_cache_clear = self.authorized_client.get(
            reverse('posts:index')
        )
        self.assertNotEqual(response.content, response_cache_clear.content)


class FollowViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_author = User.objects.create_user(
            username='author'
        )
        cls.user_follower = User.objects.create_user(
            username='follower'
        )
        cls.user_not_yet_follower = User.objects.create_user(
            username='not_yet_follower'
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user_author
        )
        cls.follow = Follow.objects.create(
            user=cls.user_follower,
            author=cls.user_author
        )

    def setUp(self):
        self.authorized_client = Client()

    def test_follow(self):
        """Авторизованный пользователь может подписываться
        на других пользователей"""
        count_follow = Follow.objects.count()
        self.authorized_client.force_login(self.user_not_yet_follower)
        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.user_author}))
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertTrue(
            Follow.objects.filter(
                user=self.user_not_yet_follower,
                author=self.user_author
            ).exists()
        )

    def test_unfollow(self):
        """Авторизованный пользователь может отписаться от подписок."""
        self.authorized_client.force_login(self.user_follower)
        count_follow = Follow.objects.count()
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.user_author}))
        self.assertEqual(Follow.objects.count(), count_follow - 1)
        self.assertFalse(
            Follow.objects.filter(
                user=self.user_follower,
                author=self.user_author
            ).exists()
        )

    def test_new_post_in_followers_page(self):
        """Новая запись пользователя появляется в ленте тех,
         кто на него подписан"""
        self.authorized_client.force_login(self.user_follower)
        post = Post.objects.create(
            text='Новый пост',
            author=self.user_author
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertIn(post, response.context['page_obj'])

    def test_new_post_not_in_not_yet_follower_page(self):
        """Новая запись пользователя не появляется в ленте тех,
         кто на него не подписан"""
        self.authorized_client.force_login(self.user_not_yet_follower)
        post = Post.objects.create(
            text='Новый пост',
            author=self.user_author
        )
        response = self.authorized_client.get(
            reverse('posts:follow_index')
        )
        self.assertNotIn(post, response.context['page_obj'])
