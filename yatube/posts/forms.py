from django import forms
from .models import Post, Comment
from django.core.validators import MinLengthValidator


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        fields = ('text', 'group', 'image')

    text = forms.CharField(
        validators=[MinLengthValidator(2, message="Пост должен содержать минимум 2 символа")]
    )


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)