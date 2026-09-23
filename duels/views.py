from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Duel, DuelVote


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

    context = {
        'duel': duel,
        'user_vote': user_vote,
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
