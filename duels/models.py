from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


# 9단계: 일기토(1:1 끝장토론) 승/패에 지급하는 포인트.
# 글쓰기/댓글/추천 포인트는 boards/models.py에 있습니다.
POINTS_DUEL_WIN = 50
POINTS_DUEL_LOSS = 10  # 져도 참가 자체에 포인트를 줘서 도전을 장려합니다.

# 2026-09-24: 게시글에서 "1:1 일기토 신청"으로 만들어진 듀얼의 투표 기간.
# 신청 즉시 진행중(active)으로 시작하고, 이 기간이 지나면 득표수로 승패가 자동 판정됩니다.
DUEL_DURATION = timedelta(days=3)


class Duel(models.Model):
    """1:1 일기토(끝장토론) 한 판.

    보수/민주 대표 논객 두 명이 주제를 놓고 붙고, 회원들은 어느 쪽 주장이
    더 설득력 있었는지 한 번씩 투표합니다. 투표는 end_at(마감 시각) 전까지만
    가능하고, 마감이 지나면 득표수가 많은 쪽이 승리로 판정됩니다(동률이면
    무승부 처리하고 전적에는 반영하지 않습니다).
    """

    STATUS_SCHEDULED = 'scheduled'
    STATUS_ACTIVE = 'active'
    STATUS_FINISHED = 'finished'
    STATUS_CHOICES = [
        (STATUS_SCHEDULED, '대기중'),
        (STATUS_ACTIVE, '진행중'),
        (STATUS_FINISHED, '종료'),
    ]

    topic = models.CharField('주제', max_length=200)
    description = models.TextField('부연 설명', blank=True)

    challenger = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='도전자',
        on_delete=models.CASCADE,
        related_name='duels_as_challenger',
    )
    opponent = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='상대',
        on_delete=models.CASCADE,
        related_name='duels_as_opponent',
    )

    start_at = models.DateTimeField('시작 시각')
    end_at = models.DateTimeField('투표 마감 시각')
    status = models.CharField('상태', max_length=20, choices=STATUS_CHOICES, default=STATUS_SCHEDULED)

    winner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='승자',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duels_won',
    )

    # 2026-09-24: 보수/민주 아레나 게시글에서 상대 진영 회원이 "1:1 일기토 신청"을 누르면
    # 그 글(원본글)을 걸고 듀얼이 생깁니다. 관리자가 직접 등록한 듀얼은 원본글이 없습니다(null).
    # 원본글이 나중에 삭제돼도 듀얼 기록은 남도록 SET_NULL.
    source_post = models.ForeignKey(
        'boards.Post',
        verbose_name='원본글',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='duels',
    )

    created_at = models.DateTimeField('등록일', auto_now_add=True)

    class Meta:
        verbose_name = '1:1 일기토'
        verbose_name_plural = '1:1 일기토 관리'
        ordering = ['-start_at']

    def __str__(self):
        return f'{self.topic} ({self.challenger.nickname} vs {self.opponent.nickname})'

    @property
    def challenger_votes(self):
        return self.votes.filter(side=DuelVote.SIDE_CHALLENGER).count()

    @property
    def opponent_votes(self):
        return self.votes.filter(side=DuelVote.SIDE_OPPONENT).count()

    @property
    def total_votes(self):
        return self.votes.count()

    @property
    def challenger_percent(self):
        total = self.total_votes
        if total == 0:
            return 50
        return round(self.challenger_votes / total * 100)

    @property
    def opponent_percent(self):
        return 100 - self.challenger_percent

    @property
    def is_voting_open(self):
        return self.status == self.STATUS_ACTIVE and timezone.now() < self.end_at

    @property
    def seconds_remaining(self):
        """홈/목록 화면 카운트다운(JS)에 넘겨줄, 마감까지 남은 초 (지났으면 0)."""
        remaining = (self.end_at - timezone.now()).total_seconds()
        return max(int(remaining), 0)

    def resolve_if_needed(self):
        """마감 시각이 지났는데 아직 진행중 상태면 득표수로 승자를 정하고
        전적(duel_wins/losses)·포인트를 반영합니다.

        실시간으로 배치/크론을 돌리는 대신, 듀얼이 조회될 때마다 이 메서드를
        호출해서 "지연 판정"하는 방식입니다 (요구사항 19장 기준 아직 별도
        스케줄러 인프라가 없어서 택한 실용적인 방법입니다).
        """
        if self.status != self.STATUS_ACTIVE or timezone.now() < self.end_at:
            return

        challenger_votes = self.challenger_votes
        opponent_votes = self.opponent_votes

        from accounts.models import User  # 순환 import 방지를 위해 함수 안에서 import

        if challenger_votes > opponent_votes:
            winner, loser = self.challenger, self.opponent
        elif opponent_votes > challenger_votes:
            winner, loser = self.opponent, self.challenger
        else:
            winner, loser = None, None

        if winner is not None:
            self.winner = winner
            User.objects.filter(pk=winner.pk).update(duel_wins=models.F('duel_wins') + 1, points=models.F('points') + POINTS_DUEL_WIN)
            User.objects.filter(pk=loser.pk).update(duel_losses=models.F('duel_losses') + 1, points=models.F('points') + POINTS_DUEL_LOSS)

        self.status = self.STATUS_FINISHED
        self.save(update_fields=['status', 'winner'])


class DuelVote(models.Model):
    """일기토 투표 1건. 한 회원은 하나의 듀얼에 한 번만 투표할 수 있습니다."""

    SIDE_CHALLENGER = 'challenger'
    SIDE_OPPONENT = 'opponent'
    SIDE_CHOICES = [
        (SIDE_CHALLENGER, '도전자'),
        (SIDE_OPPONENT, '상대'),
    ]

    duel = models.ForeignKey(Duel, verbose_name='일기토', on_delete=models.CASCADE, related_name='votes')
    voter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='투표한 회원',
        on_delete=models.CASCADE,
        related_name='duel_votes',
    )
    side = models.CharField('선택', max_length=20, choices=SIDE_CHOICES)
    voted_at = models.DateTimeField('투표일', auto_now_add=True)

    class Meta:
        verbose_name = '일기토 투표'
        verbose_name_plural = '일기토 투표 관리'
        constraints = [
            models.UniqueConstraint(fields=['duel', 'voter'], name='unique_duel_vote_per_user'),
        ]

    def __str__(self):
        return f'{self.duel.topic} - {self.voter.nickname}: {self.get_side_display()}'


class DuelComment(models.Model):
    """일기토 토론 댓글 (2026-09-24).

    읽기는 누구나 가능하지만, 쓰기는 듀얼 당사자(신청자 = challenger, 원본글 작성자 = opponent)만
    가능합니다. 일반 게시판 댓글(boards.Comment)과 달리 추천(화력) 기능이 없습니다.
    """

    duel = models.ForeignKey(Duel, verbose_name='일기토', on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name='작성자',
        on_delete=models.CASCADE,
        related_name='duel_comments',
    )
    content = models.TextField('내용', max_length=2000)
    created_at = models.DateTimeField('작성일', auto_now_add=True)

    class Meta:
        verbose_name = '일기토 토론 댓글'
        verbose_name_plural = '일기토 토론 댓글 관리'
        ordering = ['created_at']

    def __str__(self):
        return f'{self.duel.topic} - {self.author.nickname}'
