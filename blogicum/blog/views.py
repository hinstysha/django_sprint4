from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import UpdateView, ListView, CreateView, DeleteView
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Count
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required

from blog.models import Post, Category, Comment
from .forms import PostForm, CommentForm
from .utils import paginate_queryset
from .filters import get_published_posts, filter_posts_for_profile


class PostCreateView(LoginRequiredMixin, CreateView):
    """
    Представление для создания нового поста.
    Ограничено для авторизованных пользователей через LoginRequiredMixin.
    """

    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        """Автоматическая привязка текущего пользователя как автора поста."""
        form.instance.author = self.request.user
        messages.success(self.request, 'Пост успешно создан!')
        return super().form_valid(form)

    def get_success_url(self):
        """Перенаправление на страницу профиля автора после успешного создания."""
        return reverse_lazy('blog:profile', kwargs={'username': self.request.user.username})


class PostUpdateView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования существующего поста."""

    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        """Проверка прав: только автор может редактировать пост."""
        self.object = self.get_object()
        if self.object.author != request.user:
            return redirect('blog:post_detail', post_id=self.object.id)
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Возврат на страницу детального просмотра поста после редактирования."""
        return reverse_lazy('blog:post_detail', kwargs={'post_id': self.object.id})


class PostDeleteView(LoginRequiredMixin, DeleteView):
    """Представление для удаления поста с проверкой прав доступа."""

    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    success_url = reverse_lazy('blog:index')

    def dispatch(self, request, *args, **kwargs):
        """Проверка прав: только автор может удалить свой пост."""
        self.object = self.get_object()
        if self.object.author != request.user:
            return redirect('blog:post_detail', post_id=self.object.id)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Добавление формы в контекст для подтверждения действия."""
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.object)
        return context


class CommentPermissionMixin(LoginRequiredMixin):
    """
    Миксин для централизованной проверки прав на управление комментариями.
    Используется в представлениях редактирования и удаления комментариев.
    """

    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        """Проверка владельца комментария перед выполнением действия."""
        self.object = self.get_object()
        if self.object.author != request.user:
            return redirect('blog:post_detail', post_id=self.kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        """Возврат на страницу поста после изменения/удаления комментария."""
        return reverse_lazy('blog:post_detail', kwargs={'post_id': self.kwargs['post_id']})


class CommentUpdateView(CommentPermissionMixin, UpdateView):
    """Представление для редактирования комментария."""

    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'


class CommentDeleteView(CommentPermissionMixin, DeleteView):
    """Представление для удаления комментария."""

    model = Comment
    template_name = 'blog/comment.html'

    def get_context_data(self, **kwargs):
        """Очистка контекста от лишней формы при удалении."""
        context = super().get_context_data(**kwargs)
        context.pop('form', None)
        return context


def index(request):
    """Отображение главной страницы со списком всех опубликованных постов."""
    post_list = get_published_posts(Post)
    page_obj = paginate_queryset(post_list, request, per_page=10)
    context = {'page_obj': page_obj}
    return render(request, 'blog/index.html', context)


def post_detail(request, post_id):
    """Отображение детальной информации о посте и формы комментариев."""
    post = get_object_or_404(Post, pk=post_id)

    if post.author != request.user:
        post = get_object_or_404(
            Post.objects.select_related('author', 'location', 'category'),
            pk=post_id,
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        )

    form = CommentForm()
    comments = post.comments.select_related('author')

    context = {
        'post': post,
        'form': form,
        'comments': comments,
    }
    return render(request, 'blog/detail.html', context)


def category_posts(request, category_slug):
    """Отображение списка постов, отфильтрованных по конкретной категории."""
    category = get_object_or_404(
        Category, slug=category_slug, is_published=True)
    post_list = get_published_posts(Post).filter(category=category)
    page_obj = paginate_queryset(post_list, request, per_page=10)

    context = {
        'page_obj': page_obj,
        'category': category,
    }
    return render(request, 'blog/category.html', context)


class UserProfileView(ListView):
    """Отображение страницы профиля пользователя со списком его постов."""

    template_name = 'blog/profile.html'
    context_object_name = 'page_obj'
    paginate_by = 10

    def get_queryset(self):
        """Аннотация количества комментариев к постам пользователя."""
        username = self.kwargs.get('username')
        self.profile_user = get_object_or_404(User, username=username)

        user_posts = Post.objects.filter(
            author=self.profile_user
        ).annotate(
            comment_count=Count('comments')
        ).order_by('-created_at')

        is_owner = self.request.user.is_authenticated and self.request.user == self.profile_user
        return filter_posts_for_profile(user_posts, is_owner)

    def get_context_data(self, **kwargs):
        """Передача данных профиля пользователя в контекст шаблона."""
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile_user
        return context


class EditProfileView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования данных текущего пользователя."""

    model = User
    template_name = 'blog/user.html'
    fields = ('first_name', 'last_name', 'username', 'email')

    def get_object(self):
        """Всегда возвращает текущего авторизованного пользователя."""
        return self.request.user

    def get_success_url(self):
        """Возврат на страницу профиля после сохранения изменений."""
        return reverse_lazy('blog:profile', kwargs={'username': self.request.user.username})

    def form_valid(self, form):
        """Уведомление об успешном обновлении профиля."""
        messages.success(self.request, 'Профиль успешно обновлен!')
        return super().form_valid(form)


@login_required
def add_comment(request, post_id):
    """Функция обработки формы добавления комментария к посту."""
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
        messages.success(request, 'Ваш комментарий успешно добавлен!')

    return redirect('blog:post_detail', post_id=post_id)
