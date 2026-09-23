from django.urls import path

from . import views

app_name = 'duels'

urlpatterns = [
    path('ilgito/', views.duel_list, name='duel_list'),
    path('ilgito/<int:pk>/', views.duel_detail, name='duel_detail'),
    path('ilgito/<int:pk>/vote/', views.duel_vote, name='duel_vote'),
]
