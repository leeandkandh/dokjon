from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class DokjonUserAdmin(UserAdmin):
    """관리자페이지(admin)에서 회원을 조회/관리할 수 있도록 등록.

    13단계(관리자페이지)에서 정지/등급 관리 기능을 더 붙일 예정입니다.
    """
    list_display = (
        'username', 'nickname', 'email', 'party', 'rank_name', 'points',
        'duel_wins', 'duel_losses', 'is_suspended', 'is_staff', 'date_joined',
    )
    list_filter = ('party', 'is_suspended', 'is_staff', 'is_active')
    search_fields = ('username', 'nickname', 'email')
    fieldsets = UserAdmin.fieldsets + (
        ('독존 추가 정보', {
            'fields': ('nickname', 'birth_date', 'party', 'is_suspended', 'points', 'duel_wins', 'duel_losses'),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('독존 추가 정보', {'fields': ('nickname', 'birth_date', 'party')}),
    )
