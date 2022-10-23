import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from ..forms import PostForm
from ..models import Post, Group, Comment

User = get_user_model()
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='Author')
        cls.commentator = User.objects.create_user(username='Commentator')
        cls.group_lst = [
            Group.objects.create(
                title='Тестовая группа один',
                slug='slug_1',
                description='Тестовое описание',
            ),
            Group.objects.create(
                title='Тестовая группа два',
                slug='slug_2',
                description='Тестовое описание',
            )
        ]
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост',
            group=cls.group_lst[0]
        )
        cls.form = PostForm()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """При отправке валидной формы со страницы создания поста
         'posts:create_post' создаётся новый пост"""
        posts_count = Post.objects.count()
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
        form_data = {
            'text': 'Питонисты',
            'group': self.group_lst[0].id,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile', kwargs={'username': self.user})
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(
            Post.objects.filter(
                text='Питонисты',
                group=self.group_lst[0].id,
                image='posts/small.gif'
            ).exists()
        )

    def test_edit_post(self):
        """При редактировании происходи изменение существующего поста"""
        posts_count = Post.objects.count()
        self.authorized_client.force_login(self.post.author)
        form_data = {
            'text': 'tEST',
            'group': self.group_lst[1].id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                text='tEST',
                group=self.group_lst[1].id,
            ).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_create_comment(self):
        """Проверка создания авторизаонным пользователем комментария"""
        comments_count = Comment.objects.count()
        self.authorized_client.force_login(self.commentator)
        form_data = {
            'text': 'Комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text='Комментарий'
            ).exists()
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
