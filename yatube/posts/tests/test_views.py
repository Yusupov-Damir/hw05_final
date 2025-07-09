import shutil
import tempfile

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase, Client, override_settings
from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache
from ..models import Group, Post, Comment, Follow

User = get_user_model()

# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена, а потом мы ее удалим.
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)

@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsURLTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Создаём пользователя
        cls.user = User.objects.create_user(username='testuser', password='testpass123')
        # Создаём группы
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Тестовое описание'
        )
        # Добавим 12 тестовых постов для проверки пагинатора (итого 13)
        for i in range(12):
            Post.objects.create(
                author=cls.user,
                text=f'Пост {i}',
                group=cls.group
            )
        # Создаём пост с изображением
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
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост для проверки URL',
            group=cls.group,
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Модуль shutil - библиотека Python для управления файлами.
        # Метод shutil.rmtree удаляет директорию и всё её содержимое
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент:
        self.authorized_client = Client()
        # Авторизуем пользователя:
        # force_login - стандартный метод имитации авторизации пользователя
        self.authorized_client.force_login(self.__class__.user)  # __class__ используем польз-ля из setUpClass
        cache.clear()  # Очищает кэш перед каждым тестом

    # Задание 1: проверка namespace:name
    def test_urls_uses_correct_template(self):
        """view-функциях используются правильные html-шаблоны."""
        # URL-адреса и соответствующие шаблоны
        urls_templates_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list', kwargs={'slug': self.__class__.group.slug}): 'posts/group_list.html',
            reverse('posts:profile', kwargs={'username': self.__class__.user.username}): 'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.__class__.post.id}): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit', kwargs={'post_id': self.__class__.post.id}): 'posts/create_post.html',
        }
        for url, template in urls_templates_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)

    # Задание2: Тесты для пагинатора
    def test_index_first_page_contains_ten_records(self):
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_index_second_page_contains_three_records(self):
        response = self.authorized_client.get(reverse('posts:index') + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_group_list_first_page_contains_ten_records(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.__class__.group.slug}))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_group_list_second_page_contains_three_records(self):
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.__class__.group.slug}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    def test_profile_first_page_contains_ten_records(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.__class__.user.username}))
        self.assertEqual(len(response.context['page_obj']), 10)

    def test_profile_second_page_contains_three_records(self):
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.__class__.user.username}) + '?page=2')
        self.assertEqual(len(response.context['page_obj']), 3)

    # Тесты для контекста
    def test_index_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:index'))
        posts = response.context['page_obj']  # Берем все посты на странице
        # Проверяем текстовые поля
        self.assertTrue(any(post.text == 'Тестовый пост для проверки URL' for post in posts))
        self.assertTrue(any(post.author == self.__class__.user for post in posts))
        self.assertTrue(any(post.group == self.__class__.group for post in posts))
        # Проверяем изображение
        self.assertTrue(
            any(post.image and post.image.name == 'posts/small.gif' for post in posts),
            "Пост с изображением не найден в контексте или путь к изображению неверный"
        )

    def test_group_list_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:group_list', kwargs={'slug': self.__class__.group.slug}))
        posts = response.context['page_obj']
        self.assertTrue(
            any(post.text == 'Тестовый пост для проверки URL' for post in posts),
            "Пост с текстом 'Тестовый пост для проверки URL' не найден в group_list"
        )
        self.assertTrue(
            any(post.author == self.__class__.user for post in posts),
            "Пост с автором testuser не найден в group_list"
        )
        self.assertTrue(
            any(post.group == self.__class__.group for post in posts),
            "Пост с группой test-slug не найден в group_list"
        )
        self.assertTrue(
            any(post.image and post.image.name == 'posts/small.gif' for post in posts),
            "Пост с изображением posts/small.gif не найден в group_list"
        )

    def test_profile_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': self.__class__.user.username}))
        posts = response.context['page_obj']
        self.assertTrue(
            any(post.text == 'Тестовый пост для проверки URL' for post in posts),
            "Пост с текстом 'Тестовый пост для проверки URL' не найден в profile"
        )
        self.assertTrue(
            any(post.author == self.__class__.user for post in posts),
            "Пост с автором testuser не найден в profile"
        )
        self.assertTrue(
            any(post.group == self.__class__.group for post in posts),
            "Пост с группой test-slug не найден в profile"
        )
        self.assertTrue(
            any(post.image and post.image.name == 'posts/small.gif' for post in posts),
            "Пост с изображением posts/small.gif не найден в profile"
        )

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.__class__.post.id}))
        post = response.context['post']
        self.assertEqual(
            post.text,
            'Тестовый пост для проверки URL',
            "Неверный текст поста в post_detail"
        )
        self.assertEqual(
            post.author,
            self.__class__.user,
            "Неверный автор поста в post_detail"
        )
        self.assertEqual(
            post.group,
            self.__class__.group,
            "Неверная группа поста в post_detail"
        )
        self.assertTrue(
            post.image and post.image.name == 'posts/small.gif',
            "Изображение posts/small.gif не найдено в post_detail"
        )

    def test_create_post_show_correct_context_new(self):
        """Шаблон create_post для создания сформирован с правильным контекстом."""
        response = self.authorized_client.get(reverse('posts:post_create'))
        form_fields = {
            'text': forms.CharField,
            'group': forms.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)

    def test_create_post_show_correct_context_edit(self):
        """Шаблон create_post для редактирования сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit', kwargs={'post_id': self.__class__.post.id}))
        form_fields = {
            'text': forms.CharField,
            'group': forms.ChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)
        self.assertEqual(response.context['form'].instance, self.__class__.post)

    def test_guest_cannot_comment(self):
        """Неавторизованный пользователь не может комментировать посты."""
        comment_count_before = Comment.objects.count()
        form_data = {
            'text': 'Тестовый комментарий от гостя',
        }
        response = self.guest_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.__class__.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Comment.objects.count(), comment_count_before,
                         "Комментарий был добавлен неавторизованным пользователем")

    def test_comment_appears_on_post_detail(self):
        """После успешной отправки комментарий появляется на странице поста."""
        form_data = {
            'text': 'Тестовый комментарий',
        }
        response = self.authorized_client.post(
            reverse('posts:add_comment', kwargs={'post_id': self.__class__.post.id}),
            data=form_data,
            follow=True
        )
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={'post_id': self.__class__.post.id}))
        # Проверяем, что комментарий отображается на странице поста
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.__class__.post.id}))
        comments = response.context['comments']
        self.assertTrue(any(comment.text == 'Тестовый комментарий' for comment in comments),
                        "Комментарий не отображается на странице поста")

    def test_follow_unfollow(self):
        # Подписка
        response = self.authorized_client.post(
            reverse('posts:profile_follow', args=[self.__class__.user.username])
        )
        self.assertEqual(response.status_code, 302)  # Редирект
        self.assertTrue(Follow.objects.filter(user=self.__class__.user, author=self.__class__.user).exists())

        # Отписка
        response = self.authorized_client.post(
            reverse('posts:profile_unfollow', args=[self.__class__.user.username])
        )
        self.assertEqual(response.status_code, 302)  # Редирект
        self.assertFalse(Follow.objects.filter(user=self.__class__.user, author=self.__class__.user).exists())

        def test_post_in_followers_feed(self):
            # Создаём второго пользователя для подписки
            follower = User.objects.create_user(username='follower', password='testpass')
            follower_client = Client()
            follower_client.login(username='follower', password='testpass')

            # Подписываем follower на author
            follower_client.post(reverse('posts:profile_follow', args=[self.__class__.user.username]))
            self.assertTrue(Follow.objects.filter(user=follower, author=self.__class__.user).exists())

            # Проверяем ленту подписчика
            response = follower_client.get(reverse('posts:follow_index'))
            self.assertEqual(response.status_code, 200)
            self.assertContains(response, self.__class__.post.text)  # Пост виден

            # Проверяем ленту не подписанного (authorized_client не подписан)
            response = self.authorized_client.get(reverse('posts:follow_index'))
            self.assertEqual(response.status_code, 200)
            self.assertNotContains(response, self.__class__.post.text)  # Пост не виден


class CacheTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser', password='testpass123')
        cls.post = Post.objects.create(author=cls.user, text='Тестовый пост', pub_date='2025-07-07 12:00:00')

    def setUp(self):
        self.client = Client()
        cache.clear()  # Очищаем кэш перед каждым тестом

    def test_cache_with_deletion(self):
        """Проверяет, что удалённая запись остаётся в response.content до очистки кэша."""
        url = reverse('posts:index')
        # Первый запрос заполняет кэш
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, 200)
        self.assertContains(response1, 'Тестовый пост')  # Проверяем наличие поста
        # Удаляем запись
        self.__class__.post.delete()
        # Второй запрос использует кэш (удалённая запись всё ещё видна)
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, 200)
        self.assertContains(response2, 'Тестовый пост')  # Пост остаётся в кэше
        # Очищаем кэш принудительно
        cache.delete('index_page')
        # Третий запрос после очистки кэша
        response3 = self.client.get(url)
        self.assertEqual(response3.status_code, 200)
        self.assertNotContains(response3, 'Тестовый пост')  # Пост исчезает