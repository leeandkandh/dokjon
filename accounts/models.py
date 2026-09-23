from django.contrib.auth.models import AbstractUser
from django.core.validators import MinLengthValidator, RegexValidator
from django.db import models

# 요구사항 12장 + 2026-09-22 변경: 아이디는 영문(대소문자)+숫자만 허용
username_letters_digits_validator = RegexValidator(
    regex=r'^[A-Za-z0-9]+$',
    message='아이디는 영문과 숫자만 사용할 수 있습니다. (특수문자, 한글, 공백 불가)',
)

PARTY_CHOICES = [
    ('conservative', '보수'),
    ('democrat', '진보'),
]

# 9단계(요구사항 19장 "회원등급 산정기준") 포인트 등급표.
# (필요 포인트, 등급명) 튜플을 포인트가 낮은 순서로 나열합니다.
# 정치 배틀 아레나 컨셉에 맞춰 "예비당원"에서 "대통령"까지 9단계로 구성했습니다.
# 포인트를 얼마나 줄지는 boards/duels 앱의 POINTS_* 상수를 참고하세요.
RANK_TIERS = [
    (0, '예비당원'),
    (30, '청년당원'),
    (80, '지역위원장'),
    (150, '초선의원'),
    (300, '재선의원'),
    (500, '원내대표'),
    (800, '당대표'),
    (1200, '국무총리'),
    (2000, '대통령'),
]


class User(AbstractUser):
    """독존의 회원 모델.

    Django 기본 User를 확장해서 닉네임/생년월일/진영 필드를 추가했습니다.
    이렇게 프로젝트 맨 처음(첫 migrate 전)에 커스텀 User를 설정해두면,
    나중에 필드를 추가하기 쉽습니다. (기본 User를 쓰다가 나중에 바꾸는 것은
    현업에서도 아주 번거로운 작업이라 꼭 피해야 합니다.)
    """

    username = models.CharField(
        '아이디',
        max_length=20,
        unique=True,
        validators=[MinLengthValidator(4, message='아이디는 4자 이상이어야 합니다.'),
                    username_letters_digits_validator],
        error_messages={'unique': '이미 사용 중인 아이디입니다.'},
        help_text='영문/숫자 4~20자 (특수문자/한글 불가)',
    )
    nickname = models.CharField(
        '닉네임',
        max_length=15,
        unique=True,
        validators=[MinLengthValidator(4, message='닉네임은 4자 이상이어야 합니다.')],
        error_messages={'unique': '이미 사용 중인 닉네임입니다.'},
        help_text='한글/영문/숫자 4~15자',
    )
    # null=True, blank=True: createsuperuser로 관리자 계정을 만들 때는
    # 생년월일을 입력받지 않으므로(REQUIRED_FIELDS에 없음), 값이 없어도
    # 저장 가능하도록 허용해야 DB 오류(NOT NULL 제약 위반)가 나지 않습니다.
    # 일반 회원가입(SignUpForm)에서는 필수 입력이므로 실제로는 항상 값이 들어갑니다.
    birth_date = models.DateField('생년월일', null=True, blank=True)
    party = models.CharField('진영', max_length=20, choices=PARTY_CHOICES, blank=True)

    # 요구사항 13장(관리자)에서 쓸 상태: 정지회원 여부
    is_suspended = models.BooleanField('정지회원 여부', default=False)

    # 9단계: 글쓰기/댓글/추천받음/일기토 승리 등으로 쌓이는 활동 포인트.
    # 이 값으로 아래 rank_name(등급)과 명예의 전당 랭킹을 계산합니다.
    points = models.PositiveIntegerField('포인트', default=0)

    # 1:1 일기토(듀얼) 전적. 듀얼이 끝나면 duels 앱에서 이 값을 갱신합니다.
    duel_wins = models.PositiveIntegerField('일기토 승', default=0)
    duel_losses = models.PositiveIntegerField('일기토 패', default=0)

    # createsuperuser 실행 시 아이디/비밀번호 외에 추가로 물어볼 필드
    REQUIRED_FIELDS = ['email', 'nickname']

    def __str__(self):
        return self.nickname or self.username

    @property
    def rank_name(self):
        """현재 포인트에 해당하는 9단계 등급명 (예: '초선의원')."""
        name = RANK_TIERS[0][1]
        for threshold, tier_name in RANK_TIERS:
            if self.points >= threshold:
                name = tier_name
            else:
                break
        return name

    @property
    def duel_record(self):
        """전적 뱃지에 쓸 'N승 M패' 문자열. 아직 한 번도 안 붙었으면 None."""
        if self.duel_wins == 0 and self.duel_losses == 0:
            return None
        return f'{self.duel_wins}승 {self.duel_losses}패'

    @property
    def duel_win_rate(self):
        """일기토 승률(%). 붙은 적이 없으면 None."""
        total = self.duel_wins + self.duel_losses
        if total == 0:
            return None
        return round(self.duel_wins / total * 100)
