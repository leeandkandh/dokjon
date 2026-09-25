"""SEO 도우미 (2026-09-25).

구조화 데이터(JSON-LD)를 <script type="application/ld+json"> 안에 안전하게 넣을 수 있는 문자열로 만듭니다.
게시글 내용에 "</script>" 같은 글자가 있어도 스크립트 태그가 깨지지 않도록 "</"를 이스케이프합니다.
"""
import json

from .context_processors import site_base_url


def to_jsonld(data):
    return json.dumps(data, ensure_ascii=False).replace('</', '<\\/')


def absolute_url(request, path):
    """/board/... 같은 상대 주소를 https://도메인/board/... 절대 주소로."""
    if not path:
        return None
    if path.startswith(('http://', 'https://')):
        return path
    return site_base_url(request) + path


def breadcrumb(request, items):
    """items = [(이름, 상대주소), ...] → 구글 "이동 경로(BreadcrumbList)" 구조화 데이터."""
    return {
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': i, 'name': name, 'item': absolute_url(request, url)}
            for i, (name, url) in enumerate(items, start=1)
        ],
    }
