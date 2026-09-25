"""유튜브 링크 → 영상 플레이어 (2026-09-25).

글 본문(Quill 에디터가 만든 HTML)에 유튜브 주소가 있으면, 그 주소가 들어 있는 문단 바로 아래에
유튜브 플레이어(iframe)를 끼워 넣습니다. 저장된 글 내용 자체는 바꾸지 않고, 화면에 보여줄 때만 변환합니다.
(그래서 이미 올라와 있던 옛날 글에도 바로 적용됩니다)

지원하는 주소 형태:
  https://www.youtube.com/watch?v=XXXXXXXXXXX   (&t=, &list= 등 뒤에 붙은 값은 무시)
  https://youtu.be/XXXXXXXXXXX
  https://www.youtube.com/shorts/XXXXXXXXXXX
  https://www.youtube.com/live/XXXXXXXXXXX
  https://m.youtube.com/watch?v=XXXXXXXXXXX
"""
import re

from django.utils.html import escape

YOUTUBE_ID_RE = re.compile(
    r'(?:https?:)?//(?:www\.|m\.|music\.)?'
    r'(?:youtube\.com/(?:watch\?(?:[^"\'\s<>]*?(?:&amp;|&))?v=|shorts/|live/|embed/)|youtu\.be/)'
    r'([A-Za-z0-9_-]{11})(?![A-Za-z0-9_-])'
)
# 영상을 끼워 넣을 기준이 되는 "문단" 단위 (p, 제목, 인용)
_BLOCK_RE = re.compile(r'<(p|h[1-3]|blockquote)\b[^>]*>.*?</\1>', re.IGNORECASE | re.DOTALL)
MAX_EMBEDS = 10


def youtube_ids(html):
    """본문에 나오는 유튜브 영상 ID를 순서대로, 중복 없이."""
    seen = []
    for vid in YOUTUBE_ID_RE.findall(html or ''):
        if vid not in seen:
            seen.append(vid)
    return seen


def player_html(video_id):
    vid = escape(video_id)
    # youtube-nocookie.com: 영상을 재생하기 전까지 유튜브가 방문자 추적 쿠키를 심지 않는 "개인정보 보호 모드" 주소
    return (
        '<div class="video-embed">'
        f'<iframe src="https://www.youtube-nocookie.com/embed/{vid}" title="YouTube 동영상" loading="lazy" '
        'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share" '
        'referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe>'
        '</div>'
    )


def embed_youtube(html):
    """본문 HTML에서 유튜브 링크가 있는 문단 아래에 플레이어를 붙인 HTML을 돌려줍니다."""
    if not html or ('youtu' not in html):
        return html

    embedded = []

    def add_players(match):
        block = match.group(0)
        players = ''
        for vid in youtube_ids(block):
            if vid not in embedded and len(embedded) < MAX_EMBEDS:
                embedded.append(vid)
                players += player_html(vid)
        return block + players

    result = _BLOCK_RE.sub(add_players, html)

    # 목록(li) 안처럼 문단 밖에 있던 링크는 본문 맨 아래에 붙입니다
    for vid in youtube_ids(html):
        if vid not in embedded and len(embedded) < MAX_EMBEDS:
            embedded.append(vid)
            result += player_html(vid)
    return result
