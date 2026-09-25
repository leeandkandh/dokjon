"""접속 통계 수집 미들웨어 (2026-09-25).

사람이 페이지(HTML)를 볼 때마다 VisitorDay / PageViewDay에 기록합니다.
- 검색엔진 로봇, 관리자 페이지, 정적 파일, 글쓰기/수정 같은 내부 주소, 오류 응답은 세지 않습니다.
- IP 원문은 저장하지 않습니다 (core/models.py 설명 참고).
- 통계 기록이 실패해도 사이트 화면에는 절대 영향을 주지 않도록 모든 오류를 삼킵니다.
"""
import hashlib
import logging
import re
from urllib.parse import urlsplit

from django.conf import settings
from django.db import IntegrityError, transaction
from django.db.models import F
from django.utils import timezone

logger = logging.getLogger(__name__)

BOT_RE = re.compile(
    r'bot|crawl|spider|slurp|yeti|daum|bingpreview|facebookexternalhit|kakaotalk-scrap|'
    r'headless|python-requests|curl|wget|httpclient|monitor|preview|lighthouse|pagespeed',
    re.IGNORECASE,
)
MOBILE_RE = re.compile(r'Mobi|Android|iPhone|iPad', re.IGNORECASE)
SKIP_PREFIXES = ('/static/', '/media/', '/admin/', '/stats/', '/robots.txt', '/sitemap.xml', '/favicon')
SKIP_PARTS = ('/write/', '/edit/', '/delete/', '/upload-image/', '/like/', '/comments/', '/vote/', '/check-')

# 유입 경로: 이전 페이지 주소(Referer)의 도메인으로 분류
SOURCES = [
    ('google.', '구글'),
    ('naver.', '네이버'),
    ('daum.', '다음'),
    ('kakao', '카카오톡'),
    ('youtube.', '유튜브'),
    ('facebook.', '페이스북'),
    ('instagram.', '인스타그램'),
    ('t.co', 'X(트위터)'),
    ('twitter.', 'X(트위터)'),
    ('x.com', 'X(트위터)'),
    ('bing.', '빙'),
]


def classify_source(referer, own_host):
    if not referer:
        return '직접 방문'
    host = (urlsplit(referer).hostname or '').lower()
    if not host or host == own_host.split(':')[0].lower():
        return '사이트 내부'
    for key, label in SOURCES:
        if key in host:
            return label
    return '기타 사이트'


def client_ip(request):
    # nginx의 proxy_params가 넣어주는 X-Real-IP(실제 접속자 IP)를 우선 사용
    return request.META.get('HTTP_X_REAL_IP') or request.META.get('REMOTE_ADDR', '')


class VisitTrackingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            if self._should_track(request, response):
                self._track(request)
        except Exception:  # 통계 때문에 사이트가 멈추면 안 됨
            logger.exception('접속 통계 기록 실패')
        return response

    @staticmethod
    def _should_track(request, response):
        if request.method != 'GET' or response.status_code != 200:
            return False
        if 'text/html' not in response.get('Content-Type', ''):
            return False
        path = request.path
        if path.startswith(SKIP_PREFIXES) or any(part in path for part in SKIP_PARTS):
            return False
        ua = request.META.get('HTTP_USER_AGENT', '')
        if not ua or BOT_RE.search(ua):
            return False
        user = getattr(request, 'user', None)
        if user is not None and user.is_authenticated and user.is_staff:
            return False  # 운영자 본인의 방문은 통계에서 제외
        return True

    @staticmethod
    def _track(request):
        from .models import PageViewDay, VisitorDay  # 앱 로딩 순서 문제 방지

        now = timezone.now()
        today = timezone.localdate()
        ua = request.META.get('HTTP_USER_AGENT', '')
        raw = f'{today.isoformat()}|{settings.SECRET_KEY}|{client_ip(request)}|{ua}'
        visitor_hash = hashlib.sha256(raw.encode('utf-8')).hexdigest()
        user = request.user if request.user.is_authenticated else None

        updated = VisitorDay.objects.filter(date=today, visitor_hash=visitor_hash).update(
            page_views=F('page_views') + 1, last_seen=now,
            **({'user': user} if user else {}),
        )
        if not updated:
            try:
                with transaction.atomic():
                    VisitorDay.objects.create(
                        date=today, visitor_hash=visitor_hash, user=user, page_views=1, last_seen=now,
                        source=classify_source(request.META.get('HTTP_REFERER', ''), request.get_host()),
                        is_mobile=bool(MOBILE_RE.search(ua)),
                    )
            except IntegrityError:  # 같은 순간에 두 요청이 겹친 경우
                VisitorDay.objects.filter(date=today, visitor_hash=visitor_hash).update(
                    page_views=F('page_views') + 1, last_seen=now,
                )

        path = request.path[:200]
        if not PageViewDay.objects.filter(date=today, path=path).update(views=F('views') + 1):
            try:
                with transaction.atomic():
                    PageViewDay.objects.create(date=today, path=path, views=1)
            except IntegrityError:
                PageViewDay.objects.filter(date=today, path=path).update(views=F('views') + 1)
