from django.contrib import admin

from .models import Comment, Post, PostImage, PostLike


class PostImageInline(admin.TabularInline):
    model = PostImage
    extra = 0


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """관리자페이지에서 게시글을 조회/검색/삭제할 수 있도록 등록.
    11단계(신고/보안)에서 신고 누적 시 처리 기능을 더 붙일 예정입니다.
    """
    list_display = ('title', 'board', 'author', 'view_count', 'created_at')
    list_filter = ('board',)
    search_fields = ('title', 'content', 'author__username', 'author__nickname')
    date_hierarchy = 'created_at'
    inlines = [PostImageInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    """9단계: 댓글 관리자페이지. 문제 댓글을 검색해서 바로 삭제할 수 있습니다."""
    list_display = ('post', 'author', 'content', 'created_at')
    list_filter = ('post__board',)
    search_fields = ('content', 'author__username', 'author__nickname', 'post__title')
    date_hierarchy = 'created_at'


@admin.register(PostLike)
class PostLikeAdmin(admin.ModelAdmin):
    """9단계: 추천(화력) 관리자페이지. 어뷰징 의심 시 조회/삭제용입니다."""
    list_display = ('post', 'user', 'created_at')
    list_filter = ('post__board',)
    search_fields = ('post__title', 'user__username', 'user__nickname')
    date_hierarchy = 'created_at'
