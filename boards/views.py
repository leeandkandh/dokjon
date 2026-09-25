from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.core.paginator import Paginator
from django.db.models import Count, F, Q, Value
from django.db.models.functions import Greatest
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import strip_tags
from django.views.decorators.http import require_POST

from accounts.models import PARTY_CHOICES, User
from core.seo import absolute_url, breadcrumb, to_jsonld
from duels.views import active_duel_for_post, can_challenge_post
from menus.models import Menu

from .forms import CommentForm, PostForm
from .models import (
    ALLOWED_IMAGE_CONTENT_TYPES,
    MAX_UPLOAD_IMAGE_COUNT,
    MAX_UPLOAD_IMAGE_SIZE,
    POINTS_COMMENT_WRITE,
    POINTS_COMMENT_DISLIKE_RECEIVED,
    POINTS_COMMENT_LIKE_RECEIVED,
    POINTS_DISLIKE_RECEIVED,
    POINTS_LIKE_RECEIVED,
    POINTS_POST_DELETE,
    POINTS_POST_WRITE,
    Comment,
    CommentVote,
    Post,
    PostDislike,
    PostImage,
    PostLike,
)


def _save_post_images(post, files):
    """업로드된 이미지 파일들을 검사해서 PostImage로 저장하고,
    형식/용량/개수 문제로 건너뛴 파일 이름 목록을 돌려줍니다.
    (하나라도 문제가 있다고 글 작성 전체를 막지 않고, 문제 있는 파일만 건너뜁니다)
    """
    skipped = []
    room = max(MAX_UPLOAD_IMAGE_COUNT - post.images.count(), 0)

    for f in files:
        if room <= 0:
            skipped.append(f'{f.name} (최대 {MAX_UPLOAD_IMAGE_COUNT}장까지 첨부 가능)')
            continue
        if f.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
            skipped.append(f'{f.name} (지원하지 않는 파일 형식)')
            continue
        if f.size > MAX_UPLOAD_IMAGE_SIZE:
            skipped.append(f'{f.name} (파일 용량 5MB 초과)')
            continue
        PostImage.objects.create(post=post, image=f)
        room -= 1

    return skipped


# 2026-09-24 요청: 진영 전용 게시판.
# 게시판 slug가 진영 값(conservative/democrat)과 같으면, 그 진영으로 가입한 회원만
# 글쓰기를 할 수 있습니다. (읽기·추천·댓글은 누구나 가능, 관리자는 예외로 허용)
# 2026-09-25 변경: 댓글은 진영 상관없이 로그인한 회원 누구나 쓸 수 있게 풀었습니다.
PARTY_BOARD_SLUGS = {value for value, _label in PARTY_CHOICES}
PARTY_LABELS = dict(PARTY_CHOICES)

# 게시판 목록 맨 위 "화력 BEST" 개수와 대상 기간(최근 N일) (2026-09-24)
HOT_POSTS_COUNT = 10
HOT_POSTS_DAYS = 7


# 2026-09-25 SEO: 게시판별 검색 결과 제목/설명과 목록 위 소개 문구.
# 사람들이 실제로 검색할 단어(보수, 진보, 국민의힘, 더불어민주당, 정치 토론)를 자연스럽게 넣었습니다.
BOARD_SEO = {
    'conservative': {
        'title': '보수 아레나 - 보수·국민의힘 지지자 정치 토론 게시판 | 독존',
        'description': '보수 성향 회원과 국민의힘 지지자가 정치 이슈, 정책, 선거에 대한 주장을 펼치는 독존 보수 정치 토론 게시판입니다. 진보 회원은 댓글과 1:1 일기토로 반론할 수 있습니다.',
        'intro': '보수 성향·국민의힘 지지 회원이 글을 쓰는 보수 정치 토론 게시판입니다. 진보 회원도 댓글과 1:1 일기토로 반론할 수 있습니다.',
    },
    'democrat': {
        'title': '민주 아레나 - 진보·더불어민주당 지지자 정치 토론 게시판 | 독존',
        'description': '진보 성향 회원과 더불어민주당(민주당) 지지자가 정치 이슈, 정책, 선거에 대한 주장을 펼치는 독존 진보 정치 토론 게시판입니다. 보수 회원은 댓글과 1:1 일기토로 반론할 수 있습니다.',
        'intro': '진보 성향·더불어민주당 지지 회원이 글을 쓰는 진보 정치 토론 게시판입니다. 보수 회원도 댓글과 1:1 일기토로 반론할 수 있습니다.',
    },
    'free': {
        'title': '자유 게시판 - 진영 상관없는 정치·시사 자유토론 | 독존',
        'description': '보수와 진보 진영 상관없이 누구나 정치, 시사, 선거, 일상 이야기를 자유롭게 나누는 독존 자유 게시판입니다.',
        'intro': '보수·진보 진영 상관없이 누구나 정치와 시사, 일상 이야기를 나누는 자유 게시판입니다.',
    },
}


def can_write_in_board(user, board):
    """user가 board에 "글"을 쓸 수 있는지 여부. (댓글은 로그인만 하면 누구나 가능)"""
    if not user.is_authenticated:
        return False
    if board.slug not in PARTY_BOARD_SLUGS or user.is_staff:
        return True
    return user.party == board.slug


def party_only_message(board):
    return f'{board.name}에는 회원가입 때 [{PARTY_LABELS[board.slug]}] 진영을 선택한 회원만 글을 쓸 수 있습니다. (댓글은 누구나 가능)'


def _board_seo(board):
    return BOARD_SEO.get(board.slug) or {
        'title': f'{board.name} - 정치 토론 커뮤니티 | 독존',
        'description': f'독존 {board.name} 게시판의 최신 글 목록입니다.',
        'intro': '',
    }


def _post_description(post, board):
    text = ' '.join(strip_tags(post.content).split())
    if len(text) < 40:
        text = f'{text} - {board.name}에 올라온 {post.author.nickname}님의 글. {_board_seo(board)["description"]}'.strip(' -')
    return text[:150]


def _post_structured_data(request, board, post, comments, like_count):
    """게시글 상세의 구조화 데이터 (2026-09-25 SEO).

    구글은 커뮤니티 게시글용 DiscussionForumPosting 형식을 공식 지원합니다.
    제목·본문·작성자·작성일·댓글·추천수를 알려주면 검색 결과에 "토론/포럼" 형태로 더 잘 노출됩니다.
    """
    post_url = absolute_url(request, reverse('boards:post_detail', args=[board.slug, post.pk]))
    comment_list = list(comments[:20])
    posting = {
        '@type': 'DiscussionForumPosting',
        '@id': post_url,
        'url': post_url,
        'mainEntityOfPage': post_url,
        'headline': post.title,
        'text': ' '.join(strip_tags(post.content).split())[:1000],
        'datePublished': post.created_at.isoformat(),
        'dateModified': post.updated_at.isoformat(),
        'inLanguage': 'ko-KR',
        'author': {'@type': 'Person', 'name': post.author.nickname},
        'isPartOf': {'@type': 'WebPage', 'name': board.name, 'url': absolute_url(request, reverse('boards:post_list', args=[board.slug]))},
        'interactionStatistic': [
            {'@type': 'InteractionCounter', 'interactionType': 'https://schema.org/LikeAction', 'userInteractionCount': like_count},
            {'@type': 'InteractionCounter', 'interactionType': 'https://schema.org/CommentAction', 'userInteractionCount': len(comments)},
            {'@type': 'InteractionCounter', 'interactionType': 'https://schema.org/ViewAction', 'userInteractionCount': post.view_count},
        ],
        'comment': [
            {
                '@type': 'Comment',
                'text': c.content[:500],
                'datePublished': c.created_at.isoformat(),
                'author': {'@type': 'Person', 'name': c.author.nickname},
            }
            for c in comment_list
        ],
    }
    image = absolute_url(request, post.thumbnail_url)
    if image:
        posting['image'] = image
    return to_jsonld({
        '@context': 'https://schema.org',
        '@graph': [
            posting,
            breadcrumb(request, [
                ('독존', '/'),
                (board.name, reverse('boards:post_list', args=[board.slug])),
                (post.title, reverse('boards:post_detail', args=[board.slug, post.pk])),
            ]),
        ],
    })


def _get_board_or_404(slug):
    """slug에 해당하는, 실제로 게시판 역할을 하는(=하위 메뉴가 없는) Menu를 가져옵니다.

    일반/금융처럼 하위 메뉴가 있는 GNB 자체는 게시판이 아니라 묶음일 뿐이라서
    여기서 걸러냅니다 (예: /board/general/ 처럼 직접 접근하면 404).
    """
    board = get_object_or_404(Menu, slug=slug, is_active=True)
    if board.children.exists():
        raise Http404('게시판이 아닙니다.')
    return board


def post_list(request, slug):
    board = _get_board_or_404(slug)
    # 9단계: 목록 카드에 댓글수/추천수를 보여주기 위해 annotate로 한 번에 집계합니다
    # (글마다 따로 count() 쿼리를 날리면 N+1 문제가 생깁니다).
    post_qs = (
        board.posts
        .select_related('author')
        .prefetch_related('images')
        .annotate(comment_count=Count('comments', distinct=True), like_count=Count('likes', distinct=True))
        .order_by('-created_at')
    )

    paginator = Paginator(post_qs, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    # 2026-09-24: 목록 맨 위에 "화력(추천) BEST 10"을 따로 강조해서 보여줍니다 (1페이지에서만).
    # 추천을 1개 이상 받은 글만, 화력 높은 순 → 같으면 최신순.
    # 2026-09-24 추가 결정: 최근 7일 안에 쓴 글만 대상 (오래된 인기글이 계속 상위에 남지 않게)
    hot_posts = []
    if page_obj.number == 1:
        hot_since = timezone.now() - timedelta(days=HOT_POSTS_DAYS)
        hot_posts = list(
            post_qs.filter(like_count__gt=0, created_at__gte=hot_since)
            .order_by('-like_count', '-created_at')[:HOT_POSTS_COUNT]
        )

    context = {
        'board': board,
        'page_obj': page_obj,
        'hot_posts': hot_posts,
        'hot_posts_count': HOT_POSTS_COUNT,
        'hot_posts_days': HOT_POSTS_DAYS,
        'show_demographics': board.slug in PARTY_BOARD_SLUGS,
        'can_write': can_write_in_board(request.user, board),
        # 2026-09-25 SEO: 게시판별 검색 제목/설명 (2페이지부터는 제목에 페이지 번호를 붙여 중복 제목 방지)
        'page_title': _board_seo(board)['title'] + (f' ({page_obj.number}페이지)' if page_obj.number > 1 else ''),
        'meta_description': _board_seo(board)['description'],
        'board_intro': _board_seo(board)['intro'],
        'structured_data_json': to_jsonld({
            '@context': 'https://schema.org',
            **breadcrumb(request, [('독존', '/'), (board.name, reverse('boards:post_list', args=[board.slug]))]),
        }),
    }
    return render(request, 'boards/post_list.html', context)


def post_detail(request, slug, pk):
    board = _get_board_or_404(slug)
    post = get_object_or_404(
        Post.objects.select_related('author', 'board').prefetch_related('images'),
        pk=pk, board=board,
    )

    # 조회수는 "같은 브라우저(세션)에서 처음 볼 때 한 번만" 올립니다. (2026-09-24 수정)
    # 전에는 상세 화면이 열릴 때마다 +1이라서, 추천/댓글 등록 후 이 화면으로 다시
    # 돌아올 때나 새로고침할 때도 조회수가 같이 올라가는 문제가 있었습니다.
    viewed = request.session.get('viewed_posts', [])
    if post.pk not in viewed:
        # update()로 DB에서 바로 +1 (동시에 여러 명이 봐도 안전) 후, 화면에 보여줄 값만 다시 맞춥니다.
        Post.objects.filter(pk=post.pk).update(view_count=F('view_count') + 1)
        post.view_count += 1
        viewed.append(post.pk)
        request.session['viewed_posts'] = viewed[-500:]  # 세션이 너무 커지지 않게 최근 500개만 기억

    can_edit = request.user.is_authenticated and (post.author_id == request.user.id or request.user.is_staff)

    # 2026-09-25: 댓글마다 추천/반대 수와 내가 누른 것
    comments = list(
        post.comments.select_related('author').annotate(
            up_count=Count('votes', filter=Q(votes__value=CommentVote.UP)),
            down_count=Count('votes', filter=Q(votes__value=CommentVote.DOWN)),
        )
    )
    if request.user.is_authenticated:
        my_votes = dict(CommentVote.objects.filter(comment__post=post, user=request.user).values_list('comment_id', 'value'))
        for c in comments:
            c.my_vote = my_votes.get(c.pk, 0)
    like_count = post.likes.count()
    dislike_count = post.dislikes.count()
    user_has_liked = (
        request.user.is_authenticated and post.likes.filter(user_id=request.user.id).exists()
    )
    user_has_disliked = (
        request.user.is_authenticated and post.dislikes.filter(user_id=request.user.id).exists()
    )

    context = {
        'board': board,
        'post': post,
        'can_edit': can_edit,
        'comments': comments,
        'comment_count': len(comments),
        'comment_form': CommentForm(),
        'like_count': like_count,
        'user_has_liked': user_has_liked,
        'dislike_count': dislike_count,
        'user_has_disliked': user_has_disliked,
        'is_own_post': request.user.is_authenticated and post.author_id == request.user.id,
        'can_write': can_write_in_board(request.user, board),
        'show_demographics': board.slug in PARTY_BOARD_SLUGS,
        # 2026-09-24: 1:1 일기토 신청 버튼 / 이 글에 진행중인 일기토
        'can_challenge': can_challenge_post(request.user, post),
        'active_duel': active_duel_for_post(post) if board.slug in PARTY_BOARD_SLUGS else None,
        'page_title': f'{post.title} - {board.name} | 독존',
        # content는 이제 HTML이라, meta description용으로는 태그를 뗀 순수 텍스트만 사용
        # 2026-09-25 SEO: 공백 정리 + 150자 (구글 검색 결과에 보이는 길이), 본문이 짧으면 게시판 설명으로 보충
        'meta_description': _post_description(post, board),
        'og_image_url': absolute_url(request, post.thumbnail_url),
        'structured_data_json': _post_structured_data(request, board, post, comments, like_count),
    }
    return render(request, 'boards/post_detail.html', context)


@login_required
@require_POST
def upload_image(request, slug):
    """글쓰기 에디터(Quill)에서 이미지를 드래그하거나 붙여넣었을 때 호출되는 업로드 API.

    여기서 저장하는 이미지는 "첨부 이미지"(PostImage, 글 아래 갤러리)와는 다릅니다.
    글을 아직 저장하기 전(글쓰기 화면)에도 바로 업로드가 되어야 하므로, Post와
    연결짓지 않고 media 폴더에 파일만 저장한 뒤 그 주소(URL)를 돌려주면, 에디터가
    본문 안에 <img> 태그로 바로 삽입합니다.
    """
    board = _get_board_or_404(slug)
    if not can_write_in_board(request.user, board):
        return JsonResponse({'error': party_only_message(board)}, status=403)
    f = request.FILES.get('image')

    if not f:
        return JsonResponse({'error': '파일이 없습니다.'}, status=400)
    if f.content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        return JsonResponse({'error': '지원하지 않는 파일 형식입니다. (jpg/png/gif/webp만 가능)'}, status=400)
    if f.size > MAX_UPLOAD_IMAGE_SIZE:
        return JsonResponse({'error': '파일 용량은 5MB를 넘을 수 없습니다.'}, status=400)

    saved_path = default_storage.save(f'posts/{board.slug}/inline/{f.name}', f)
    return JsonResponse({'url': default_storage.url(saved_path)})


@login_required
def post_create(request, slug):
    board = _get_board_or_404(slug)
    if not can_write_in_board(request.user, board):
        messages.error(request, party_only_message(board))
        return redirect('boards:post_list', slug=board.slug)

    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.board = board
            post.author = request.user
            post.save()

            skipped = _save_post_images(post, request.FILES.getlist('images'))
            if skipped:
                messages.warning(request, '다음 파일은 업로드되지 않았습니다: ' + ', '.join(skipped))

            # 9단계: 글쓰기 포인트 지급
            User.objects.filter(pk=post.author_id).update(points=F('points') + POINTS_POST_WRITE)

            messages.success(request, f'글이 등록되었습니다. (포인트 +{POINTS_POST_WRITE}점)')
            return redirect('boards:post_detail', slug=board.slug, pk=post.pk)
    else:
        form = PostForm()

    context = {
        'board': board,
        'form': form,
        'max_image_count': MAX_UPLOAD_IMAGE_COUNT,
        'points_post_write': POINTS_POST_WRITE,
        'page_title': f'글쓰기 - {board.name} - 독존',
    }
    return render(request, 'boards/post_form.html', context)


@login_required
def post_edit(request, slug, pk):
    board = _get_board_or_404(slug)
    post = get_object_or_404(Post, pk=pk, board=board)

    if post.author_id != request.user.id and not request.user.is_staff:
        messages.error(request, '본인이 작성한 글만 수정할 수 있습니다.')
        return redirect('boards:post_detail', slug=board.slug, pk=post.pk)

    if request.method == 'POST':
        form = PostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()

            # 체크된 기존 이미지 삭제
            delete_ids = request.POST.getlist('delete_images')
            if delete_ids:
                post.images.filter(id__in=delete_ids).delete()

            skipped = _save_post_images(post, request.FILES.getlist('images'))
            if skipped:
                messages.warning(request, '다음 파일은 업로드되지 않았습니다: ' + ', '.join(skipped))
            messages.success(request, '글이 수정되었습니다.')
            return redirect('boards:post_detail', slug=board.slug, pk=post.pk)
    else:
        form = PostForm(instance=post)

    context = {
        'board': board,
        'form': form,
        'post': post,
        'max_image_count': MAX_UPLOAD_IMAGE_COUNT,
        'page_title': f'글수정 - {board.name} - 독존',
    }
    return render(request, 'boards/post_form.html', context)


@login_required
def post_delete(request, slug, pk):
    board = _get_board_or_404(slug)
    post = get_object_or_404(Post, pk=pk, board=board)

    if post.author_id != request.user.id and not request.user.is_staff:
        messages.error(request, '본인이 작성한 글만 삭제할 수 있습니다.')
        return redirect('boards:post_detail', slug=board.slug, pk=post.pk)

    if request.method == 'POST':
        author_id = post.author_id
        post.delete()
        # 2026-09-24: 글 삭제 시 글쓴이 포인트 -3 (관리자가 지워도 글쓴이에게서 차감, 0 미만으로는 안 내려감)
        User.objects.filter(pk=author_id).update(
            points=Greatest(F('points') - POINTS_POST_DELETE, Value(0))
        )
        messages.success(request, f'글이 삭제되었습니다. (포인트 -{POINTS_POST_DELETE}점)')
        return redirect('boards:post_list', slug=board.slug)

    context = {
        'board': board,
        'post': post,
        'points_post_delete': POINTS_POST_DELETE,
        'page_title': f'글삭제 확인 - {board.name} - 독존',
    }
    return render(request, 'boards/post_confirm_delete.html', context)


@login_required
@require_POST
def comment_add(request, slug, pk):
    """댓글 작성. (9단계) 목록/상세의 댓글수 뱃지를 실데이터로 채우기 위한 기능입니다."""
    board = _get_board_or_404(slug)
    post = get_object_or_404(Post, pk=pk, board=board)

    # 2026-09-25: 댓글은 진영 제한 없음 (로그인은 @login_required로 이미 확인)
    form = CommentForm(request.POST)
    if form.is_valid():
        Comment.objects.create(post=post, author=request.user, content=form.cleaned_data['content'])
        User.objects.filter(pk=request.user.id).update(points=F('points') + POINTS_COMMENT_WRITE)
        messages.success(request, '댓글이 등록되었습니다.')
    else:
        for error in form.errors.get('content', []):
            messages.error(request, error)

    return redirect('boards:post_detail', slug=board.slug, pk=post.pk)


@login_required
@require_POST
def comment_delete(request, slug, pk, comment_pk):
    board = _get_board_or_404(slug)
    post = get_object_or_404(Post, pk=pk, board=board)
    comment = get_object_or_404(Comment, pk=comment_pk, post=post)

    if comment.author_id != request.user.id and not request.user.is_staff:
        messages.error(request, '본인이 작성한 댓글만 삭제할 수 있습니다.')
        return redirect('boards:post_detail', slug=board.slug, pk=post.pk)

    comment.delete()
    messages.success(request, '댓글이 삭제되었습니다.')
    return redirect('boards:post_detail', slug=board.slug, pk=post.pk)


def _add_points(user_id, delta):
    """포인트 증감. 0점 밑으로는 내려가지 않습니다."""
    if delta >= 0:
        User.objects.filter(pk=user_id).update(points=F('points') + delta)
    else:
        User.objects.filter(pk=user_id).update(points=Greatest(F('points') + delta, Value(0)))


def _post_vote(request, slug, pk, kind):
    """게시글 추천(화력)/반대 공통 처리 (2026-09-25).

    - 추천: 글쓴이 +1, 반대: 글쓴이 -1
    - 같은 버튼을 다시 누르면 취소(포인트도 되돌림)
    - 추천과 반대는 동시에 못 함: 반대 상태에서 추천을 누르면 반대가 취소되고 추천으로 바뀜 (반대도 마찬가지)
    - 본인 글에는 추천/반대 불가 (포인트 셀프 적립 방지)
    """
    board = _get_board_or_404(slug)
    post = get_object_or_404(Post, pk=pk, board=board)
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    if post.author_id == request.user.id:
        message = '본인 글에는 추천/반대를 할 수 없습니다.'
        if is_ajax:
            return JsonResponse({'error': message}, status=400)
        messages.info(request, message)
        return redirect('boards:post_detail', slug=board.slug, pk=post.pk)

    like = PostLike.objects.filter(post=post, user=request.user).first()
    dislike = PostDislike.objects.filter(post=post, user=request.user).first()

    if kind == 'like':
        if like:
            like.delete()
            _add_points(post.author_id, -POINTS_LIKE_RECEIVED)
        else:
            if dislike:
                dislike.delete()
                _add_points(post.author_id, POINTS_DISLIKE_RECEIVED)
            PostLike.objects.create(post=post, user=request.user)
            _add_points(post.author_id, POINTS_LIKE_RECEIVED)
    else:
        if dislike:
            dislike.delete()
            _add_points(post.author_id, POINTS_DISLIKE_RECEIVED)
        else:
            if like:
                like.delete()
                _add_points(post.author_id, -POINTS_LIKE_RECEIVED)
            PostDislike.objects.create(post=post, user=request.user)
            _add_points(post.author_id, -POINTS_DISLIKE_RECEIVED)

    if is_ajax:
        return JsonResponse({
            'liked': PostLike.objects.filter(post=post, user=request.user).exists(),
            'disliked': PostDislike.objects.filter(post=post, user=request.user).exists(),
            'like_count': post.likes.count(),
            'dislike_count': post.dislikes.count(),
        })
    return redirect('boards:post_detail', slug=board.slug, pk=post.pk)


@login_required
@require_POST
def like_toggle(request, slug, pk):
    """추천(화력) 토글. 글쓴이 +1 (2026-09-25: 반대와 함께 _post_vote로 통합)"""
    return _post_vote(request, slug, pk, 'like')


@login_required
@require_POST
def dislike_toggle(request, slug, pk):
    """반대 토글. 글쓴이 -1 (2026-09-25)"""
    return _post_vote(request, slug, pk, 'dislike')


@login_required
@require_POST
def comment_vote(request, slug, pk, comment_pk):
    """댓글 추천(+1)/반대(-1) 토글 (2026-09-25). POST value=up|down.
    규칙은 게시글과 같습니다(다시 누르면 취소, 추천↔반대 전환, 본인 댓글 불가)."""
    board = _get_board_or_404(slug)
    post = get_object_or_404(Post, pk=pk, board=board)
    comment = get_object_or_404(Comment, pk=comment_pk, post=post)
    back = redirect(f"{reverse('boards:post_detail', args=[board.slug, post.pk])}#comment-{comment.pk}")

    value = {'up': CommentVote.UP, 'down': CommentVote.DOWN}.get(request.POST.get('value'))
    if value is None:
        return back
    if comment.author_id == request.user.id:
        messages.info(request, '본인 댓글에는 추천/반대를 할 수 없습니다.')
        return back

    points_for = {CommentVote.UP: POINTS_COMMENT_LIKE_RECEIVED, CommentVote.DOWN: -POINTS_COMMENT_DISLIKE_RECEIVED}
    vote = CommentVote.objects.filter(comment=comment, user=request.user).first()
    if vote:
        _add_points(comment.author_id, -points_for[vote.value])  # 기존 것 되돌리기
        if vote.value == value:
            vote.delete()  # 같은 버튼 다시 누름 = 취소
            return back
        vote.value = value
        vote.save(update_fields=['value'])
    else:
        CommentVote.objects.create(comment=comment, user=request.user, value=value)
    _add_points(comment.author_id, points_for[value])
    return back
