import re

from django.conf import settings
from django.db import models

from menus.models import Menu

# 본문(HTML) 안에서 첫 번째 <img src="..."> 를 찾기 위한 정규식.
# 8단계 요청: 목록 화면에서 제목 앞에 썸네일을 보여주기 위해 사용합니다.
_FIRST_IMG_SRC_RE = re.compile(r'<img[^>]+src=["\']([^"\']+)["\']', re.IGNORECASE)

# 9단계(포인트) 요청으로 목업 화면(댓글수/추천수)을 실제로 동작하게 만들면서
# 함께 도입한 활동 포인트. 글/댓글 삭제 시에는 따로 차감하지 않습니다(일반적인
# 커뮤니티 정책과 동일 - 어뷰징 방지는 11단계 신고/보안에서 별도로 다룰 예정).
# 2026-09-24 변경: 모든 게시판 글쓰기 +2점, 글 삭제 시 -3점 (0점 밑으로는 안 내려감)
POINTS_POST_WRITE = 2
POINTS_POST_DELETE = 3
POINTS_COMMENT_WRITE = 2
POINTS_LIKE_RECEIVED = 1


class Post(models.Model):
    """게시글.

    어떤 게시판에 속하는지는 menus 앱의 Menu를 그대로 재사용합니다.
    "하위 메뉴가 없는(=리프) 메뉴"가 곧 실제 게시판입니다.
    예) 보수, 민주, 일기토, 자유(일반>자유), 주식(금융>주식)
    이렇게 하면 나중에 관리자가 /admin/의 "메뉴 관리"에서 메뉴를 추가하는 것만으로
    코드 수정 없이 새 게시판이 생깁니다. (일반/금융처럼 하위 메뉴가 있는 GNB
    자체는 게시판이 아니라 "묶음" 역할만 합니다 - views.py에서 걸러냅니다)
    """

    board = models.ForeignKey(
        Menu,
        verbose_name='게시판',
        on_delete=models.CASCADE,
        related_name='posts',
        limit_choices_to={'children__isnull': True},
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='작성자',
        on_delete=models.CASCADE,
        related_name='posts',
    )
    title = models.CharField('제목', max_length=200)

    # 8단계부터 글쓰기 화면에 에디터(Quill)가 붙으면서, 이 필드에는 순수 텍스트가 아니라
    # 정제된(bleach로 위험 태그를 걸러낸) HTML이 저장됩니다. 화면에 뿌릴 때는
    # linebreaks가 아니라 |safe로 그대로 렌더링합니다 (post_detail.html 참고).
    content = models.TextField('내용')

    # 같은 사람이 새로고침할 때마다 계속 올라가는 문제는
    # 11단계(신고/보안) 즈음에 세션/쿠키로 중복 방지를 붙일 예정입니다.
    view_count = models.PositiveIntegerField('조회수', default=0)

    created_at = models.DateTimeField('작성일', auto_now_add=True)
    updated_at = models.DateTimeField('수정일', auto_now=True)

    class Meta:
        verbose_name = '게시글'
        verbose_name_plural = '게시글 관리'
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    @property
    def thumbnail_url(self):
        """목록 화면에서 제목 앞에 보여줄 썸네일 이미지 주소.

        1순위: 아래에 첨부한 이미지(PostImage)가 있으면 그 중 첫 번째.
        2순위: 첨부는 없지만 본문 에디터 안에 드래그로 넣은 이미지가 있으면 그 중 첫 번째.
        3순위: 본문에 유튜브 링크가 있으면 첫 번째 영상의 썸네일.
        둘 다 없으면 None (템플릿에서 썸네일 없이 렌더링).
        """
        attached = list(self.images.all())  # prefetch_related('images') 캐시를 그대로 사용
        if attached:
            return attached[0].image.url
        match = _FIRST_IMG_SRC_RE.search(self.content)
        if match:
            return match.group(1)
        # 3순위(2026-09-25): 이미지는 없고 유튜브 링크가 있으면 그 영상의 썸네일
        from .youtube import youtube_ids  # 순환 import 방지
        ids = youtube_ids(self.content)
        return f'https://i.ytimg.com/vi/{ids[0]}/hqdefault.jpg' if ids else None


# 7단계(파일업로드) 규칙. "첨부파일 용량" 정식 기준은 아직 확정 전(요구사항 19장)이라
# 우선 일반적인 커뮤니티 사이트 기준으로 잡아둔 값입니다. 나중에 바뀌면 이 숫자만 고치면 됩니다.
MAX_UPLOAD_IMAGE_SIZE = 5 * 1024 * 1024  # 장당 5MB
MAX_UPLOAD_IMAGE_COUNT = 5  # 글 하나당 최대 5장
ALLOWED_IMAGE_CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']


def post_image_upload_to(instance, filename):
    # media/posts/게시판slug/연/월/원본파일명 형태로 정리해서 저장
    return f'posts/{instance.post.board.slug}/%Y/%m/{filename}'


class PostImage(models.Model):
    """게시글에 첨부된 이미지. 글 하나에 여러 장(최대 MAX_UPLOAD_IMAGE_COUNT) 첨부 가능합니다."""

    post = models.ForeignKey(Post, verbose_name='게시글', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField('이미지', upload_to=post_image_upload_to)
    created_at = models.DateTimeField('업로드일', auto_now_add=True)

    class Meta:
        verbose_name = '첨부 이미지'
        verbose_name_plural = '첨부 이미지 관리'
        ordering = ['id']

    def __str__(self):
        return f'{self.post.title} - {self.image.name}'


class Comment(models.Model):
    """게시글 댓글. (9단계: 목업의 '댓글수' 뱃지를 실제 데이터로 연결하기 위해 추가)"""

    post = models.ForeignKey(Post, verbose_name='게시글', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='작성자',
        on_delete=models.CASCADE,
        related_name='comments',
    )
    content = models.TextField('내용', max_length=1000)
    created_at = models.DateTimeField('작성일', auto_now_add=True)

    class Meta:
        verbose_name = '댓글'
        verbose_name_plural = '댓글 관리'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.post.title} - {self.author.nickname}: {self.content[:20]}'


class PostLike(models.Model):
    """게시글 추천(화력). 한 사람이 같은 글에 한 번만 추천할 수 있습니다.
    (9단계: 목업의 '추천/화력수' 뱃지를 실제 데이터로 연결하기 위해 추가)
    """

    post = models.ForeignKey(Post, verbose_name='게시글', on_delete=models.CASCADE, related_name='likes')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='추천한 회원',
        on_delete=models.CASCADE,
        related_name='post_likes',
    )
    created_at = models.DateTimeField('추천일', auto_now_add=True)

    class Meta:
        verbose_name = '추천(화력)'
        verbose_name_plural = '추천(화력) 관리'
        constraints = [
            models.UniqueConstraint(fields=['post', 'user'], name='unique_post_like_per_user'),
        ]

    def __str__(self):
        return f'{self.post.title} - {self.user.nickname} 추천'
