from django.db import models


class Menu(models.Model):
    """GNB(주 메뉴)/LNB(하위 메뉴)를 관리자가 직접 추가/수정/삭제할 수 있도록 하는 모델.

    구조:
    - parent가 없는(=None) 메뉴 ⇒ GNB(상단 주 메뉴). 예) 보수, 민주, 일기토, 일반, 금융
    - parent가 있는 메뉴 ⇒ 그 부모 GNB에 속하는 LNB(왼쪽 하위 메뉴). 예) 일반 > 자유

    이렇게 부모-자식 관계(self-referential ForeignKey) 하나로 GNB/LNB를 함께 표현하면,
    관리자페이지(admin)에서 메뉴를 추가/순서변경/숨김 처리할 때마다
    화면(gnb.html, lnb.html)에 자동으로 반영됩니다. (6단계에서 게시판이 생기면
    url 필드를 실제 게시판 주소로 채워 넣을 예정입니다. 지금은 '#' 기본값)
    """

    name = models.CharField('메뉴 이름', max_length=30)

    # 화면에 표시되는 링크 텍스트와 별개로, CSS 클래스(gnb-conservative 등)와
    # 나중에 게시판 URL(/board/<slug>/)에도 쓸 영문 식별자입니다.
    slug = models.SlugField(
        'slug (영문 식별자)',
        max_length=30,
        help_text='영문 소문자/숫자/하이픈만 사용 (예: conservative, democrat). CSS 색상, 게시판 주소에 사용됩니다.',
    )

    parent = models.ForeignKey(
        'self',
        verbose_name='상위 메뉴 (GNB)',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name='children',
        help_text='비워두면 GNB(주 메뉴)가 되고, 상위 메뉴를 선택하면 그 메뉴의 LNB(하위 메뉴)가 됩니다.',
    )

    url = models.CharField(
        '링크 주소',
        max_length=200,
        default='#',
        blank=True,
        help_text='게시판이 아직 없는 메뉴는 "#"으로 두세요. 6단계(게시판)에서 실제 주소로 교체합니다.',
    )

    order = models.PositiveIntegerField(
        '표시 순서',
        default=0,
        help_text='숫자가 작을수록 먼저 표시됩니다.',
    )

    is_active = models.BooleanField(
        '사용 여부',
        default=True,
        help_text='체크를 해제하면 삭제하지 않고도 화면에서 숨길 수 있습니다.',
    )

    class Meta:
        verbose_name = '메뉴'
        verbose_name_plural = '메뉴 관리'
        ordering = ['order', 'id']

    def __str__(self):
        if self.parent_id:
            return f'{self.parent.name} > {self.name}'
        return self.name
