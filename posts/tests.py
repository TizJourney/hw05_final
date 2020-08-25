from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Post, Follow

User = get_user_model()

DEFAULT_USERNAME = 'normal'
DEFAULT_EMAIL_TEMPLATE = '{}@domain.com'
DEFAULT_FIRST_NAME_TEMPLATE = '{}_first_name'
DEFAULT_LAST_NAME_TEMPLATE = '{}_last_name'

DEFAULT_POST_TEXT = 'post text'


def _create_user(username=DEFAULT_USERNAME):
    return User.objects.create_user(
        username=username,
        email=DEFAULT_EMAIL_TEMPLATE.format(username),
        password=username,
        first_name=DEFAULT_FIRST_NAME_TEMPLATE.format(username),
        last_name=DEFAULT_LAST_NAME_TEMPLATE.format(username),
    )

#набор вспомогательных классов для тестов


class PostsTestWithHelpers(TestCase):
    def _check_post_content(self, post, post_text):
        self.assertIsInstance(post, Post, msg='Тип содержимого не пост')
        self.assertEqual(
            post.text, post_text,
            msg='Текст поста не соответствует')

    def _check_paginated_page_empty_response(self, response):
        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api создания поста')
        self.assertEqual(
            len(response.context['page']), 0,
            msg='В ответе есть какое-то содержимое'
        )


    def _check_paginated_page_response(self, response, post_text):
        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api')
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


class PostsTest(PostsTestWithHelpers):
    def setUp(self):
        self.user = _create_user()

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.not_authorized_client = Client()

        self.text_content = DEFAULT_POST_TEXT
        self.post = Post.objects.create(
            text=self.text_content, author=self.user)

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


class FollowerTest(PostsTestWithHelpers):
    def setUp(self):
        #автор, авторизован
        self.author_username = 'author'
        self.author_user = _create_user(self.author_username)

        self.author_client = Client()
        self.author_client.force_login(self.author_user)
        self.author_first_post_text = 'first post'
        #пользователь, ни на кого не подписан
        self.user = _create_user()

        #авторизованный клиент пользователя
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        #пользователь, подписан на автора, авторизован
        self.follower_username = 'follower'
        self.follower_user = _create_user(self.follower_username)
        self.follower_client = Client()
        self.follower_client.force_login(self.follower_user)
        Follow.objects.create(
            user=self.follower_user,
            author=self.author_user
        )

    def _calculated_follow_count(self, follower, author=None):
        if author is not None:
            return Follow.objects.filter(
                user=follower,
                author=author
            ).count()

        return Follow.objects.filter(user=follower).count()

    def test_authorized_user_follow_and_unfollow(self):
        self.assertEqual(
            self._calculated_follow_count(self.user), 0,
            msg='Не должно быть подписок до начала теста'
        )

        response = self.authorized_client.get(
            reverse('profile_follow', args=(self.author_username,)),
            follow=True
        )

        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка при попытке подписаться на автора')

        self.assertEqual(
            self._calculated_follow_count(self.user), 1,
            msg='Не добавилась подписка'
        )

        self.assertEqual(
            self._calculated_follow_count(self.user, self.author_user), 1,
            msg='Не добавилась подписка на автора'
        )

        response = self.authorized_client.get(
            reverse('profile_unfollow', args=(self.author_username,)),
            follow=True
        )

        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка при попытке отписаться от автора')

        self.assertEqual(
            self._calculated_follow_count(self.user, self.author_user), 0,
            msg='Не уменьшилось количество подписок после отписки'
        )

    def test_author_posts_on_follower(self):

        response = self.authorized_client.get(reverse('follow_index'))
        #не должен видеть постов
        self._check_paginated_page_empty_response(response)

        response = self.follower_client.get(reverse('follow_index'))
        #не должен видеть постов
        self._check_paginated_page_empty_response(response)

        #автор пишет пост
        response = self.author_client.post(
            reverse('new_post'),
            {
                'text': self.author_first_post_text,
            },
            follow=True)
        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api создания поста')

        response = self.authorized_client.get(reverse('follow_index'))
        #не подписанный пользователь все ещё не должен видеть постов
        self._check_paginated_page_empty_response(response)

        response = self.follower_client.get(reverse('follow_index'))
        #подписанный пользователь должен увидеть новый пост
        self._check_paginated_page_response(
            response,
            self.author_first_post_text
        )
