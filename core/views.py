from django.contrib.auth import get_user_model
from django.shortcuts import render

from boards.models import Post
from duels.models import Duel
from menus.models import Menu

User = get_user_model()


def home(request):
    """메인 페이지.

    보수/민주 최신글은 6단계(게시판)에서 만든 Post 모델과 연결했습니다.
    보수/민주는 GNB이면서 동시에 하위 메뉴가 없는(=리프) 메뉴라서 그 자체가
    게시판이라는 점을 이용해, slug로 바로 게시글을 조회합니다.

    가입자 진영 비율은 실제 회원가입 시 선택한 party(보수/진보) 값을 세어서
    퍼센트로 계산합니다. "실시간 통합 랭킹"은 전체 게시판을 통틀어 조회수가
    높은 글 TOP 5입니다 (2026-09-23, 참고 디자인 반영).

    9단계(포인트/일기토) 반영: "일기토 실시간 투표"와 "포인트 기반 명예의 전당"은
    이제 실제 데이터로 연결됩니다. "팩트체크 검증대", "즉석 여론조사"는 여전히
    설계 전이라 디자인만 넣고 "준비 중"으로 표시합니다.
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
        'page_title': '독존 - 정치 토론 커뮤니티',
        'meta_description': '독존은 보수와 민주 진영이 자유롭게 정치 토론을 나누는 정치 커뮤니티입니다.',
        'conservative_posts': conservative_board.posts.select_related('author')[:5] if conservative_board else [],
        'democrat_posts': democrat_board.posts.select_related('author')[:5] if democrat_board else [],
        'conservative_percent': conservative_percent,
        'democrat_percent': democrat_percent,
        'total_member_count': total_count,
        'top_posts': top_posts,
        'hall_of_fame': hall_of_fame,
        'current_duel': current_duel,
    }
    return render(request, 'core/home.html', context)
