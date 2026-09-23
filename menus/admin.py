from django.contrib import admin

from .models import Menu


@admin.register(Menu)
class MenuAdmin(admin.ModelAdmin):
    """관리자페이지에서 GNB/LNB 메뉴를 추가/순서변경/숨김 처리하는 화면.

    - 상위 메뉴(parent)를 비워두면 GNB, 선택하면 그 메뉴의 LNB가 됩니다.
    - 사용 여부(is_active) 체크를 해제하면 삭제하지 않고도 화면에서 숨길 수 있습니다.
    """
    list_display = ('name', 'slug', 'parent', 'order', 'is_active')
    list_filter = ('is_active', 'parent')
    list_editable = ('order', 'is_active')
    search_fields = ('name', 'slug')
    ordering = ('order', 'id')
    prepopulated_fields = {'slug': ('name',)}
