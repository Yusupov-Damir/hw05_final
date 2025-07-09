from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.core.cache import cache

from .models import Post, Group, Follow
from .forms import PostForm, CommentForm

User = get_user_model()

posts_per_page = 10  # Для paginator.

def pag(post_list, request):
    """Вынес дублирующийся код пагинатора."""
    paginator = Paginator(post_list, posts_per_page)  # Показывать по 10 записей на странице.
    page_number = request.GET.get('page')  # Из URL извлекаем номер запрошенной страницы - page.
    page_obj = paginator.get_page(page_number)  # Получаем набор записей для страницы с запрошенным номером.
    return page_obj

def index(request):
    cache_key = 'index_page'  # Определяем ключ кэша.
    post_list = cache.get(cache_key)  # Пытаемся получить данные из кэша.

    # Если данные в кэше отсутствуют.
    if post_list is None:
        post_list = Post.objects.all()  # Выполняем запрос к базе и сохраняем в кэш на 20 секунд.
        cache.set(cache_key, post_list, 20)
    page_obj = pag(post_list, request)
    return render(request, 'posts/index.html', {
        'page_obj': page_obj,
        'index': True,
    })

def group_posts(request, slug):  # Принимаем в аргументе переменную slug из URL.
    group = get_object_or_404(Group, slug=slug)  # Берем объект модели Group, у которого поле slug = перем-ой.
    post_list = Post.objects.all().filter(group=group)
    page_obj = pag(post_list, request)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, 'posts/group_list.html', context)

def profile(request, username):
    author = get_object_or_404(User, username=username)  # Берем автора по контексту запроса.
    # Не авторизованному пользователю всегда предлагаем подписаться.
    # Тогда при нажатии на подписку сработает редирект, требующий регистрацию и выкидывающий предложение зарег-ся.
    following = False

    #  Если зашел авторизованный пользователь - проверяем подписку
    if request.user.is_authenticated:
        following = Follow.objects.filter(user=request.user, author=author).exists()  # Проверяем наличие подписки.

    posts_count = Post.objects.filter(author=author).count()
    post_list = Post.objects.all().filter(author=author)
    page_obj = pag(post_list, request)
    return render(request, 'posts/profile.html', {
        'profile': author,
        'page_obj': page_obj,
        'posts_count': posts_count,
        'following' : following,  #  передаем для кнопки
    })

def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    comments = post.comments.all()  # Получаем комментарии через related_name='comments'
    form = CommentForm()  # Пустая форма для отображения
    posts_count = Post.objects.filter(author=post.author).count()
    return render(request, 'posts/post_detail.html', {
        'post': post,
        'posts_count': posts_count,
        'comments' : comments,
        'form' : form,
    })

@login_required  # Только для авторизованных польз-ей.
def post_create(request):
    """
    1. Метод form.save() — создаёт объект модели (Post) на основе данных формы.
    Параметр commit=False: "Создай объект, но не сохраняй его в базу данных сразу".
    Эта строка нужна чтобы далее добавить к объекту поле, которого нет в форме.
    2. Поле author объекта post. Объект request.user — это текущий
    авторизованный пользователь, который доступен благодаря декоратору @login_required.
    И так как в модели Post поле author определено как ForeignKey к модели User,
    значит поле author должно содержать объект модели User, а не строку с именем.
    """
    groups = Group.objects.all()  # Получаем группы для выпадающего меню в шаблоне.
    # Форма сразу для GET и POST запросов.
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
    )

    if request.method == 'POST' and form.is_valid():  # POST запрос идет сюда.
        post = form.save(commit=False)  # 1.
        post.author = request.user  # 2.
        post.save()  # Cохраняет объект post в базу данных.
        return redirect('posts:profile', username=request.user.username)

    # GET и невалидная форма сюда:
    return render(request, 'posts/create_post.html', {'form': form, 'groups': groups})

@login_required  # Только для автор-ых пользователей.
def post_edit(request, post_id):
    post = get_object_or_404(Post, pk=post_id)  # Запрашиваем объект модели Post - редактируемый пост.
    groups = Group.objects.all()
    is_edit = True  # Переменная нужна так как мы используем один шаблон для двух эндпоинтов.

    if post.author != request.user:  # Проверяем, является ли текущий пользователь автором.
        return redirect('posts:post_detail', post_id=post_id)  # Не автор поста получает редирект, автор идет дальше.

    # Форма сразу для GET и POST запросов.
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )

    if request.method == 'POST' and form.is_valid():  # POST запрос идет сюда.
        form.save()
        return redirect('posts:post_detail', post_id=post_id)

    # GET и невалидная форма сюда:
    return render(
        request,
        'posts/create_post.html',
        {'form': form, 'groups': groups, 'is_edit': is_edit, 'post': post},
    )

@login_required
def add_comment(request, post_id):
    # Получаем пост и сохраните его в переменную post.
    post = get_object_or_404(Post, pk=post_id)
    if request.method == 'POST':
        form = CommentForm(request.POST or None)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.author = request.user
            comment.post = post
            comment.save()
        # Если форма невалидна редирект на post_detail
        return redirect('posts:post_detail', post_id=post_id)
    # Если метод не POST редирект на post_detail
    return redirect('posts:post_detail', post_id=post_id)

@login_required
def follow_index(request):
    """
    "Мои подписки"
    author__following__user=request.user - фильтрует посты, где author — любой пользователь,
    на которого подписан request.user через модель Follow.
    select_related - ускоряет рендеринг, загружая `author` (для имени) и `group` (для ссылок) в одном запросе.
    """
    post_list = Post.objects.filter(author__following__user=request.user).select_related('author', 'group')
    page_obj = pag(post_list, request)
    return render(request, 'posts/follow.html', {
        'page_obj': page_obj,
        'follow': True,
    })

@login_required
def profile_follow(request, username):
    """
    "Подписаться на пользователя"
    Берем текущего пользователя из запроса user=request.user, а автора из переданного контекста username.
    """
    author = get_object_or_404(User, username=username) #  Берем автора поста из контекста запроса

    # POST запрос идет сюда.
    if request.method == 'POST' and not Follow.objects.filter(user=request.user, author=author).exists():
        Follow.objects.create(user=request.user, author=author)

    # GET, подписка уже есть и финальный редирект - сюда:
    return redirect('posts:profile', username=username)

@login_required
def profile_unfollow(request, username):
    """
    "Отписаться"
    Берем текущего пользователя из запроса user=request.user, а автора из переданного контекста username.
    """
    author = get_object_or_404(User, username=username)  # Берем автора поста из контекста запроса
    follow = Follow.objects.filter(user=request.user, author=author) # Берем запись о подписке

    # POST запрос идет сюда.
    if request.method == 'POST' and follow.exists():
        follow.delete()

    # GET, подписка уже есть и финальный редирект - сюда:
    return redirect('posts:profile', username=username)