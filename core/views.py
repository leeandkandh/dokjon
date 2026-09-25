from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count
import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.shortcuts import redirect, render
from django.utils import timezone

from accounts.models import RANK_TIERS
from boards.models import POINTS_COMMENT_WRITE, POINTS_LIKE_RECEIVED, POINTS_POST_DELETE, POINTS_POST_WRITE
from duels.models import DUEL_DURATION, POINTS_DUEL_LOSS, POINTS_DUEL_WIN
from boards.models import Post
from boards.views import HOT_POSTS_DAYS
from duels.models import Duel
from menus.models import Menu

from .context_processors import DEFAULT_DESCRIPTION, DEFAULT_TITLE
from .forms import InquiryForm
from .models import Inquiry

User = get_user_model()
logger = logging.getLogger(__name__)

# 약관/방침 시행일 (내용을 고치면 날짜도 같이 바꿔주세요)
POLICY_EFFECTIVE_DATE = '2026년 9월 24일'


def home(request):
    """메인 페이지.

    보수/민주 최신글은 6단계(게시판)에서 만든 Post 모델과 연결했습니다.
    보수/민주는 GNB이면서 동시에 하위 메뉴가 없는(=리프) 메뉴라서 그 자체가
    게시판이라는 점을 이용해, slug로 바로 게시글을 조회합니다.

    가입자 진영 비율은 실제 회원가입 시 선택한 party(보수/진보) 값을 세어서
    퍼센트로 계산합니다. "실시간 통합 랭킹"은 전체 게시판을 통틀어 조회수가
    높은 글 TOP 5입니다 (2026-09-23, 참고 디자인 반영).

    9단계(포인트/일기토) 반영: "일기토 실시간 투표"와 "포인트 기반 명예의 전당"은
    실제 데이터로 연결됩니다.

    2026-09-24: "준비 중"이던 팩트체크 검증대/즉석 여론조사 카드를 없애고,
    그 자리에 "화력 TOP 5"(전체 게시판 추천수 상위 5개 글)와
    "독존 등극"(최고 등급 독존에 오른 회원 전원)을 넣었습니다.
    보수/민주 최신글에는 글쓴이·성별/나이대·화력·댓글수를 함께 보여줍니다.
    """
    conservative_board = Menu.objects.filter(slug='conservative', is_active=True).first()
    democrat_board = Menu.objects.filter(slug='democrat', is_active=True).first()

    conservative_count = User.objects.filter(party='conservative').count()
    democrat_count = User.objects.filter(party='democrat').count()
    total_count = conservative_count + democrat_count

    if total_count > 0:
        conservative_percent = round(conservative_count / total_count * 100)
        democrat_percent = 100 - conservative_percent
    else:
        # 아직 가입자가 한 명도 없으면 반반으로 보여줍니다.
        conservative_percent = 50
        democrat_percent = 50

    top_posts = Post.objects.select_related('board', 'author').order_by('-view_count', '-created_at')[:5]

    # 게시글에 댓글수/화력(추천수)을 붙이는 공통 쿼리 (2026-09-24)
    counted_posts = (
        Post.objects.select_related('board', 'author')
        .annotate(comment_count=Count('comments', distinct=True), like_count=Count('likes', distinct=True))
    )

    # 2026-09-24: 전체 게시판 통틀어 화력(추천) 높은 글 TOP 5 (추천 0개인 글은 제외)
    # (게시판 화력 BEST와 똑같이 최근 7일 안에 쓴 글만 대상)
    fire_since = timezone.now() - timedelta(days=HOT_POSTS_DAYS)
    fire_top_posts = (
        counted_posts.filter(like_count__gt=0, created_at__gte=fire_since)
        .order_by('-like_count', '-created_at')[:5]
    )

    # 2026-09-24: 최고 등급 "독존"에 오른 회원 전원 (포인트 높은 순)
    top_rank_points = RANK_TIERS[-1][0]
    top_rank_members = User.objects.filter(points__gte=top_rank_points).order_by('-points', 'date_joined')

    # 9단계: 명예의 전당 - 포인트 상위 5명 (0점 회원은 아직 활동이 없는 것이므로 제외)
    hall_of_fame = User.objects.filter(points__gt=0).order_by('-points')[:5]

    # 9단계: 현재 진행중인 일기토(투표 마감이 가까운 순) 하나를 메인에 노출
    for duel in Duel.objects.filter(status=Duel.STATUS_ACTIVE):
        duel.resolve_if_needed()
    current_duel = (
        Duel.objects.select_related('challenger', 'opponent')
        .filter(status=Duel.STATUS_ACTIVE)
        .order_by('end_at')
        .first()
    )

    context = {
        # 2026-09-25 SEO: 검색 결과 제목/설명 (core/context_processors.py의 기본 문구와 동일)
        'page_title': DEFAULT_TITLE,
        'meta_description': DEFAULT_DESCRIPTION,
        'conservative_posts': counted_posts.filter(board=conservative_board).order_by('-created_at')[:5] if conservative_board else [],
        'democrat_posts': counted_posts.filter(board=democrat_board).order_by('-created_at')[:5] if democrat_board else [],
        'fire_top_posts': fire_top_posts,
        'hot_posts_days': HOT_POSTS_DAYS,
        'top_rank_members': top_rank_members,
        'top_rank_name': RANK_TIERS[-1][1],
        'top_rank_points': top_rank_points,
        'conservative_percent': conservative_percent,
        'democrat_percent': democrat_percent,
        'total_member_count': total_count,
        'top_posts': top_posts,
        'hall_of_fame': hall_of_fame,
        'current_duel': current_duel,
    }
    return render(request, 'core/home.html', context)


# ---------------- 안내 페이지 (2026-09-24) ----------------
# 포인트/등급/일기토 수치는 코드의 상수를 그대로 가져다 보여줘서,
# 나중에 수치를 바꿔도 안내 페이지가 자동으로 맞춰집니다.

def _policy_context(title, description):
    return {
        'page_title': f'{title} | 독존',
        'meta_description': description,
        'effective_date': POLICY_EFFECTIVE_DATE,
        'contact_email': settings.CONTACT_EMAIL,
    }


def terms(request):
    context = _policy_context('이용약관', '독존 서비스 이용약관입니다.')
    return render(request, 'core/terms.html', context)


def privacy(request):
    context = _policy_context('개인정보처리방침', '독존 개인정보처리방침입니다.')
    return render(request, 'core/privacy.html', context)


def _points_context():
    return {
        'rank_tiers': RANK_TIERS,
        'points_post_write': POINTS_POST_WRITE,
        'points_post_delete': POINTS_POST_DELETE,
        'points_comment_write': POINTS_COMMENT_WRITE,
        'points_like_received': POINTS_LIKE_RECEIVED,
        'points_duel_win': POINTS_DUEL_WIN,
        'points_duel_loss': POINTS_DUEL_LOSS,
        'duel_days': DUEL_DURATION.days,
        'hot_posts_days': HOT_POSTS_DAYS,
    }


def guidelines(request):
    context = _policy_context('커뮤니티 가이드라인', '보수·진보 정치 토론 커뮤니티 독존의 이용 규칙 - 보수 아레나·민주 아레나 권한, 금지 행위, 포인트와 등급 안내.')
    context.update(_points_context())
    return render(request, 'core/guidelines.html', context)


def duel_rules(request):
    context = _policy_context('1:1 일기토 규칙', '보수 vs 진보 1:1 정치 끝장토론 "일기토"의 신청, 토론, 투표, 판정 규칙과 보상 안내.')
    context.update(_points_context())
    return render(request, 'core/duel_rules.html', context)


def contact(request):
    """광고/제휴 문의 · 고객센터 (2026-09-24).

    ?type=ad 로 들어오면 "광고/제휴 문의"가 미리 선택됩니다.
    접수 내용은 DB에 저장하고 CONTACT_EMAIL(dlrjsgmli@naver.com)로 메일을 보냅니다.
    """
    initial_type = request.GET.get('type')
    if initial_type not in dict(Inquiry.TYPE_CHOICES):
        initial_type = Inquiry.TYPE_SUPPORT

    if request.method == 'POST':
        form = InquiryForm(request.POST)
        if form.is_valid():
            if form.cleaned_data.get('website'):
                # 숨김 칸이 채워져 있으면 봇으로 보고 조용히 성공 화면만 보여줍니다.
                return redirect('core:contact_done')

            inquiry = form.save(commit=False)
            if request.user.is_authenticated:
                inquiry.user = request.user
            inquiry.save()

            member_line = (
                f'회원: {request.user.nickname} ({request.user.username})' if request.user.is_authenticated else '회원: 비회원'
            )
            body = (
                f'[독존] {inquiry.get_inquiry_type_display()}가 접수되었습니다.\n\n'
                f'유형: {inquiry.get_inquiry_type_display()}\n'
                f'이름: {inquiry.name}\n'
                f'회신 이메일: {inquiry.email}\n'
                f'{member_line}\n'
                f'접수 시각: {timezone.localtime(inquiry.created_at):%Y-%m-%d %H:%M}\n\n'
                f'제목: {inquiry.subject}\n\n'
                f'{inquiry.message}\n'
            )
            try:
                EmailMessage(
                    subject=f'[독존 {inquiry.get_inquiry_type_display()}] {inquiry.subject}',
                    body=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[settings.CONTACT_EMAIL],
                    reply_to=[inquiry.email],  # 메일에서 "답장"을 누르면 문의한 사람에게 바로 회신됩니다
                ).send()
                inquiry.email_sent = True
                inquiry.save(update_fields=['email_sent'])
            except Exception:  # 메일 서버 문제가 있어도 문의 자체는 DB에 저장돼 있으므로 사용자에게는 정상 접수로 안내
                logger.exception('문의 메일 발송 실패 (inquiry id=%s)', inquiry.pk)

            return redirect('core:contact_done')
    else:
        initial = {'inquiry_type': initial_type}
        if request.user.is_authenticated:
            initial.update({'name': request.user.nickname, 'email': request.user.email})
        form = InquiryForm(initial=initial)

    context = _policy_context('문의하기', '독존 고객센터 및 광고/제휴 문의')
    context['form'] = form
    return render(request, 'core/contact.html', context)


def contact_done(request):
    context = _policy_context('문의 접수 완료', '독존 문의 접수 완료')
    return render(request, 'core/contact_done.html', context)


def ranks(request):
    """회원 등급 안내 (2026-09-24). 상단 "회원등급" 링크로 들어옵니다.

    전체 10단계 등급표(기준 포인트, 등급별 회원 수)와, 로그인한 회원이면
    내 현재 등급과 다음 등급까지의 진행률을 보여줍니다.
    등급표는 accounts/models.py의 RANK_TIERS를 그대로 읽으므로 기준을 바꾸면 자동 반영됩니다.
    """
    members = User.objects.filter(is_active=True)
    user = request.user if request.user.is_authenticated else None

    tiers = []
    for index, (threshold, name) in enumerate(RANK_TIERS):
        next_threshold = RANK_TIERS[index + 1][0] if index + 1 < len(RANK_TIERS) else None
        in_tier = members.filter(points__gte=threshold)
        if next_threshold is not None:
            in_tier = in_tier.filter(points__lt=next_threshold)
        tiers.append({
            'level': index + 1,
            'name': name,
            'threshold': threshold,
            'next_threshold': next_threshold,
            'member_count': in_tier.count(),
            'is_current': user is not None and user.rank_name == name,
            'is_reached': user is not None and user.points >= threshold,
            'is_top': next_threshold is None,
        })

    progress = None
    if user is not None:
        nxt = user.next_rank
        if nxt:
            next_name, next_threshold, remaining = nxt
            current_threshold = max(t for t, _ in RANK_TIERS if t <= user.points)
            span = next_threshold - current_threshold
            progress = {
                'next_name': next_name,
                'remaining': remaining,
                'percent': round((user.points - current_threshold) / span * 100) if span else 100,
            }

    context = _policy_context('회원 등급', '독존 정치 커뮤니티 회원 등급표 - 초심자부터 독존까지 10단계 등급과 포인트 쌓는 법, 등급별 회원 수.')
    context.update(_points_context())
    context.update({
        'tiers': list(reversed(tiers)),  # 화면에는 최고 등급(독존)이 맨 위
        'tier_count': len(tiers),
        'progress': progress,
        'total_members': members.count(),
    })
    return render(request, 'core/ranks.html', context)


def robots_txt(request):
    """robots.txt (2026-09-25 SEO). 검색엔진에게 수집해도 되는 곳/안 되는 곳과 sitemap 위치를 알려줍니다."""
    from django.http import HttpResponse

    from .context_processors import site_base_url

    lines = [
        'User-agent: *',
        'Allow: /',
        # 로그인·회원·관리자·글쓰기/수정/삭제·API 주소는 검색에 나올 필요 없음
        'Disallow: /admin/',
        'Disallow: /accounts/',
        'Disallow: /login/',
        'Disallow: /logout/',
        'Disallow: /contact/done/',
        'Disallow: /board/*/write/',
        'Disallow: /board/*/upload-image/',
        'Disallow: /board/*/edit/',
        'Disallow: /board/*/delete/',
        'Disallow: /board/*/like/',
        'Disallow: /board/*/comments/',
        'Disallow: /ilgito/challenge/',
        'Disallow: /ilgito/*/vote/',
        'Disallow: /ilgito/*/comments/',
        '',
        f'Sitemap: {site_base_url(request)}/sitemap.xml',
        '',
    ]
    return HttpResponse('\n'.join(lines), content_type='text/plain; charset=utf-8')
