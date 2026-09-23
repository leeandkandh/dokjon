import bleach
from django import forms

from accounts.validators import contains_banned_word

from .models import Comment, Post

# 에디터(Quill)가 만들어내는 HTML 중에서 허용할 태그/속성만 화이트리스트로 정의합니다.
# 글쓰기 폼은 결국 <textarea name="content">에 원본 HTML이 그대로 들어오므로
# (JS를 꺼도, 개발자도구로 조작해도 서버까지 도달하는 값은 똑같습니다),
# 여기서 걸러주지 않으면 <script> 같은 위험한 태그가 그대로 저장/렌더링될 수 있습니다.
ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'span',
    'h1', 'h2', 'h3', 'blockquote', 'code', 'pre',
    'ul', 'ol', 'li', 'a', 'img',
]
ALLOWED_ATTRS = {
    'a': ['href', 'target', 'rel'],
    'img': ['src', 'alt'],
    'span': ['class'],
}


class PostForm(forms.ModelForm):
    """글쓰기/글수정 폼. board(게시판)와 author(작성자)는 URL/로그인 정보로
    views.py에서 채우므로, 사용자가 직접 입력하는 건 제목/내용뿐입니다."""

    class Meta:
        model = Post
        fields = ['title', 'content']
        labels = {'title': '제목', 'content': '내용'}
        widgets = {
            'title': forms.TextInput(attrs={'maxlength': 200}),
            'content': forms.Textarea(attrs={'rows': 15}),
        }

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if not title:
            raise forms.ValidationError('제목을 입력해주세요.')
        # 금칙어 목록은 지금은 accounts/validators.py의 임시 목록을 그대로 씁니다.
        # 8단계(금칙어 시스템)에서 DB 기반으로 확장할 예정입니다.
        if contains_banned_word(title):
            raise forms.ValidationError('제목에 사용할 수 없는 단어가 포함되어 있습니다.')
        return title

    def clean_content(self):
        raw_html = self.cleaned_data['content'].strip()

        # 1) 허용 목록에 없는 태그/속성(script, onclick 등)을 모두 제거
        cleaned_html = bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)

        # 2) 글자만 뽑아서 "내용이 비어있는지"와 "금칙어 포함 여부"를 검사
        #    (이미지만 넣고 글자가 없는 경우는 허용합니다)
        text_only = bleach.clean(cleaned_html, tags=[], strip=True).strip()
        has_image = '<img' in cleaned_html

        if not text_only and not has_image:
            raise forms.ValidationError('내용을 입력해주세요.')
        if contains_banned_word(text_only):
            raise forms.ValidationError('내용에 사용할 수 없는 단어가 포함되어 있습니다.')

        return cleaned_html


class CommentForm(forms.ModelForm):
    """댓글 작성 폼. 에디터 없이 일반 텍스트만 받습니다."""

    class Meta:
        model = Comment
        fields = ['content']
        labels = {'content': '댓글'}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 2, 'maxlength': 1000, 'placeholder': '댓글을 입력하세요'}),
        }

    def clean_content(self):
        content = self.cleaned_data['content'].strip()
        if not content:
            raise forms.ValidationError('댓글 내용을 입력해주세요.')
        if contains_banned_word(content):
            raise forms.ValidationError('댓글에 사용할 수 없는 단어가 포함되어 있습니다.')
        return content
