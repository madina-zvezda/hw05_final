import shutil
import tempfile
from http import HTTPStatus

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from posts.models import Comment, Follow, Group, Post

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostViewTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='auth2')
        cls.group = Group.objects.create(
            title='Тестовая Группа',
            slug='test-slug',
            description='тестовое описание группы'
        )

        cls.post = Post.objects.create(
            text='Тестовый текст',
            author=cls.user,
            group=cls.group
        )

        cls.templates_pages_names = [
            ('posts/index.html', reverse('posts:index')),
            ('posts/group_list.html', reverse(
                'posts:group_list', kwargs={'slug': 'test-slug'})),
            ('posts/profile.html', reverse('posts:profile', args=[cls.user])),
            ('posts/post_detail.html', reverse(
                'posts:post_detail', kwargs={'post_id': cls.post.pk})),
            ('posts/post_create.html', reverse('posts:post_create')),
            ('posts/post_create.html', reverse(
                'posts:post_edit', kwargs={'post_id': cls.post.pk})),
        ]

        cls.index = 'posts:index'
        cls.group_list = 'posts:group_list'
        cls.profile = 'posts:profile'
        cls.post_detail = 'posts:post_detail'
        cls.post_edit = 'posts:post_edit'
        cls.post_create = 'posts:post_create'

        cls.small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        cls.uploaded = SimpleUploadedFile(name='small.gif',
                                           content=cls.small_gif,
                                           content_type='image/gif')

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)
        super().tearDownClass()

    def tearDown(self) -> None:
        cache.clear()

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""

        for template, reverse_name in self.templates_pages_names:
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_page_show_correct_context_authorized(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(self.index))

        page_context = response.context['page_obj'][0]

        self.assertEqual(page_context, self.post)

    def test_group_list_page_show_correct_context_authorized(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(self.group_list, kwargs={'slug': self.group.slug}))

        page_context = response.context['page_obj'][0]
        group_context = response.context['group']

        self.assertEqual(page_context.author, self.post.author)
        self.assertEqual(page_context.group, self.post.group)
        self.assertEqual(group_context, self.group)

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(self.profile, args=[self.user]))

        page_context = response.context['page_obj'][0]
        author_context = response.context['author']

        self.assertEqual(page_context.author, self.post.author)
        self.assertEqual(page_context, self.post)
        self.assertEqual(author_context, self.user)

    def test_post_detail_page_show_correct_context_authorized(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(self.post_detail, kwargs={'post_id': self.post.pk}))

        post_context = response.context['post']

        self.assertEqual(post_context, self.post)

    def test_post_create_page_show_correct_context(self):
        """Шаблон post_create сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse(self.post_create))

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_post_edit_page_show_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse(self.post_edit, kwargs={'post_id': self.post.pk}))

        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertTrue(response.context.get('is_edit'))

    def test_post_is_not_in_another_group(self):
        """Созданный пост не попал в группу
           Для которой не был предназначен."""
        Group.objects.create(
            title='Another_group',
            slug='test-another-slug',
        )
        response = self.authorized_client.get(
            reverse(self.group_list, args=['test-another-slug']))

        self.assertNotIn(self.post, response.context['page_obj'])

    def test_post_added_correctly_user2(self):
        """Пост при создании не добавляется другому пользователю."""
        response_profile = self.authorized_client.get(
            reverse(self.profile,
                    kwargs={'username': f'{self.user.username}'}))

        group2 = Group.objects.create(title='Тестовая группа 2',
                                      slug='test_group2')
        post = Post.objects.create(
            text='Тестовый пост от другого автора',
            author=self.user2,
            group=group2)
        profile = response_profile.context['page_obj']

        self.assertNotIn(post, profile,
                         'поста нет в группе другого пользователя')

    def test_post_added_correctly(self):
        """"Пост виден на главной странице и странице группы."""

        response_index = self.authorized_client.get(
            reverse(self.index))
        response_group = self.authorized_client.get(
            reverse(self.group_list,
                    kwargs={'slug': f'{self.group.slug}'}))

        index_page = response_index.context['page_obj']
        group_page = response_group.context['page_obj']

        self.assertIn(self.post, index_page, 'поста нет на главной')
        self.assertIn(self.post, group_page, 'поста нет в группе')

    def image_in_context(self):
        url_names = (self.index, self.profile, self.group_list,
                     self.post_detail)
        for url in url_names:
            with self.subTest(value=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.context.get('post').image,
                                 self.post.image)

    def test_cache_context(self):
        '''Проверка кэширования страницы index'''
        before_creating_post = self.authorized_client.get(
            reverse('posts:index'))
        first_item = before_creating_post.content
        Post.objects.create(
            author=self.user,
            text='Проверка кэша',
            group=self.group)
        after_creating_post = self.authorized_client.get(
            reverse('posts:index'))
        item_after = after_creating_post.content
        self.assertEqual(item_after, first_item)
        cache.clear()
        after_clear = self.authorized_client.get(reverse('posts:index'))
        self.assertNotEqual(item_after, after_clear)


class PaginatorViewTest(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='auth')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.group = Group.objects.create(
            title='Тестовая Группа',
            slug='Test_slug',
            description='тестовое описание группы'
        )
        test_nout_more = 3
        test_nout = settings.POSTS_PER_PAGE + test_nout_more

        self.posts = Post.objects.bulk_create(
            [
                Post(
                    text=f'Тестовые посты номер {number}',
                    author=self.user,
                    group=self.group
                )
                for number in range(test_nout)
            ]
        )

    def tearDown(self) -> None:
        cache.clear()

    def test_second_page_contains_three_records(self):
        """На второй странице должно быть три поста."""

        response = self.client.get(reverse('posts:index') + '?page=2')
        response = self.client.get(
            reverse('posts:group_list',
                    kwargs={'slug': self.group.slug}) + '?page=2')
        response = self.client.get(
            reverse('posts:profile', args=[self.user]) + '?page=2')

        self.assertEqual(len(response.context['page_obj']), 3)

    def test_first_page_contains(self):
        """Тест Пагинатора для Первой страницы."""
        url_names = {
            reverse('posts:index'): settings.POSTS_PER_PAGE,
            reverse('posts:group_list', kwargs={'slug': self.group.slug}):
            settings.POSTS_PER_PAGE,
            reverse('posts:profile', args=[self.user]):
            settings.POSTS_PER_PAGE,
        }

        for value, expected in url_names.items():
            with self.subTest(value=value):
                response = self.client.get(value + '?page=1')
                self.assertEqual(len(response.context['page_obj']), expected)


class CommentTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth1')
        cls.not_author = User.objects.create_user(
            username='not_author')
        cls.group = Group.objects.create(title='Тестовая группа',
                                         slug='test_group')
        cls.post = Post.objects.create(text='Тестовый текст',
                                       group=cls.group,
                                       author=cls.user)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    def tearDown(self) -> None:
        cache.clear()

    def test_comment_authorized_client(self):
        """Коментировать может только авторизованный пользователь."""
        self.comment = Comment.objects.create(post_id=self.post.id,
                                              author=self.user,
                                              text='Тестовый коммент')
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))
        comments = {response.context['comments'][0].text: 'Тестовый коммент',
                    response.context['comments'][0].author: self.user.username
                    }
        for value, expected in comments.items():
            self.assertEqual(comments[value], expected)
        self.assertTrue(response.context['form'], 'форма получена')

    def test_comment_added_correctly(self):
        """"Комментарий появляется на странице поста."""
        self.comment = Comment.objects.create(post_id=self.post.id,
                                              author=self.user,
                                              text='Тестовый коммент')

        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}))

        comment = response.context['comments']

        self.assertIn(self.comment, comment, 'коммента нет на странице поста')


class FollowTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.post_autor = User.objects.create(
            username='post_autor',
        )
        cls.post_follower = User.objects.create(
            username='post_follower',
        )
        cls.post = Post.objects.create(
            text='Подпишись на меня',
            author=cls.post_autor,
        )

    def setUp(self):
        cache.clear()
        self.author_client = Client()
        self.author_client.force_login(self.post_follower)
        self.follower_client = Client()
        self.follower_client.force_login(self.post_autor)

    def tearDown(self) -> None:
        cache.clear()

    def test_follow_on_user(self):
        """Проверка подписки на пользователя."""
        count_follow = Follow.objects.count()
        self.follower_client.post(
            reverse('posts:profile_follow',
                    kwargs={'username': self.post_follower}))
        follow = Follow.objects.all().latest('id')
        self.assertEqual(Follow.objects.count(), count_follow + 1)
        self.assertTrue(
            Follow.objects.filter(
                author=follow.author_id,
                user=follow.user_id).exists()
        )

    def test_unfollow_on_user(self):
        """Проверка отписки от пользователя."""
        Follow.objects.create(
            user=self.post_autor,
            author=self.post_follower)

        self.follower_client.post(
            reverse('posts:profile_unfollow',
                    kwargs={'username': self.post_follower}))

        self.assertFalse(Follow.objects.all().exists())

    def test_follow_on_authors(self):
        """Проверка записей у тех кто подписан."""
        post = Post.objects.create(
            author=self.post_autor,
            text="Подпишись на меня")
        Follow.objects.create(
            user=self.post_follower,
            author=self.post_autor)
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertIn(post, response.context['page_obj'].object_list)

    def test_notfollow_on_authors(self):
        """Проверка записей у тех кто не подписан."""
        post = Post.objects.create(
            author=self.post_autor,
            text="Подпишись на меня")
        response = self.author_client.get(
            reverse('posts:follow_index'))
        self.assertNotIn(post, response.context['page_obj'].object_list)
