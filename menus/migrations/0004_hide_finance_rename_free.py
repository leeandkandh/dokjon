from django.db import migrations

# 2026-09-24 요청:
# - "여론/금융" 메뉴(게시판)는 일단 숨김 처리 (삭제하지 않고 is_active=False → 나중에 관리자에서 다시 켤 수 있음)
# - "자유토론" 이름을 "자유"로 변경


def forwards(apps, schema_editor):
    Menu = apps.get_model('menus', 'Menu')
    Menu.objects.filter(slug='finance').update(is_active=False)
    Menu.objects.filter(slug='free').update(name='자유')


def backwards(apps, schema_editor):
    Menu = apps.get_model('menus', 'Menu')
    Menu.objects.filter(slug='finance').update(is_active=True)
    Menu.objects.filter(slug='free').update(name='자유토론')


class Migration(migrations.Migration):

    dependencies = [
        ('menus', '0003_rename_boards'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
