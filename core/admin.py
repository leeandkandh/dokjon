from django.contrib import admin

from .models import Inquiry


@admin.register(Inquiry)
class InquiryAdmin(admin.ModelAdmin):
    """광고/제휴 · 고객센터 문의 목록. 답변은 회신 이메일로 직접 보내고 '답변 완료'를 체크하세요."""

    list_display = ('subject', 'inquiry_type', 'name', 'email', 'user', 'email_sent', 'is_answered', 'created_at')
    list_filter = ('inquiry_type', 'is_answered', 'email_sent')
    list_editable = ('is_answered',)
    search_fields = ('subject', 'message', 'name', 'email')
    readonly_fields = ('inquiry_type', 'name', 'email', 'subject', 'message', 'user', 'email_sent', 'created_at')
