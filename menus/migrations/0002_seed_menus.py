from django.db import migrations


# 초기 메뉴 데이터: GNB 5개(보수/민주/일기토/일반/금융) + LNB 2개(일반>자유, 금융>주식)
# data migration으로 넣어두면, 다른 개발자가 이 프로젝트를 새로 내려받아 migrate만 해도
# 처음부터 화면에 메뉴가 똑같이 뜹니다. (운영 중에는 관리자페이지에서 자유롭게 수정)
GNB_ITEMS = [
    {'name': '보수', 'slug': 'conservative', 'order': 1},
    {'name': '민주', 'slug': 'democrat', 'order': 2},
    {'name': '일기토', 'slug': 'ilgito', 'order': 3},
    {'name': '일반', 'slug': 'general', 'order': 4},
    {'name': '금융', 'slug': 'finance', 'order': 5},
]

# {부모 slug: [자식(name, slug, order), ...]}
LNB_ITEMS = {
    'general': [{'name': '자유', 'slug': 'free', 'order': 1}],
    'finance': [{'name': '주식', 'slug': 'stock', 'order': 1}],
}


def seed_menus(apps, schema_editor):
    Menu = apps.get_model('menus', 'Menu')

    slug_to_id = {}
    for item in GNB_ITEMS:
        menu = Menu.objects.create(
            name=item['name'], slug=item['slug'], order=item['order'], parent=None,
        )
        slug_to_id[item['slug']] = menu.id

    for parent_slug, children in LNB_ITEMS.items():
        parent_id = slug_to_id[parent_slug]
        for child in children:
            Menu.objects.create(
                name=child['name'], slug=child['slug'], order=child['order'],
                parent_id=parent_id,
            )


def remove_seed_menus(apps, schema_editor):
    Menu = apps.get_model('menus', 'Menu')
    all_slugs = [item['slug'] for item in GNB_ITEMS]
    for children in LNB_ITEMS.values():
        all_slugs += [child['slug'] for child in children]
    Menu.objects.filter(slug__in=all_slugs).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('menus', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_menus, remove_seed_menus),
    ]
