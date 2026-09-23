from django.contrib.auth import login as auth_login
from django.http import JsonResponse
from django.shortcuts import redirect, render

from .forms import SignUpForm
from .models import User


def signup(request):
    """회원가입 화면.

    가입에 성공하면 바로 로그인 상태로 만들어서 메인 페이지로 보냅니다.
    (요구사항 12장: 회원가입 시 약관 동의 화면은 5단계 이후 별도로 추가 예정)
    """
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('core:home')
    else:
        form = SignUpForm()

    return render(request, 'accounts/signup.html', {'form': form})


def check_username(request):
    """아이디 중복확인 (AJAX). ?username=값 형태로 GET 요청을 받습니다."""
    username = request.GET.get('username', '').strip()
    available = bool(username) and not User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'available': available})


def check_nickname(request):
    """닉네임 중복확인 (AJAX). ?nickname=값 형태로 GET 요청을 받습니다."""
    nickname = request.GET.get('nickname', '').strip()
    available = bool(nickname) and not User.objects.filter(nickname__iexact=nickname).exists()
    return JsonResponse({'available': available})


def check_email(request):
    """이메일 중복확인 (AJAX). ?email=값 형태로 GET 요청을 받습니다."""
    email = request.GET.get('email', '').strip()
    available = bool(email) and not User.objects.filter(email__iexact=email).exists()
    return JsonResponse({'available': available})
