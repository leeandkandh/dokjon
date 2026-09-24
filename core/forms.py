from django import forms

from .models import Inquiry


class InquiryForm(forms.ModelForm):
    """광고/제휴 · 고객센터 문의 폼 (2026-09-24)."""

    # 스팸봇 방지용 숨김 칸(honeypot). 사람은 안 보이니 비워두고, 봇은 채우는 경우가 많습니다.
    website = forms.CharField(required=False, widget=forms.TextInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}))
    agree_privacy = forms.BooleanField(
        label='문의 처리를 위한 개인정보(이름, 이메일) 수집·이용에 동의합니다.',
        required=True,
        error_messages={'required': '개인정보 수집·이용에 동의해야 문의를 보낼 수 있습니다.'},
    )

    class Meta:
        model = Inquiry
        fields = ['inquiry_type', 'name', 'email', 'subject', 'message']
        widgets = {
            'inquiry_type': forms.RadioSelect,
            'message': forms.Textarea(attrs={'rows': 8, 'maxlength': 3000}),
            'subject': forms.TextInput(attrs={'maxlength': 100}),
        }
