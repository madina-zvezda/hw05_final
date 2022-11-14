from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase
from posts.models import Group, Post

User = get_user_model()


class PostsURLTest(TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.user = User.objects.create_user(username='username')
        cls.user2 = User.objects.create_user(username='username2')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост1',
            group=cls.group,
        )

        cls.index_url = '/'
        cls.group_posts = f'/group/{cls.group.slug}/'
        cls.profile = f'/profile/{cls.user.username}/'
        cls.post_detail = f'/posts/{cls.post.pk}/'
        cls.post_edit_url = f'/posts/{cls.post.pk}/edit/'
        cls.post_create_url = f'/posts/{cls.post.id}/edit/'
        cls.page_not_found_url = '/unexistring_page/'

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = Client()
        self.not_author = Client()
        self.authorized_client.force_login(self.user)
        self.not_author.force_login(self.user2)
        cache.clear()

    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            self.index_url: 'posts/index.html',
            self.group_posts: 'posts/group_list.html',
            self.profile: 'posts/profile.html',
            self.post_create_url: 'posts/post_create.html'
        }

        for address, template in templates_url_names.items():
            with self.subTest(address=address):
                response = self.authorized_client.get(address)
                self.assertTemplateUsed(response, template)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_url_guest_exists_at_desired_location(self):
        """Страницы, доступные любому пользователю."""
        request = {
            self.index_url: HTTPStatus.OK,
            self.group_posts: HTTPStatus.OK,
            self.profile: HTTPStatus.OK,
            self.post_detail: HTTPStatus.OK,
            self.page_not_found_url: HTTPStatus.NOT_FOUND,
        }
        for address, status in request.items():
            with self.subTest(address=address):
                response = self.guest_client.get(address)

                self.assertEqual(response.status_code, status)

    def test_url_redirect_anonymous_on_admin_login(self):
        """
        Страницы для авторизованных пользователей перенаправят
        анонимного пользователя на страницу логина.
        """
        request = {
            '/create/': '/auth/login/?next=/create/',
            f'/posts/{self.post.pk}/edit/':
                f'/auth/login/?next=/posts/{self.post.pk}/edit/',
        }
        for address, add_login in request.items():
            with self.subTest(address=address):
                response = self.client.get(address, follow=True)
                self.assertRedirects(response, add_login)

    def test_url_authorized_edit_post(self):
        """
        Не автор поста не может редактировать пост.
        """
        redirect = f'/posts/{self.post.id}/'

        response = self.not_author.get(f'/posts/{self.post.pk}/edit/',
                                       follow=True)
        self.assertRedirects(response, redirect)

    def test_404(self):
        """Страница 404 отдаёт кастомный шаблон."""
        response = self.guest_client.get('/test-not',
                                         follow=True)
        self.assertEqual(response.status_code,
                         HTTPStatus.NOT_FOUND)
        self.assertTemplateUsed(response, 'core/404.html')
