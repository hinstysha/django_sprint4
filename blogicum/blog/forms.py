from django import forms
from .models import Post, Comment


class PostForm(forms.ModelForm):
    class Meta:
        model = Post
        exclude = ('author',)
        widgets = {
            'pub_date': forms.DateTimeInput(
                format='%Y-%m-%dT%H:%M',
                attrs={'type': 'datetime-local'}
            ),
        }

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if first_name:
            return first_name.split()[0]
        return first_name


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Напишите ваш комментарий...',
                'required': True,
            }),
        }
        labels = {
            'text': 'Комментарий',
        }
