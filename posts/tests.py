from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Post

User = get_user_model()

DEFAULT_USERNAME = 'normal'
DEFAULT_EMAIL = 'email@domain.com'
DEFAULT_PASSWORD = '1234'
DEFAULT_FIRST_NAME = 'name'
DEFAULT_LAST_NAME = 'last_name'

DEFAULT_POST_TEXT = 'post text'


class PostsTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username=DEFAULT_USERNAME,
            email=DEFAULT_EMAIL,
            password=DEFAULT_PASSWORD,
            first_name=DEFAULT_FIRST_NAME,
            last_name=DEFAULT_LAST_NAME
        )

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.not_authorized_client = Client()

        self.text_content = DEFAULT_POST_TEXT
        self.post = Post.objects.create(
            text=self.text_content, author=self.user)

    def _check_post_content(self, post, post_text):
        self.assertIsInstance(post, Post, msg='Тип содержимого не пост')
        self.assertEqual(
            post.text, post_text,
            msg='Текст поста не соответствует')

    def _check_paginated_page_response(self, response, post_text):
        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api создания поста')
        self.assertEqual(
            len(response.context['page']), 1,
            msg='В ответе нет страницы с постом'
        )
        self.assertEqual(
            response.context['page'].number, 1,
            msg='Внутри страницы нет поста')
        self.assertIsInstance(
            response.context['page'][0], Post, msg='Тип содержимого не пост')
        self._check_post_content(response.context['page'][0], post_text)

    def _check_content_pages(self, post_text=DEFAULT_POST_TEXT):
        response = self.not_authorized_client.get(reverse('index'))
        self._check_paginated_page_response(response, post_text)

        response = self.not_authorized_client.get(
            reverse('profile', kwargs={'username': DEFAULT_USERNAME})
        )
        self._check_paginated_page_response(response, post_text)

        response = self.not_authorized_client.get(
            reverse(
                'post',
                kwargs={
                    'username': DEFAULT_USERNAME, 'post_id': self.post.id}))

        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api страницы поста')

        self.assertIsInstance(
            response.context['post'], Post, msg='Внутри страницы нет поста')

        self._check_post_content(response.context['post'], post_text)

    def test_profile_url(self):
        response = self.authorized_client.get(
            reverse('profile', kwargs={'username': DEFAULT_USERNAME})
        )
        self.assertEqual(response.status_code, 200)

    def test_create_new_post_after_authorization(self):
        posts_on_start = Post.objects.all().count()
        new_post_text = 'new post text'
        response = self.authorized_client.post(
            reverse('new_post'),
            {
                'text': new_post_text,
            },
            follow=True)
        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api создания поста')

        posts_after = Post.objects.all().count()
        self.assertEqual(
            posts_after, posts_on_start + 1,
            msg='Количество постов не увеличилось на 1')
        
        new_post = Post.objects.latest('pub_date')
        self._check_post_content(new_post, new_post_text)

    def test_create_new_post_not_authorized(self):
        posts_on_start = Post.objects.all().count()
        response = self.not_authorized_client.post(
            reverse('new_post'),
            {
                'text': DEFAULT_POST_TEXT,
            },
            follow=True)

        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api создания поста')

        self.assertEqual(
            response.resolver_match.url_name,
            'login',  msg='Нет редиректа на логин')

        posts_after = Post.objects.all().count()
        self.assertEqual(
            posts_on_start, posts_after,
            msg='В базе данных есть пост неавторизованного пользователя'
        )

    def test_post_on_content_pages(self):
        self._check_content_pages()

    def test_editied_post_on_content_pages(self):
        edited_text_content = 'changed post text'

        response = self.authorized_client.post(
            reverse(
                'post_edit',
                kwargs={
                    'username': DEFAULT_USERNAME, 'post_id': self.post.id
                }
            ),
            {
                'text': edited_text_content,
            },
            follow=True)

        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api редактирования поста')

        self._check_content_pages(edited_text_content)
