import datetime

from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User, GENDER_CHOICES, PARTY_CHOICES
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
    # 2026-09-23 추가: 성별 선택 (남성/여성)
    gender = forms.ChoiceField(label='성별', choices=GENDER_CHOICES, widget=forms.RadioSelect)
    agree_terms = forms.BooleanField(
        label='위 이용약관 및 개인정보 수집·이용에 동의합니다.',
        required=True,
        error_messages={'required': '약관에 동의해야 회원가입을 진행할 수 있습니다.'},
    )

    class Meta:
        model = User
        fields = ['username', 'nickname', 'email', 'birth_date', 'party', 'gender']
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


class ProfileForm(forms.ModelForm):
    """마이페이지 > 내 정보 변경 폼 (2026-09-24).

    아이디/닉네임/진영은 변경 불가라서 폼 필드 자체에 넣지 않았습니다.
    (화면에는 읽기 전용으로 보여주기만 하고, 누가 요청을 조작해서 값을 보내도
    폼에 없는 필드라 저장되지 않습니다.)
    """

    birth_date = forms.DateField(
        label='생년월일',
        widget=forms.SelectDateWidget(
            years=range(_CURRENT_YEAR - 100, _CURRENT_YEAR + 1),
            empty_label=('년도', '월', '일'),
        ),
    )
    gender = forms.ChoiceField(label='성별', choices=GENDER_CHOICES, widget=forms.RadioSelect)

    class Meta:
        model = User
        fields = ['email', 'birth_date', 'gender']
        labels = {'email': '이메일'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True

    def clean_email(self):
        email = self.cleaned_data['email']
        # 본인이 이미 쓰던 이메일은 그대로 저장 가능, 다른 회원이 쓰는 이메일만 막음
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('이미 사용 중인 이메일입니다.')
        return email
