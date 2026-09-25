"""sitemap.xml (2026-09-25 SEO).

구글·네이버에 "이 사이트에 이런 페이지들이 있다"고 알려주는 지도입니다.
구글 서치 콘솔 / 네이버 서치어드바이저에 https://www.dokjon.com/sitemap.xml 을 제출하세요.
글이 새로 올라오면 자동으로 목록에 포함됩니다.
"""
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from boards.models import Post
from duels.models import Duel
from menus.models import Menu


class _BaseSitemap(Sitemap):
    """.env의 SITE_URL(예: https://www.dokjon.com)이 있으면 그 도메인으로 주소를 만듭니다."""

    def get_domain(self, site=None):
        if settings.SITE_URL:
            return urlsplit(settings.SITE_URL).netloc
        return super().get_domain(site)

    def get_protocol(self, protocol=None):
        if settings.SITE_URL:
            return urlsplit(settings.SITE_URL).scheme or 'https'
        return super().get_protocol(protocol)


class StaticPageSitemap(_BaseSitemap):
    changefreq = 'daily'

    def items(self):
        return ['core:home', 'duels:duel_list', 'core:ranks', 'core:guidelines', 'core:duel_rules', 'core:terms', 'core:privacy']

    def location(self, item):
        return reverse(item)

    def priority(self, item):
        return {'core:home': 1.0, 'duels:duel_list': 0.8}.get(item, 0.4)


class BoardSitemap(_BaseSitemap):
    """보수 아레나 / 민주 아레나 / 자유 등 실제 게시판(하위 메뉴가 없는 활성 메뉴)."""

    changefreq = 'hourly'
    priority = 0.9

    def items(self):
        return [m for m in Menu.objects.filter(is_active=True).order_by('order') if m.slug and not m.children.exists() and m.slug != 'ilgito']

    def location(self, menu):
        return reverse('boards:post_list', args=[menu.slug])


class PostSitemap(_BaseSitemap):
    changefreq = 'daily'
    priority = 0.7
    limit = 5000

    def items(self):
        return Post.objects.filter(board__is_active=True).select_related('board').order_by('-created_at')

    def location(self, post):
        return reverse('boards:post_detail', args=[post.board.slug, post.pk])

    def lastmod(self, post):
        return post.updated_at


class DuelSitemap(_BaseSitemap):
    changefreq = 'hourly'
    priority = 0.6

    def items(self):
        return Duel.objects.exclude(status=Duel.STATUS_SCHEDULED).order_by('-start_at')

    def location(self, duel):
        return reverse('duels:duel_detail', args=[duel.pk])

    def lastmod(self, duel):
        return duel.end_at if duel.status == Duel.STATUS_FINISHED else duel.start_at


SITEMAPS = {
    'pages': StaticPageSitemap,
    'boards': BoardSitemap,
    'posts': PostSitemap,
    'duels': DuelSitemap,
}
