from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('signup/', views.signup, name='signup'),
    path('check-username/', views.check_username, name='check_username'),
    path('check-nickname/', views.check_nickname, name='check_nickname'),
    path('check-email/', views.check_email, name='check_email'),
    path('mypage/', views.mypage, name='mypage'),
    path('mypage/password/', views.MyPasswordChangeView.as_view(), name='password_change'),
    path('mypage/withdraw/', views.withdraw, name='withdraw'),
]
