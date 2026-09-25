from django.conf import settings

# 2026-09-25 SEO: 사이트 기본 문구. 검색 결과에 제목·설명으로 그대로 노출되는 문장입니다.
# 사람들이 실제로 검색하는 단어(정치, 보수, 진보, 국민의힘, 더불어민주당, 토론, 커뮤니티)를
# 자연스러운 문장 안에 넣었습니다. 같은 단어를 과하게 반복하면 구글이 스팸으로 볼 수 있어 피했습니다.
SITE_NAME = '독존'
DEFAULT_TITLE = '독존 - 보수 vs 진보 정치 토론 커뮤니티'
DEFAULT_DESCRIPTION = (
    '독존(dokjon)은 보수와 진보, 국민의힘 지지자와 더불어민주당 지지자가 진영별 아레나에서 '
    '정치 이슈를 토론하고 1:1 일기토로 끝장토론을 벌이는 정치 커뮤니티입니다.'
)


def site_base_url(request):
    """대표 주소. .env의 SITE_URL이 있으면 그것을, 없으면 지금 접속한 주소를 씁니다."""
    return settings.SITE_URL or f'{request.scheme}://{request.get_host()}'


def seo(request):
    base = site_base_url(request)

    # canonical: 쿼리스트링(?utm=... 등)은 떼고, 게시판 페이지 번호(?page=2 이상)만 유지
    canonical = base + request.path
    page = request.GET.get('page')
    if page and page.isdigit() and page != '1':
        canonical += f'?page={page}'

    return {
        'site_name': SITE_NAME,
        'site_base_url': base,
        'canonical_url': canonical,
        'default_title': DEFAULT_TITLE,
        'default_description': DEFAULT_DESCRIPTION,
        'google_site_verification': settings.GOOGLE_SITE_VERIFICATION,
        'naver_site_verification': settings.NAVER_SITE_VERIFICATION,
    }
