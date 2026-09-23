import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Menu',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=30, verbose_name='메뉴 이름')),
                ('slug', models.SlugField(help_text='영문 소문자/숫자/하이픈만 사용 (예: conservative, democrat). CSS 색상, 게시판 주소에 사용됩니다.', max_length=30, verbose_name='slug (영문 식별자)')),
                ('url', models.CharField(blank=True, default='#', help_text='게시판이 아직 없는 메뉴는 "#"으로 두세요. 6단계(게시판)에서 실제 주소로 교체합니다.', max_length=200, verbose_name='링크 주소')),
                ('order', models.PositiveIntegerField(default=0, help_text='숫자가 작을수록 먼저 표시됩니다.', verbose_name='표시 순서')),
                ('is_active', models.BooleanField(default=True, help_text='체크를 해제하면 삭제하지 않고도 화면에서 숨길 수 있습니다.', verbose_name='사용 여부')),
                ('parent', models.ForeignKey(blank=True, help_text='비워두면 GNB(주 메뉴)가 되고, 상위 메뉴를 선택하면 그 메뉴의 LNB(하위 메뉴)가 됩니다.', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='menus.menu', verbose_name='상위 메뉴 (GNB)')),
            ],
            options={
                'verbose_name': '메뉴',
                'verbose_name_plural': '메뉴 관리',
                'ordering': ['order', 'id'],
            },
        ),
    ]
