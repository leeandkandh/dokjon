from django import template
from django.utils.safestring import mark_safe

from boards.youtube import embed_youtube

register = template.Library()


@register.filter
def youtube_embed(html):
    """{{ post.content|youtube_embed }} — 유튜브 링크 아래에 영상 플레이어를 붙입니다 (boards/youtube.py).

    post.content는 저장할 때 이미 bleach로 위험한 태그를 걸러낸 HTML이고, 여기서 추가하는 것은
    영상 ID(영문·숫자·-·_ 11자리)만 넣어 만든 고정된 iframe이라 안전합니다.
    """
    return mark_safe(embed_youtube(html))
