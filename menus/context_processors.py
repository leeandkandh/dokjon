from django.db.models import Prefetch

from .models import Menu


def menu_context(request):
    """모든 템플릿에서 gnb_items를 바로 쓸 수 있도록 전역 context에 메뉴를 넣어줍니다.

    settings.py의 TEMPLATES > OPTIONS > context_processors에 등록해두면,
    각 view에서 매번 메뉴 목록을 조회해서 context에 넣어줄 필요 없이
    gnb.html / lnb.html에서 바로 {% for item in gnb_items %} 로 사용할 수 있습니다.

    parent가 없는(=GNB) 메뉴만 최상위로 가져오고, 각 메뉴의 하위 메뉴(children)는
    prefetch_related로 미리 가져와서 화면 하나 그릴 때 DB에 딱 2번만 질의합니다.
    """
    children_qs = Menu.objects.filter(is_active=True).order_by('order', 'id')
    gnb_items = (
        Menu.objects
        .filter(parent__isnull=True, is_active=True)
        .order_by('order', 'id')
        .prefetch_related(Prefetch('children', queryset=children_qs))
    )
    return {'gnb_items': gnb_items}
