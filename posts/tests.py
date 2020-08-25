from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from .models import Post, Follow

User = get_user_model()

DEFAULT_USERNAME = 'normal'
DEFAULT_EMAIL_TEMPLATE = '{}@domain.com'
DEFAULT_FIRST_NAME_TEMPLATE = '{}_first_name'
DEFAULT_LAST_NAME_TEMPLATE = '{}_last_name'

DEFAULT_POST_TEXT = 'текст поста'

NOT_EXISTING_URL = '/not_existring_url/'


def _create_user(username=DEFAULT_USERNAME):
    return User.objects.create_user(
        username=username,
        email=DEFAULT_EMAIL_TEMPLATE.format(username),
        password=username,
        first_name=DEFAULT_FIRST_NAME_TEMPLATE.format(username),
        last_name=DEFAULT_LAST_NAME_TEMPLATE.format(username),
    )

class PostContext:
    def __init__(self, post_text, contain_image=False):
        self.text = post_text
        self.contain_image = contain_image


class PostsTestWithHelpers(TestCase):
    def _check_post_content(self, post, post_context):
        self.assertIsInstance(post, Post, msg='Тип содержимого не пост')
        self.assertEqual(
            post.text, post_context.text,
            msg='Текст поста не соответствует')

    def _check_paginated_page_empty_response(self, response):
        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api создания поста')
        self.assertEqual(
            len(response.context['page']), 0,
            msg='В ответе есть какое-то содержимое'
        )

    def _check_paginated_page_response(self, response, post_contexts):
        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api')

        self.assertEqual(
            response.context['page'].number, 1,
            msg='Количество страниц с ответами не совпадает')

        self.assertEqual(
            len(response.context['page']), len(post_contexts),
            msg='Количество постов в ответе не совпадает'
        )

        if not post_contexts:
            #пустая страница, дальше проверять нет смысла
            return

        
        for post_item, context in zip(response.context['page'], post_contexts):
            self.assertIsInstance(
                post_item,
                Post,
                msg='Тип содержимого не пост'
            )
            self._check_post_content(post_item, context)

    def _check_content_pages(self, posts_context, client):
        response = client.get(reverse('index'))

        self._check_paginated_page_response(response, posts_context)

        response = client.get(
            reverse('profile', kwargs={'username': DEFAULT_USERNAME})
        )
        self._check_paginated_page_response(response, posts_context)


    def _check_single_post(self, post_context, client, username, post_id):
        response = client.get(
            reverse(
                'post',
                kwargs={
                    'username': username,
                    'post_id': post_id
                }
            )
        )

        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api страницы поста')

        self.assertIsInstance(
            response.context['post'], Post, msg='Внутри страницы нет поста')

        self._check_post_content(response.context['post'], post_context)


class PostsTest(PostsTestWithHelpers):
    def setUp(self):
        self.user = _create_user()

        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.not_authorized_client = Client()

        self.text_content = DEFAULT_POST_TEXT
        self.post = Post.objects.create(
            text=self.text_content, author=self.user)
        self.post_context = PostContext(self.text_content)            

    def test_404(self):
        response = self.authorized_client.get(NOT_EXISTING_URL)
        self.assertEqual(response.status_code, 404)


    def test_profile_url(self):
        response = self.authorized_client.get(
            reverse('profile', kwargs={'username': DEFAULT_USERNAME})
        )
        self.assertEqual(response.status_code, 200)

    def test_create_new_post_after_authorization(self):
        posts_on_start = Post.objects.all().count()
        new_post_text = 'новый текст поста'
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
        new_post_context = PostContext(new_post_text)
        self._check_post_content(new_post, new_post_context)

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
        self._check_content_pages(
            [self.post_context],
            self.not_authorized_client
        )
        self._check_single_post(
            self.post_context,
            self.not_authorized_client,
            DEFAULT_USERNAME,
            self.post.id
        )

    def test_editied_post_on_content_pages(self):
        edited_text_content = 'редактированный текст'

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

        edited_post_context = PostContext(edited_text_content)
        self._check_content_pages(
            [edited_post_context],
            self.authorized_client
        )
        self._check_single_post(
            edited_post_context,
            self.authorized_client,
            DEFAULT_USERNAME,
            self.post.id
        )

    def test_image_content_pages(self):
        image_post_text_content = 'пост картинкой'

        #добавим пост с картинкой
        response = self.authorized_client.post(
            reverse('new_post'),
            {
                'text': image_post_text_content,
                # 'image': image,
            },
            follow=True)

        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api создания нового поста')

        image_post_context = PostContext(
            image_post_text_content,
            contain_image=True
        )
        self._check_content_pages(
            [image_post_context, self.post_context],
            self.authorized_client
        )

        new_post = Post.objects.latest('pub_date')
        self._check_single_post(
            image_post_context,
            self.authorized_client,
            DEFAULT_USERNAME,
            new_post.id
        )



    def _check_number_comments(self):
        return self.post.comments.all().count()

    def _check_comment_content(self, comment_text):
        comment = self.post.comments.all().latest('created')
        self.assertEqual(
            comment.text, comment_text,
            msg='Содержимое комментария некорректно'
        )

    def test_only_authorized_user_can_add_comments(self):
        comment_text = 'текст комментария'
        self.assertEqual(
            self._check_number_comments(), 0,
            msg='Количество комментариев до проверки должно быть 0'
        )

        response = self.authorized_client.post(
            reverse(
                'add_comment',
                kwargs={
                    'username': DEFAULT_USERNAME, 'post_id': self.post.id
                }
            ),
            {
                'text': comment_text,
            },
            follow=True)
        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api добавления комментария')

        self.assertEqual(
            self._check_number_comments(), 1,
            msg='Теперь должен быть 1 комментарий'
        )
        self._check_comment_content(comment_text)

        response = self.not_authorized_client.post(
            reverse(
                'add_comment',
                kwargs={
                    'username': DEFAULT_USERNAME, 'post_id': self.post.id
                }
            ),
            {
                'text': comment_text,
            },
            follow=True)

        self.assertEqual(
            response.status_code, 200,
            msg='Ошибка вызова api добавления комментария')

        self.assertEqual(
            self._check_number_comments(), 1,
            msg='Количество комментариев не должно изменится'
        )


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
        self._check_paginated_page_response(response, [])

        response = self.follower_client.get(reverse('follow_index'))
        #не должен видеть постов
        self._check_paginated_page_response(response, [])

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
        self._check_paginated_page_response(response, [])

        response = self.follower_client.get(reverse('follow_index'))
        #подписанный пользователь должен увидеть новый пост
        post_contexts = [PostContext(self.author_first_post_text)]
        self._check_paginated_page_response(response, post_contexts)
