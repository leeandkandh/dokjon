from django.db import migrations

# 2026-09-23: 사용자가 준 참고 디자인의 상단 메뉴 이름으로 게시판 이름을 바꿉니다.
# 보수 -> 보수 아레나 / 민주 -> 민주 아레나 / 일기토 -> 일기토 (1:1 끝장토론)
# 일반>자유 -> "자유토론"으로 이름을 바꾸고 최상위 메뉴로 승격 (더 이상 "일반" 밑에 있지 않음)
# 금융 -> "여론/금융"으로 이름을 바꾸고, 하위 메뉴였던 "주식"은 숨김 처리
# (참고 이미지의 상단 메뉴바에는 하위 메뉴 없이 6개가 한 줄로 나란히 있었습니다)

RENAMES = {
    'conservative': '보수 아레나',
    'democrat': '민주 아레나',
    'ilgito': '일기토 (1:1 끝장토론)',
}


def rename_boards(apps, schema_editor):
    Menu = apps.get_model('menus', 'Menu')

    for slug, new_name in RENAMES.items():
        Menu.objects.filter(slug=slug).update(name=new_name)

    free = Menu.objects.filter(slug='free').first()
    if free:
        free.name = '자유토론'
        free.parent = None
        free.order = 5
        free.save()

    general = Menu.objects.filter(slug='general').first()
    if general:
        general.is_active = False
        general.save()

    finance = Menu.objects.filter(slug='finance').first()
    if finance:
        finance.name = '여론/금융'
        finance.order = 6
        finance.save()

    stock = Menu.objects.filter(slug='stock').first()
    if stock:
        stock.is_active = False
        stock.save()


def revert_renames(apps, schema_editor):
    Menu = apps.get_model('menus', 'Menu')

    original_names = {
        'conservative': '보수',
        'democrat': '민주',
        'ilgito': '일기토',
        'finance': '금융',
    }
    for slug, name in original_names.items():
        Menu.objects.filter(slug=slug).update(name=name)

    general = Menu.objects.filter(slug='general').first()
    if general:
        general.is_active = True
        general.save()

    free = Menu.objects.filter(slug='free').first()
    if free and general:
        free.name = '자유'
        free.parent = general
        free.order = 1
        free.save()

    stock = Menu.objects.filter(slug='stock').first()
    if stock:
        stock.is_active = True
        stock.save()


class Migration(migrations.Migration):

    dependencies = [
        ('menus', '0002_seed_menus'),
    ]

    operations = [
        migrations.RunPython(rename_boards, revert_renames),
    ]
