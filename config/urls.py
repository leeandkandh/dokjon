"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    # 로그인/로그아웃은 Django가 기본 제공하는 뷰를 그대로 사용
    # (login 템플릿은 templates/registration/login.html)
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # 회원가입 등 accounts 앱 URL
    path('accounts/', include('accounts.urls')),

    # 게시판(글 목록/작성/수정/삭제) URL (6단계에서 추가)
    path('', include('boards.urls')),

    # 1:1 일기토(끝장토론) 대진/투표 URL (9단계에서 추가)
    path('', include('duels.urls')),

    # core 앱(메인 페이지 등 공통 페이지)의 URL을 루트('')에 연결
    path('', include('core.urls')),
]

# 개발 중(DEBUG=True)에는 Django가 직접 media/ 폴더의 업로드 파일을 서비스합니다.
# (운영 서버에서는 이렇게 하지 않고 Nginx나 S3 등에서 직접 서비스합니다 - 14단계에서 다룰 예정)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
