from django.urls import path

from . import views

app_name = 'boards'

urlpatterns = [
    path('board/<slug:slug>/', views.post_list, name='post_list'),
    path('board/<slug:slug>/write/', views.post_create, name='post_create'),
    path('board/<slug:slug>/upload-image/', views.upload_image, name='upload_image'),
    path('board/<slug:slug>/<int:pk>/', views.post_detail, name='post_detail'),
    path('board/<slug:slug>/<int:pk>/edit/', views.post_edit, name='post_edit'),
    path('board/<slug:slug>/<int:pk>/delete/', views.post_delete, name='post_delete'),
    path('board/<slug:slug>/<int:pk>/comments/', views.comment_add, name='comment_add'),
    path('board/<slug:slug>/<int:pk>/comments/<int:comment_pk>/delete/', views.comment_delete, name='comment_delete'),
    path('board/<slug:slug>/<int:pk>/like/', views.like_toggle, name='like_toggle'),
    # 2026-09-25: 반대 + 댓글 추천/반대
    path('board/<slug:slug>/<int:pk>/dislike/', views.dislike_toggle, name='dislike_toggle'),
    path('board/<slug:slug>/<int:pk>/comments/<int:comment_pk>/vote/', views.comment_vote, name='comment_vote'),
]
