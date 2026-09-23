# 9단계(포인트/등급) 마이그레이션.
# 실제 프로젝트(C:\dev\dokjon)의 accounts 마이그레이션 체인(0001_initial,
# 0002_alter_user_birth_date_alter_user_party_and_more) 위에 points/duel_wins/
# duel_losses 필드 3개만 추가합니다.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_alter_user_birth_date_alter_user_party_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='points',
            field=models.PositiveIntegerField(default=0, verbose_name='포인트'),
        ),
        migrations.AddField(
            model_name='user',
            name='duel_wins',
            field=models.PositiveIntegerField(default=0, verbose_name='일기토 승'),
        ),
        migrations.AddField(
            model_name='user',
            name='duel_losses',
            field=models.PositiveIntegerField(default=0, verbose_name='일기토 패'),
        ),
    ]
