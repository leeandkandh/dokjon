from django.conf import settings
from django.db import models


class Inquiry(models.Model):
    """광고/제휴 문의 · 고객센터 문의 (2026-09-24).

    문의 폼으로 들어온 내용은 메일 발송 성공 여부와 상관없이 항상 여기에 저장됩니다.
    (메일 설정이 안 돼 있거나 발송이 실패해도 관리자 페이지 > 문의 관리에서 확인 가능)
    """

    TYPE_SUPPORT = 'support'
    TYPE_AD = 'ad'
    TYPE_CHOICES = [
        (TYPE_SUPPORT, '고객센터 문의'),
        (TYPE_AD, '광고/제휴 문의'),
    ]

    inquiry_type = models.CharField('문의 유형', max_length=20, choices=TYPE_CHOICES, default=TYPE_SUPPORT)
    name = models.CharField('이름(회사명)', max_length=50)
    email = models.EmailField('회신 받을 이메일')
    subject = models.CharField('제목', max_length=100)
    message = models.TextField('내용', max_length=3000)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='로그인 회원',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inquiries',
    )
    email_sent = models.BooleanField('메일 발송 성공', default=False)
    is_answered = models.BooleanField('답변 완료', default=False)
    created_at = models.DateTimeField('접수일', auto_now_add=True)

    class Meta:
        verbose_name = '문의'
        verbose_name_plural = '문의 관리'
        ordering = ['-created_at']

    def __str__(self):
        return f'[{self.get_inquiry_type_display()}] {self.subject}'
