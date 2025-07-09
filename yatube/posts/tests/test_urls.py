from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from ..models import Group, Post

User = get_user_model()

class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаём пользователя
        cls.user = User.objects.create_user(username='testuser', password='testpass123')
        # Создаём группу
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        # Создадим запись пост
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост для проверки URL',
            group=cls.group
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент:
        self.authorized_client = Client()
        # Авторизуем пользователя:
        # force_login - стандартный метод имитации авторизации пользователя
        self.authorized_client.force_login(self.__class__.user)  # __class__ используем польз-ля из setUpClass

    # Проверяем доступность страниц для любого пользователя
    def test_home_url(self):
        """Страница / доступна любому пользователю."""
        response = self.guest_client.get('/')
        self.assertEqual(response.status_code, 200)

    def test_group_slug_url(self):
        """Страница /group/<slug>/ доступна любому пользователю."""
        response = self.guest_client.get('/group/test-slug/')
        self.assertEqual(response.status_code, 200)

    def test_profile_username_url(self):
        """Страница /profile/<username>/ доступна любому пользователю."""
        response = self.guest_client.get('/profile/testuser/')
        self.assertEqual(response.status_code, 200)

    def test_post_id_url(self):
        """Страница /posts/<post_id>/ доступна любому пользователю."""
        response = self.guest_client.get(f'/posts/{self.__class__.post.id}/')
        self.assertEqual(response.status_code, 200)

    def test_404_url(self):
        """Страница не существует."""
        response = self.guest_client.get('/unexisting/')
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, 'core/404.html')

    # Проверяем доступность страниц для авторизованного пользователя
    def test_create_url(self):
        """Страница /create/ доступна авторизованному пользователю."""
        response = self.authorized_client.get('/create/')
        self.assertEqual(response.status_code, 200)

    # Проверяем доступность страниц для автора
    def test_post_edit_url(self):
        """Страница /posts/<post_id>/edit/ доступна автору."""
        response = self.authorized_client.get(f'/posts/{self.__class__.post.id}/edit/')
        self.assertEqual(response.status_code, 200)

    # Проверяем соответствие шаблонов
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        # Шаблоны по адресам
        templates_url_names = {
            '/': 'posts/index.html',
            '/group/test-slug/': 'posts/group_list.html',
            '/profile/testuser/': 'posts/profile.html',
            f'/posts/{self.__class__.post.id}/': 'posts/post_detail.html',
            '/create/': 'posts/create_post.html',
            f'/posts/{self.__class__.post.id}/edit/': 'posts/create_post.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)



