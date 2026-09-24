from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from accounts.models import PARTY_CHOICES
from boards.models import Post

from .models import DUEL_DURATION, Duel, DuelComment, DuelVote

PARTY_VALUES = {value for value, _label in PARTY_CHOICES}
DUEL_COMMENT_MAX_LENGTH = 2000


def can_challenge_post(user, post):
    """user가 post(보수/민주 아레나 글)에 1:1 일기토를 신청할 수 있는지. (2026-09-24)

    조건: 로그인 + 진영 게시판의 글 + 신청자와 글쓴이 모두 진영이 있고 서로 다른 진영 + 본인 글 아님.
    예) 민주 회원은 보수 아레나의 보수 회원 글에, 보수 회원은 민주 아레나의 민주 회원 글에 신청 가능.
    """
    if not user.is_authenticated or user.pk == post.author_id:
        return False
    if post.board.slug not in PARTY_VALUES:
        return False
    if user.party not in PARTY_VALUES or user.party == post.board.slug:
        return False
    author_party = post.author.party
    return author_party in PARTY_VALUES and author_party != user.party


def active_duel_for_post(post):
    """이 글에 걸린 진행중 일기토 (없으면 None). 마감 지난 건 여기서 판정까지 합니다."""
    for duel in post.duels.filter(status=Duel.STATUS_ACTIVE):
        duel.resolve_if_needed()
    return post.duels.filter(status=Duel.STATUS_ACTIVE).first()


def _resolve_active_duels():
    """마감 시각이 지난 진행중 듀얼들을 판정합니다. 목록/상세를 보여주기 직전에 호출합니다."""
    for duel in Duel.objects.filter(status=Duel.STATUS_ACTIVE):
        duel.resolve_if_needed()


def duel_list(request):
    _resolve_active_duels()

    duel_qs = Duel.objects.select_related('challenger', 'opponent', 'winner')
    current_duel = duel_qs.filter(status=Duel.STATUS_ACTIVE).order_by('end_at').first()

    paginator = Paginator(duel_qs.exclude(pk=current_duel.pk) if current_duel else duel_qs, 10)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    context = {
        'current_duel': current_duel,
        'page_obj': page_obj,
        'page_title': '일기토 (1:1 끝장토론) - 독존',
        'meta_description': '독존 보수 아레나 vs 민주 아레나, 1:1 끝장토론 대진표와 투표 결과입니다.',
    }
    return render(request, 'duels/duel_list.html', context)


def duel_detail(request, pk):
    duel = get_object_or_404(Duel.objects.select_related('challenger', 'opponent', 'winner'), pk=pk)
    duel.resolve_if_needed()

    user_vote = None
    if request.user.is_authenticated:
        user_vote = duel.votes.filter(voter=request.user).first()

    is_participant = request.user.is_authenticated and request.user.id in (duel.challenger_id, duel.opponent_id)
    source_post = duel.source_post
    if source_post is not None:
        source_post = Post.objects.select_related('author', 'board').prefetch_related('images').get(pk=source_post.pk)

    context = {
        'duel': duel,
        'user_vote': user_vote,
        'is_participant': is_participant,
        'can_vote': request.user.is_authenticated and not is_participant and user_vote is None and duel.is_voting_open,
        'can_comment': is_participant and duel.status == Duel.STATUS_ACTIVE,
        'source_post': source_post,
        'duel_comments': duel.comments.select_related('author'),
        'comment_max_length': DUEL_COMMENT_MAX_LENGTH,
        'page_title': f'{duel.topic} - 일기토 - 독존',
        'meta_description': f'{duel.challenger.nickname} vs {duel.opponent.nickname}, {duel.topic} 일기토 투표 현황입니다.',
    }
    return render(request, 'duels/duel_detail.html', context)


@login_required
@require_POST
def duel_vote(request, pk):
    duel = get_object_or_404(Duel, pk=pk)
    duel.resolve_if_needed()

    side = request.POST.get('side')
    valid_sides = {choice for choice, _ in DuelVote.SIDE_CHOICES}

    if not duel.is_voting_open:
        messages.error(request, '투표가 마감되었거나 아직 시작하지 않은 일기토입니다.')
    elif side not in valid_sides:
        messages.error(request, '선택이 올바르지 않습니다.')
    elif duel.votes.filter(voter=request.user).exists():
        messages.error(request, '이미 투표한 일기토입니다.')
    elif request.user.id in (duel.challenger_id, duel.opponent_id):
        messages.error(request, '본인이 출전한 일기토에는 투표할 수 없습니다.')
    else:
        DuelVote.objects.create(duel=duel, voter=request.user, side=side)
        messages.success(request, '투표가 반영되었습니다.')

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'challenger_votes': duel.challenger_votes,
            'opponent_votes': duel.opponent_votes,
            'challenger_percent': duel.challenger_percent,
            'opponent_percent': duel.opponent_percent,
        })

    return redirect('duels:duel_detail', pk=duel.pk)


@login_required
@require_POST
def duel_challenge(request, post_pk):
    """게시글에서 "1:1 일기토 신청" (2026-09-24).

    신청하면 바로 진행중(active) 듀얼이 생기고 투표가 열립니다.
    신청자 = challenger(도전자), 원본글 작성자 = opponent(상대).
    한 글에는 동시에 하나의 진행중 일기토만 걸 수 있습니다.
    """
    post = get_object_or_404(Post.objects.select_related('author', 'board'), pk=post_pk)
    back_to_post = redirect('boards:post_detail', slug=post.board.slug, pk=post.pk)

    existing = active_duel_for_post(post)
    if existing:
        messages.info(request, '이 글에는 이미 진행중인 일기토가 있습니다.')
        return redirect('duels:duel_detail', pk=existing.pk)

    if not can_challenge_post(request.user, post):
        messages.error(request, '상대 진영 회원의 보수/민주 아레나 글에만 일기토를 신청할 수 있습니다.')
        return back_to_post

    now = timezone.now()
    duel = Duel.objects.create(
        topic=post.title[:200],
        challenger=request.user,
        opponent=post.author,
        start_at=now,
        end_at=now + DUEL_DURATION,
        status=Duel.STATUS_ACTIVE,
        source_post=post,
    )
    messages.success(request, '1:1 일기토가 시작되었습니다! 아래 토론란에 첫 주장을 남겨보세요.')
    return redirect('duels:duel_detail', pk=duel.pk)


@login_required
@require_POST
def duel_comment_add(request, pk):
    """일기토 토론 댓글. 신청자와 원본글 작성자(듀얼 당사자)만 쓸 수 있습니다."""
    duel = get_object_or_404(Duel, pk=pk)
    duel.resolve_if_needed()

    content = request.POST.get('content', '').strip()
    if request.user.id not in (duel.challenger_id, duel.opponent_id):
        messages.error(request, '일기토 토론에는 신청자와 원본글 작성자만 글을 쓸 수 있습니다.')
    elif duel.status != Duel.STATUS_ACTIVE:
        messages.error(request, '종료된 일기토에는 더 이상 글을 쓸 수 없습니다.')
    elif not content:
        messages.error(request, '내용을 입력해주세요.')
    elif len(content) > DUEL_COMMENT_MAX_LENGTH:
        messages.error(request, f'내용은 {DUEL_COMMENT_MAX_LENGTH}자까지 쓸 수 있습니다.')
    else:
        DuelComment.objects.create(duel=duel, author=request.user, content=content)
        messages.success(request, '토론 글이 등록되었습니다.')

    return redirect('duels:duel_detail', pk=duel.pk)


@login_required
@require_POST
def duel_comment_delete(request, pk, comment_pk):
    duel = get_object_or_404(Duel, pk=pk)
    comment = get_object_or_404(DuelComment, pk=comment_pk, duel=duel)

    if comment.author_id != request.user.id and not request.user.is_staff:
        messages.error(request, '본인이 작성한 글만 삭제할 수 있습니다.')
    else:
        comment.delete()
        messages.success(request, '토론 글이 삭제되었습니다.')

    return redirect('duels:duel_detail', pk=duel.pk)
