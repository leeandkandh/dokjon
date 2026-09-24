from django.urls import path

from . import views

app_name = 'duels'

urlpatterns = [
    path('ilgito/', views.duel_list, name='duel_list'),
    path('ilgito/<int:pk>/', views.duel_detail, name='duel_detail'),
    path('ilgito/<int:pk>/vote/', views.duel_vote, name='duel_vote'),
    # 2026-09-24: 게시글에서 일기토 신청 + 당사자 전용 토론 댓글
    path('ilgito/challenge/<int:post_pk>/', views.duel_challenge, name='duel_challenge'),
    path('ilgito/<int:pk>/comments/', views.duel_comment_add, name='duel_comment_add'),
    path('ilgito/<int:pk>/comments/<int:comment_pk>/delete/', views.duel_comment_delete, name='duel_comment_delete'),
]
