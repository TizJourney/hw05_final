from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, PostForm
from .models import Comment, Follow, Group, Post

POSTS_PER_PAGE = 10

User = get_user_model()


def page_not_found(request, exception):
    return render(
        request,
        "misc/404.html",
        {"path": request.path},
        status=404
    )


def server_error(request):
    return render(request, "misc/500.html", status=500)


def _prepare_post_content(post_query, page_number):
    paginator = Paginator(post_query, POSTS_PER_PAGE)
    page = paginator.get_page(page_number)
    return {'page': page, 'paginator': paginator}


def _prepare_profile_content(profile_user, guest_user=None):
    post_count = profile_user.posts.all().count()
    follower_count = profile_user.follower.all().count()
    following_count = profile_user.following.all().count()

    following = False
    if guest_user is not None and guest_user.is_authenticated:
        following = guest_user.follower.filter(author=profile_user).exists()

    context = {
        'post_count': post_count,
        'profile_user': profile_user,
        'follower_count': follower_count,
        'following_count': following_count,
        'following': following,
    }
    return context


def index(request):
    page_number = request.GET.get('page')
    post_query = Post.objects.select_related(
        'author').select_related('group').all()

    context = _prepare_post_content(post_query, page_number)

    return render(
        request,
        'posts/index.html',
        context
    )


def group_posts(request, slug):
    page_number = request.GET.get('page')

    group = get_object_or_404(Group, slug=slug)
    group_posts = group.posts.select_related(
        'author').select_related('group').all()

    context = {'group': group}
    context.update(_prepare_post_content(group_posts, page_number))

    return render(request, 'group.html', context)


def profile(request, username):
    page_number = request.GET.get('page')

    user = get_object_or_404(User, username=username)
    post_list = user.posts.select_related(
        'author').select_related('group').all()

    context = _prepare_post_content(post_list, page_number)
    context.update(_prepare_profile_content(user, request.user))

    return render(request, 'posts/profile.html', context)


def post_view(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)

    comments = post.comments.all()
    comment_form = CommentForm()

    context = {
        'post': post,
        'comment_form': comment_form,
        'comments': comments,
    }
    context.update(_prepare_profile_content(post.author, request.user))

    return render(request, 'posts/post_view.html', context)


@login_required
def new_post(request):
    if request.method == 'POST':
        form = PostForm(request.POST, files=request.FILES or None)
        if form.is_valid():
            form.instance.author = request.user
            form.save()
            return redirect('index')

        return render(
            request,
            'posts/new.html',
            {'form': form, 'new_post': True}
        )

    form = PostForm()
    return render(request, 'posts/new.html', {'form': form, 'new_post': True})


@login_required
def post_edit(request, username, post_id):
    post = get_object_or_404(Post, id=post_id, author__username=username)

    if post.author != request.user:
        return redirect('post', username, post_id)

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )

    if form.is_valid():
        form.save()
        return redirect('post', username, post_id)

    return render(
        request,
        'posts/post_edit.html',
        {'post': post, 'form': form}
    )


@login_required
def add_comment(request, username, post_id):
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if not form.is_valid():
            redirect('post', username=username, post_id=post_id)

        form.instance.author = request.user
        form.instance.post = get_object_or_404(
            Post,
            id=post_id,
            author__username=username
        )
        form.save()
        return redirect('post', username=username, post_id=post_id)

    form = CommentForm()
    return redirect('post', username=username, post_id=post_id)


@login_required
def follow_index(request):
    follows = Follow.objects.select_related('author').filter(user=request.user)
    followed_users = list(set([follow.author for follow in follows]))
    post_query = Post.objects.filter(author__in=followed_users)

    context = {'follower': request.user}

    page_number = request.GET.get('page')
    context.update(_prepare_post_content(post_query, page_number))

    return render(request, "posts/follow.html", context)


@login_required
def profile_follow(request, username):
    #нельзя подписываться на несуществующего пользователя
    author = get_object_or_404(User, username=username)

    #нельзя подписываться на самого себя
    if author == request.user:
        return redirect('profile', username=username)

    follow, created = Follow.objects.get_or_create(
        author=author,
        user=request.user
    )

    return redirect('profile', username=username)

@login_required
def profile_unfollow(request, username):
    #нельзя отписываться от несуществующего пользователя
    author = get_object_or_404(User, username=username)

    #нельзя отписаться от несуществующей подписки
    follow = get_object_or_404(
        Follow,
        author=author,
        user=request.user
    )
    follow.delete()

    return redirect('profile', username=username)
