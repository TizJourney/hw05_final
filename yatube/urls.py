from django.contrib import admin
from django.contrib.flatpages import views as flatpages_views
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static

handler404 = "posts.views.page_not_found"  # noqa
handler500 = "posts.views.server_error"  # noqa

urlpatterns = [
    path('auth/', include('users.urls')),
    path('auth/', include('django.contrib.auth.urls')),
    path('about/', include('django.contrib.flatpages.urls')),
    path('admin/', admin.site.urls),

    path('', include('posts.urls')),
]

urlpatterns += [
    path(
        'about-author/',
        flatpages_views.flatpage,
        {'url': '/author/'},
        name='about_author'
    ),
    path(
        'about-spec/',
        flatpages_views.flatpage,
        {'url': '/spec/'},
        name='about_author'),
]

if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT
    )
    urlpatterns += static(
        settings.STATIC_URL,
        document_root=settings.STATIC_ROOT
    )
