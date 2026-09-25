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


# ---------------- 접속 통계 (2026-09-25) ----------------
# 관리자 통계 대시보드(/stats/)용 기록입니다. core/middleware.py가 페이지를 볼 때마다 채웁니다.
# 개인정보 보호: IP 원문은 저장하지 않고, "날짜 + 비밀키 + IP + 브라우저 정보"를 되돌릴 수 없게
# 변환(해시)한 값만 저장합니다. 날짜가 바뀌면 같은 사람도 다른 값이 되므로 날짜를 넘어 추적할 수 없습니다.
# 추적용 쿠키도 새로 심지 않습니다.

class VisitorDay(models.Model):
    """하루 동안의 방문자 1명 (= 그날의 순방문자 1명)."""

    date = models.DateField('날짜', db_index=True)
    visitor_hash = models.CharField('방문자 식별값(해시)', max_length=64)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, verbose_name='회원', on_delete=models.SET_NULL,
        null=True, blank=True, related_name='visit_days',
    )
    page_views = models.PositiveIntegerField('페이지뷰', default=0)
    source = models.CharField('유입 경로', max_length=40, blank=True)
    is_mobile = models.BooleanField('모바일', default=False)
    first_seen = models.DateTimeField('첫 방문 시각', auto_now_add=True)
    last_seen = models.DateTimeField('마지막 활동 시각', db_index=True)

    class Meta:
        verbose_name = '일별 방문자'
        verbose_name_plural = '일별 방문자'
        constraints = [models.UniqueConstraint(fields=['date', 'visitor_hash'], name='unique_visitor_per_day')]


class PageViewDay(models.Model):
    """날짜별 · 페이지 주소별 조회수 (인기 페이지 집계용)."""

    date = models.DateField('날짜', db_index=True)
    path = models.CharField('페이지 주소', max_length=200)
    views = models.PositiveIntegerField('조회수', default=0)

    class Meta:
        verbose_name = '일별 페이지 조회'
        verbose_name_plural = '일별 페이지 조회'
        constraints = [models.UniqueConstraint(fields=['date', 'path'], name='unique_path_per_day')]
