import datetime

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, PARTY_CHOICES
from .validators import contains_banned_word

_CURRENT_YEAR = datetime.date.today().year


class SignUpForm(UserCreationForm):
    # 생년월일: 텍스트 입력 대신 년/월/일 각각 select 박스로 입력
    birth_date = forms.DateField(
        label='생년월일',
        widget=forms.SelectDateWidget(
            years=range(_CURRENT_YEAR - 100, _CURRENT_YEAR + 1),
            empty_label=('년도', '월', '일'),
        ),
    )
    party = forms.ChoiceField(label='진영', choices=PARTY_CHOICES)
    agree_terms = forms.BooleanField(
        label='위 이용약관 및 개인정보 수집·이용에 동의합니다.',
        required=True,
        error_messages={'required': '약관에 동의해야 회원가입을 진행할 수 있습니다.'},
    )

    class Meta:
        model = User
        fields = ['username', 'nickname', 'email', 'birth_date', 'party']
        labels = {
            'username': '아이디',
            'nickname': '닉네임',
            'email': '이메일',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_username(self):
        username = self.cleaned_data['username']
        if contains_banned_word(username):
            raise forms.ValidationError('아이디에 사용할 수 없는 단어가 포함되어 있습니다.')
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError('이미 사용 중인 아이디입니다.')
        return username

    def clean_nickname(self):
        nickname = self.cleaned_data['nickname']
        if contains_banned_word(nickname):
            raise forms.ValidationError('닉네임에 사용할 수 없는 단어가 포함되어 있습니다.')
        if User.objects.filter(nickname__iexact=nickname).exists():
            raise forms.ValidationError('이미 사용 중인 닉네임입니다.')
        return nickname

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('이미 사용 중인 이메일입니다.')
        return email
