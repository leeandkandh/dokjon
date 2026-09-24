from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    path('', views.home, name='home'),
    # 2026-09-24: 약관/방침/가이드/문의
    path('terms/', views.terms, name='terms'),
    path('privacy/', views.privacy, name='privacy'),
    path('guidelines/', views.guidelines, name='guidelines'),
    path('ilgito-rules/', views.duel_rules, name='duel_rules'),
    path('contact/', views.contact, name='contact'),
    path('ranks/', views.ranks, name='ranks'),
    path('contact/done/', views.contact_done, name='contact_done'),
]
