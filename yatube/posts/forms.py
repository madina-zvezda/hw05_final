from django.forms import ModelForm

from .models import Post, Comment


class PostForm(ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')
        labels = {
            'text': 'Текст статьи',
            'group': 'Рубрика Вашей статьи'}
        help_texts = {
            'text': 'обязательное поле',
            'group': 'выберите рубрику из списка или оставьте пустым'}


class CommentForm(ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        labels = {
            'text': 'Текст комментария'}
        help_texts = {'text': 'обязательное поле'}
