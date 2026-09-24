from django.contrib import admin

from .models import Duel, DuelComment, DuelVote


class DuelVoteInline(admin.TabularInline):
    model = DuelVote
    extra = 0
    readonly_fields = ('voter', 'side', 'voted_at')
    can_delete = False


class DuelCommentInline(admin.TabularInline):
    model = DuelComment
    extra = 0
    readonly_fields = ('author', 'created_at')


@admin.register(Duel)
class DuelAdmin(admin.ModelAdmin):
    """관리자페이지에서 일기토 대진을 등록/진행/종료 상태로 관리합니다.
    보통 status를 'scheduled' -> 'active'로 바꿔 투표를 열고, end_at이 지나면
    화면 조회 시 자동으로 승자가 판정되어 'finished'로 바뀝니다.
    """
    list_display = ('topic', 'challenger', 'opponent', 'status', 'start_at', 'end_at', 'winner')
    list_filter = ('status',)
    search_fields = ('topic', 'challenger__nickname', 'opponent__nickname')
    autocomplete_fields = ('challenger', 'opponent', 'winner')
    date_hierarchy = 'start_at'
    raw_id_fields = ('source_post',)
    inlines = [DuelVoteInline, DuelCommentInline]
