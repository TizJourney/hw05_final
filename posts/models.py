from django.contrib.auth import get_user_model
from django.db import models

User = get_user_model()


class Group(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=200)
    description = models.TextField()

    def __str__(self):
        return self.title


class Post(models.Model):
    text = models.TextField(
        'Текст публикации',
        help_text='Содержимое поста. Обязательно к заполнению.')
    pub_date = models.DateTimeField(
        'Дата публикации',
        auto_now_add=True,
        help_text='Дата публикации. По-умолчанию выставляется текущее время.'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts',
        verbose_name='Автор',
        help_text='Автор публикации. Заполняется автоматически.'
    )
    group = models.ForeignKey(
        Group,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='posts',
        verbose_name='Группа',
        help_text='Выберите группу поста из списка. Опционально.'
    )
    image = models.ImageField(
        upload_to='posts/',
        blank=True,
        null=True,
        verbose_name='Изображение',
        help_text='Загрузка изображения. Опционально.'
    )

    class Meta:
        ordering = ('-pub_date',)

    def __str__(self):
        text_sample = self.text[:12]
        author = self.author
        return f'@{author}: {text_sample}'


class Comment(models.Model):
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Автор',
        help_text='Автор комментария. Заполняется автоматически.',
    )
    post = models.ForeignKey(
        Post,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Пост',
        help_text='Пост, к которому относится комментарий.'
    )
    text = models.TextField(
        'Комментарий',
        help_text='Содержимое комментария. Обязательно к заполнению.')
    created = models.DateTimeField(
        'Время создания',
        auto_now_add=True,
        help_text='Время создания. По-умолчанию выставляется текущее время.'
    )

    class Meta:
        ordering = ('-created',)

    def __str__(self):
        text_sample = self.text[:12]
        author = self.author
        return f'@{author}: {text_sample}'


class Follow(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='follower',
        verbose_name='Подписчик',
        help_text='Пользователь, который подписывается.',
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following',
        verbose_name='Автор',
        help_text='Пользователь, которого подписываются.',
    )

    class Meta:
        unique_together = ('user', 'author')

    def __str__(self):
        user = self.user
        author = self.author
        return f'Подписка @{user} на @{author}'
