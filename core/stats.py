"""관리자 통계 대시보드 데이터 (2026-09-25). 화면은 templates/core/stats.html, 주소는 /stats/ (관리자만)."""
import math
import re
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from accounts.models import PARTY_CHOICES
from boards.models import Comment, Post, PostLike
from duels.models import Duel
from menus.models import Menu

from .models import PageViewDay, VisitorDay

User = get_user_model()
RETENTION_DAYS = 400  # 약 13개월 지난 방문 기록은 자동 삭제 (개인정보처리방침과 동일)
REALTIME_MINUTES = 5
CHART_DAYS = 30


def _nice_max(value):
    """y축 최대값을 보기 좋은 숫자(1, 2, 5, 10, 20, 50 …)로 올림."""
    if value <= 0:
        return 5
    exp = 10 ** math.floor(math.log10(value))
    for step in (1, 2, 5, 10):
        if value <= step * exp:
            return step * exp
    return 10 * exp


def _column_chart(days, values, extra, height=200, width=720):
    """일별 세로 막대 SVG 좌표 계산. extra = 툴팁에 같이 보여줄 페이지뷰."""
    left, right, top, bottom = 36, 8, 12, 24
    plot_w, plot_h = width - left - right, height - top - bottom
    y_max = _nice_max(max(values) if values else 0)
    slot = plot_w / len(days)
    bar_w = min(18, slot - 4)
    bars = []
    for i, (day, value) in enumerate(zip(days, values)):
        h = 0 if value == 0 else max(2, value / y_max * plot_h)
        x = left + i * slot + (slot - bar_w) / 2
        y = top + plot_h - h
        r = min(4, h / 2, bar_w / 2)
        # 위쪽 모서리만 둥글게(데이터 끝), 바닥(기준선)은 각지게
        path = (
            f'M{x:.1f},{top + plot_h:.1f} V{y + r:.1f} Q{x:.1f},{y:.1f} {x + r:.1f},{y:.1f} '
            f'H{x + bar_w - r:.1f} Q{x + bar_w:.1f},{y:.1f} {x + bar_w:.1f},{y + r:.1f} V{top + plot_h:.1f} Z'
        ) if h else ''
        bars.append({
            'path': path, 'label': day.strftime('%m/%d'), 'weekday': '월화수목금토일'[day.weekday()],
            'value': value, 'extra': extra[i],
            'hit_x': left + i * slot, 'hit_w': slot,
            'is_today': i == len(days) - 1,
        })
    ticks = [{'y': top + plot_h - plot_h * k / 4, 'value': int(y_max * k / 4)} for k in range(5)]
    x_labels = [{'x': left + i * slot + slot / 2, 'text': days[i].strftime('%m/%d')}
                for i in range(len(days)) if (len(days) - 1 - i) % 7 == 0]
    return {
        'width': width, 'height': height, 'left': left, 'right': width - right, 'top': top,
        'baseline': top + plot_h, 'plot_h': plot_h, 'bars': bars, 'ticks': ticks, 'x_labels': x_labels,
        'label_y': height - 6,
    }


_POST_RE = re.compile(r'^/board/([\w-]+)/(\d+)/$')
_BOARD_RE = re.compile(r'^/board/([\w-]+)/$')
_DUEL_RE = re.compile(r'^/ilgito/(\d+)/$')
_FIXED_PAGES = {
    '/': '메인', '/ilgito/': '일기토 목록', '/ranks/': '회원 등급', '/guidelines/': '커뮤니티 가이드라인',
    '/ilgito-rules/': '1:1 일기토 규칙', '/terms/': '이용약관', '/privacy/': '개인정보처리방침',
    '/contact/': '문의하기', '/login/': '로그인', '/accounts/signup/': '회원가입', '/accounts/mypage/': '마이페이지',
}


def _page_titles(paths):
    """인기 페이지 주소 → 사람이 읽을 수 있는 이름 (글 제목, 게시판 이름 등)."""
    post_ids = [int(m.group(2)) for p in paths if (m := _POST_RE.match(p))]
    duel_ids = [int(m.group(1)) for p in paths if (m := _DUEL_RE.match(p))]
    posts = {p.pk: p.title for p in Post.objects.filter(pk__in=post_ids)}
    duels = {d.pk: d.topic for d in Duel.objects.filter(pk__in=duel_ids)}
    boards = dict(Menu.objects.values_list('slug', 'name'))
    titles = {}
    for p in paths:
        if p in _FIXED_PAGES:
            titles[p] = _FIXED_PAGES[p]
        elif m := _POST_RE.match(p):
            titles[p] = f'[{boards.get(m.group(1), m.group(1))}] {posts.get(int(m.group(2)), "(삭제된 글)")}'
        elif m := _BOARD_RE.match(p):
            titles[p] = f'{boards.get(m.group(1), m.group(1))} 목록'
        elif m := _DUEL_RE.match(p):
            titles[p] = f'[일기토] {duels.get(int(m.group(1)), "(삭제됨)")}'
        else:
            titles[p] = p
    return titles


def build_stats():
    now = timezone.now()
    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    chart_start = today - timedelta(days=CHART_DAYS - 1)

    # 오래된 방문 기록 정리 (가볍게 매번 실행)
    cutoff = today - timedelta(days=RETENTION_DAYS)
    VisitorDay.objects.filter(date__lt=cutoff).delete()
    PageViewDay.objects.filter(date__lt=cutoff).delete()

    def day_totals(day):
        agg = VisitorDay.objects.filter(date=day).aggregate(v=Count('id'), pv=Sum('page_views'))
        return agg['v'] or 0, agg['pv'] or 0

    today_v, today_pv = day_totals(today)
    yday_v, yday_pv = day_totals(today - timedelta(days=1))
    week_qs = VisitorDay.objects.filter(date__gte=week_start)
    week_agg = week_qs.aggregate(v=Count('id'), pv=Sum('page_views'))
    today_qs = VisitorDay.objects.filter(date=today)

    realtime = VisitorDay.objects.filter(last_seen__gte=now - timedelta(minutes=REALTIME_MINUTES)).count()
    today_members = today_qs.filter(user__isnull=False).count()
    today_mobile = today_qs.filter(is_mobile=True).count()

    # 30일 일별 방문자 (+페이지뷰는 툴팁/표에)
    by_day = {
        row['date']: row for row in
        VisitorDay.objects.filter(date__gte=chart_start).values('date').annotate(v=Count('id'), pv=Sum('page_views'))
    }
    days = [chart_start + timedelta(days=i) for i in range(CHART_DAYS)]
    visitors = [by_day.get(d, {}).get('v', 0) for d in days]
    pageviews = [by_day.get(d, {}).get('pv', 0) or 0 for d in days]
    chart = _column_chart(days, visitors, pageviews)

    # 최근 14일 활동 (가입/글/댓글/일기토)
    def per_day(qs, field):
        return {r['d']: r['n'] for r in qs.filter(**{f'{field}__date__gte': today - timedelta(days=13)})
                .values(d=TruncDate(field, tzinfo=timezone.get_current_timezone()))
                .annotate(n=Count('id'))}
    signups = per_day(User.objects.filter(withdrawn_at__isnull=True), 'date_joined')
    posts_d = per_day(Post.objects.all(), 'created_at')
    comments_d = per_day(Comment.objects.all(), 'created_at')
    duels_d = per_day(Duel.objects.all(), 'created_at')
    activity = []
    for i in range(14):
        d = today - timedelta(days=i)
        activity.append({
            'date': d, 'visitors': by_day.get(d, {}).get('v', 0), 'pageviews': by_day.get(d, {}).get('pv', 0) or 0,
            'signups': signups.get(d, 0), 'posts': posts_d.get(d, 0), 'comments': comments_d.get(d, 0), 'duels': duels_d.get(d, 0),
        })

    # 유입 경로 (최근 7일)
    sources = list(week_qs.values('source').annotate(n=Count('id')).order_by('-n'))
    src_max = max([s['n'] for s in sources] or [1])
    for s in sources:
        s['pct'] = round(s['n'] / src_max * 100)
        s['source'] = s['source'] or '알 수 없음'

    # 인기 페이지 (최근 7일)
    top_pages = list(
        PageViewDay.objects.filter(date__gte=week_start).values('path').annotate(n=Sum('views')).order_by('-n')[:10]
    )
    titles = _page_titles([p['path'] for p in top_pages])
    page_max = max([p['n'] for p in top_pages] or [1])
    for p in top_pages:
        p['title'] = titles[p['path']]
        p['pct'] = round(p['n'] / page_max * 100)

    # 진영 비교
    members = User.objects.filter(is_active=True, withdrawn_at__isnull=True)
    party_rows = []
    metrics = [
        ('회원 수', lambda party: members.filter(party=party).count()),
        ('오늘 방문한 회원', lambda party: today_qs.filter(user__party=party).count()),
        ('최근 7일 새 글', lambda party: Post.objects.filter(created_at__date__gte=week_start, author__party=party).count()),
        ('최근 7일 댓글', lambda party: Comment.objects.filter(created_at__date__gte=week_start, author__party=party).count()),
        ('최근 7일 받은 화력', lambda party: PostLike.objects.filter(created_at__date__gte=week_start, post__author__party=party).count()),
        ('일기토 승리(누적)', lambda party: members.filter(party=party).aggregate(n=Sum('duel_wins'))['n'] or 0),
    ]
    for label, fn in metrics:
        c, d = fn('conservative'), fn('democrat')
        total = c + d
        party_rows.append({
            'label': label, 'conservative': c, 'democrat': d,
            'c_pct': round(c / total * 100) if total else 50, 'd_pct': (100 - round(c / total * 100)) if total else 50,
            'empty': total == 0,
        })

    # 회원 구성: 나이대 × 진영·성별
    age_table = {}
    for m in members.exclude(birth_date__isnull=True).only('birth_date', 'party', 'gender'):
        age = m.age_group or '기타'
        row = age_table.setdefault(age, {'age': age, 'c_m': 0, 'c_f': 0, 'd_m': 0, 'd_f': 0, 'total': 0})
        key = {'conservative': 'c', 'democrat': 'd'}.get(m.party)
        if key and m.gender in ('male', 'female'):
            row[f'{key}_{"m" if m.gender == "male" else "f"}'] += 1
        row['total'] += 1
    age_rows = sorted(age_table.values(), key=lambda r: (r['age'] == '기타', r['age']))

    return {
        'generated_at': timezone.localtime(now),
        'realtime': realtime, 'realtime_minutes': REALTIME_MINUTES,
        'today_visitors': today_v, 'today_pageviews': today_pv,
        'yesterday_visitors': yday_v, 'yesterday_pageviews': yday_pv,
        'visitor_delta': today_v - yday_v,
        'week_visitors': week_agg['v'] or 0, 'week_pageviews': week_agg['pv'] or 0,
        'today_members': today_members, 'today_guests': today_v - today_members,
        'today_mobile_pct': round(today_mobile / today_v * 100) if today_v else 0,
        'total_members': members.count(),
        'today_signups': signups.get(today, 0),
        'chart': chart, 'chart_days': CHART_DAYS,
        'activity': activity,
        'sources': sources, 'top_pages': top_pages,
        'party_rows': party_rows, 'party_labels': dict(PARTY_CHOICES),
        'age_rows': age_rows,
    }
