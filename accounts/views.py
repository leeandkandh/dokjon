from django.contrib import messages
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.db import transaction
from django.urls import reverse_lazy

from .forms import ProfileForm, SignUpForm, WithdrawForm
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


@login_required
def mypage(request):
    """마이페이지 = 내 정보 보기/변경 (2026-09-24).

    아이디/닉네임/진영은 읽기 전용으로 보여주기만 하고, 이메일/생년월일/성별만 바꿀 수 있습니다.
    """
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, '내 정보가 변경되었습니다.')
            return redirect('accounts:mypage')
    else:
        form = ProfileForm(instance=request.user)

    context = {
        'form': form,
        'page_title': '마이페이지 - 독존',
    }
    return render(request, 'accounts/mypage.html', context)


class MyPasswordChangeView(auth_views.PasswordChangeView):
    """마이페이지에서 들어가는 비밀번호 변경. 바꾼 뒤에도 로그인 상태는 유지됩니다(Django 기본 동작)."""

    template_name = 'accounts/password_change.html'
    success_url = reverse_lazy('accounts:mypage')

    def form_valid(self, form):
        messages.success(self.request, '비밀번호가 변경되었습니다.')
        return super().form_valid(form)


@login_required
def withdraw(request):
    """회원 탈퇴 (2026-09-24). 마이페이지 맨 아래 "회원 탈퇴"에서 들어옵니다.

    비밀번호 재확인 + 동의 체크 후 User.withdraw()로 개인정보를 지우고 로그아웃합니다.
    "글·댓글도 삭제"를 고르면 본인 게시글(첨부 이미지·댓글·화력 포함)과 본인 댓글을 지웁니다.
    일기토 토론 글과 투표는 상대방·다른 회원의 기록이라 남습니다(작성자는 "탈퇴회원N"으로 표시).
    """
    user = request.user
    if user.is_superuser:
        messages.error(request, '관리자(슈퍼유저) 계정은 여기서 탈퇴할 수 없습니다. 관리자 페이지에서 처리해주세요.')
        return redirect('accounts:mypage')

    from boards.models import Comment, Post  # accounts ↔ boards 순환 import 방지

    post_count = Post.objects.filter(author=user).count()
    comment_count = Comment.objects.filter(author=user).count()

    if request.method == 'POST':
        form = WithdrawForm(user, request.POST)
        if form.is_valid():
            with transaction.atomic():
                if form.cleaned_data['delete_content']:
                    Comment.objects.filter(author=user).delete()
                    Post.objects.filter(author=user).delete()
                user.withdraw()
            auth_logout(request)
            messages.success(request, '회원 탈퇴가 완료되었습니다. 그동안 독존을 이용해주셔서 감사합니다.')
            return redirect('core:home')
    else:
        form = WithdrawForm(user)

    context = {
        'form': form,
        'post_count': post_count,
        'comment_count': comment_count,
        'page_title': '회원 탈퇴 - 독존',
    }
    return render(request, 'accounts/withdraw.html', context)
