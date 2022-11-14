import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Group, Post, Comment

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Test title',
            slug='test_slug',
            description='тестовое описание группы'
        )
        cls.post = Post.objects.create(
            text='Test text',
            group=cls.group,
            author=cls.user
        )
        cls.form = PostFormTest()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_post(self):
        """Валидная форма создает запись в Post."""

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

        posts_count = Post.objects.count()
        form_data = {
            'author': self.user,
            'text': 'Тестовый текст',
            'group': self.group.id,
            'image': uploaded
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'), data=form_data, follow=True
        )
        self.assertRedirects(
            response, reverse('posts:profile', args=[self.user]))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), posts_count + 1)
        self.assertTrue(
            Post.objects.filter(
                author=form_data['author'],
                text=form_data['text'],
                group=form_data['group'],
                image='posts/small.gif'
            ).exists()
        )

    def test_guest_create_post(self):
        """Валидная форма не создает запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Тестовый текст',
            'group': self.group.id
        }

        redirect = '/auth/login/?next=/create/'

        response = self.guest_client.post(reverse('posts:post_create'),
                                          data=form_data,
                                          follow=True)
        self.assertRedirects(response, redirect)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), posts_count)

    def test_post_edit(self):
        """Валидная форма редактирует запись в Post."""
        posts_count = Post.objects.count()
        form_data = {
            'author': self.user,
            'text': 'Тестовый текст2',
            'group': self.group.id
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', args=[self.post.pk]),
            data=form_data,
            follow=True
        )

        self.assertRedirects(response, reverse('posts:post_detail',
                             args=[self.post.pk]))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), posts_count)
        self.assertTrue(
            Post.objects.filter(
                author=form_data['author'],
                text=form_data['text'],
                group=form_data['group']
            ).exists()
        )


class CommentFormTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Test title',
            slug='test_slug',
            description='тестовое описание группы'
        )
        cls.post = Post.objects.create(
            text='Test text',
            group=cls.group,
            author=cls.user
        )
        cls.comment = Comment.objects.create(post_id=cls.post.id,
                                             author=cls.user,
                                             text='Тестовый коммент')

    @classmethod
    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_comment(self):
        '''Проверка создания комментария'''
        comment_count = Comment.objects.count()
        form_data = {'post_id': self.post.id,
                     'text': 'Тестовый коммент2'}
        response = self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.id}),
            data=form_data, follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertTrue(Comment.objects.filter(
                        text='Тестовый коммент2',
                        post=self.post.id,
                        author=self.user
                        ).exists())
        self.assertEqual(Comment.objects.count(),
                         comment_count + 1)

    def test_no_edit_comment(self):
        '''Проверка запрета комментирования не авторизованого пользователя'''
        posts_count = Comment.objects.count()
        form_data = {'text': 'Тестовый коммент2'}
        response = self.guest_client.post(reverse('posts:add_comment',
                                          kwargs={'post_id': self.post.id}),
                                          data=form_data,
                                          follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(Comment.objects.count(),
                            posts_count + 1)

    def test_comment_null(self):
        '''Запрет пустого комментария'''
        posts_count = Comment.objects.count()
        form_data = {'text': ''}
        response = self.authorized_client.post(
            reverse('posts:add_comment',
                    kwargs={'post_id': self.post.id}),
            data=form_data,
            follow=True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertNotEqual(Comment.objects.count(),
                            posts_count + 1)
