"""Для отображения картинок import settings и import static.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('', include('posts.urls', namespace = 'posts')),
    path('admin/', admin.site.urls),
    path('auth/', include('users.urls', namespace = 'users')),
    path('about/', include('about.urls', namespace='about')),
]

# Кастомизация функций ошибки.
handler404 = 'core.views.page_not_found'
handler500 = 'core.views.server_error'
handler403 = 'core.views.permission_denied'

# Настройка отображения картинок, работает в режиме отладки.
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL, document_root=settings.MEDIA_ROOT
    )