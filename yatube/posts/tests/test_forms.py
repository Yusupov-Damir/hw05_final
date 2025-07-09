import shutil
import tempfile

from django.test import TestCase, Client, override_settings
from django.urls import reverse
from django.contrib.auth.models import User
from ..models import Post, Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings


# Создаем временную папку для медиа-файлов;
# на момент теста медиа папка будет переопределена, а потом мы ее удалим.
TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='testuser', password='testpass123')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test-slug',
            description='Описание группы'
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Исходный текст поста',
            group=cls.group
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        # Модуль shutil - библиотека Python для управления файлами.
        # Метод shutil.rmtree удаляет директорию и всё её содержимое
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.__class__.user)

    def test_create_post(self):
        """Проверка создания нового поста при отправке валидной формы."""
        post_count_before = Post.objects.count()
        # Для тестирования загрузки изображений
        # берём байт-последовательность картинки,
        # состоящей из двух пикселей: белого и чёрного
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
            'text': 'Новый тестовый пост',
            'group': self.__class__.group.id,
            'image': uploaded,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Post.objects.count(), post_count_before + 1)
        new_post = Post.objects.latest('id')
        self.assertEqual(new_post.text, 'Новый тестовый пост')
        self.assertEqual(new_post.image, 'posts/small.gif')
        self.assertEqual(new_post.group.id, self.__class__.group.id)
        self.assertEqual(new_post.author, self.__class__.user)
        self.assertRedirects(response, reverse('posts:profile', kwargs={'username': self.__class__.user.username}))

    def test_edit_post(self):
        """Проверка редактирования поста при отправке валидной формы."""
        post_count_before = Post.objects.count()
        form_data = {
            'text': 'Обновлённый текст поста',
            'group': self.__class__.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_edit', kwargs={'post_id': self.__class__.post.id}),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), post_count_before)
        edited_post = Post.objects.get(id=self.__class__.post.id)
        self.assertEqual(edited_post.text, 'Обновлённый текст поста')
        self.assertEqual(edited_post.group.id, self.__class__.group.id)
        self.assertEqual(edited_post.author, self.__class__.user)
        self.assertRedirects(response, reverse('posts:post_detail', kwargs={'post_id': self.__class__.post.id}))