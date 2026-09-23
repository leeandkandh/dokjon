# 9단계(댓글/추천) 마이그레이션.
# 실제 프로젝트(C:\dev\dokjon)의 boards 마이그레이션 체인(0001_initial,
# 0002_postimage) 위에 Comment/PostLike 모델만 추가합니다.
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('boards', '0002_postimage'),
    ]

    operations = [
        migrations.CreateModel(
            name='Comment',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.TextField(max_length=1000, verbose_name='내용')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='작성일')),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to=settings.AUTH_USER_MODEL, verbose_name='작성자')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comments', to='boards.post', verbose_name='게시글')),
            ],
            options={
                'verbose_name': '댓글',
                'verbose_name_plural': '댓글 관리',
                'ordering': ['created_at'],
            },
        ),
        migrations.CreateModel(
            name='PostLike',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='추천일')),
                ('post', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='likes', to='boards.post', verbose_name='게시글')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='post_likes', to=settings.AUTH_USER_MODEL, verbose_name='추천한 회원')),
            ],
            options={
                'verbose_name': '추천(화력)',
                'verbose_name_plural': '추천(화력) 관리',
                'constraints': [
                    models.UniqueConstraint(fields=('post', 'user'), name='unique_post_like_per_user'),
                ],
            },
        ),
    ]
