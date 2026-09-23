document.addEventListener('DOMContentLoaded', function () {
    // 모바일 GNB(햄버거 메뉴) 열고 닫기
    var toggleBtn = document.querySelector('.gnb-toggle');
    var gnbList = document.getElementById('gnb-list');

    if (toggleBtn && gnbList) {
        toggleBtn.addEventListener('click', function () {
            var isOpen = gnbList.classList.toggle('is-open');
            toggleBtn.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
    }

    // ---------------- 회원가입 폼 ----------------
    var signupForm = document.getElementById('signup-form');
    if (signupForm) {
        var agreeCheckbox = document.getElementById('id_agree_terms');
        var termsError = document.getElementById('terms-js-error');

        // 아이디/닉네임/이메일: 입력창을 벗어나면(blur) DB에서 바로 중복 검사
        var dupFields = [
            {
                input: document.getElementById('id_username'),
                result: document.getElementById('username-check-result'),
                url: signupForm.getAttribute('data-check-username-url'),
                param: 'username',
                message: '이미 사용 중인 아이디입니다.',
            },
            {
                input: document.getElementById('id_nickname'),
                result: document.getElementById('nickname-check-result'),
                url: signupForm.getAttribute('data-check-nickname-url'),
                param: 'nickname',
                message: '이미 사용 중인 닉네임입니다.',
            },
            {
                input: document.getElementById('id_email'),
                result: document.getElementById('email-check-result'),
                url: signupForm.getAttribute('data-check-email-url'),
                param: 'email',
                message: '이미 사용 중인 이메일입니다.',
            },
        ];

        // 값이 바뀌면 이전 검사 결과는 신뢰할 수 없으니 일단 지워둠
        dupFields.forEach(function (field) {
            if (!field.input) return;
            field.checkedValue = null;
            field.isDuplicate = false;
            field.input.addEventListener('input', function () {
                field.checkedValue = null;
                field.result.hidden = true;
                field.result.textContent = '';
            });
        });

        // 하나의 필드를 실제로 서버에 물어보고 결과를 반영하는 함수
        function checkField(field) {
            var value = field.input ? field.input.value.trim() : '';
            if (!value) {
                field.checkedValue = value;
                field.isDuplicate = false;
                field.result.hidden = true;
                return Promise.resolve();
            }
            return fetch(field.url + '?' + field.param + '=' + encodeURIComponent(value))
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    field.checkedValue = value;
                    field.isDuplicate = !data.available;
                    if (field.isDuplicate) {
                        field.result.textContent = field.message;
                        field.result.hidden = false;
                    } else {
                        field.result.hidden = true;
                        field.result.textContent = '';
                    }
                })
                .catch(function () {
                    // 네트워크 오류 시에는 일단 통과시키고, 최종 확인은 서버 제출 시 다시 한번 검사됨
                    field.checkedValue = value;
                    field.isDuplicate = false;
                    field.result.hidden = true;
                });
        }

        dupFields.forEach(function (field) {
            if (!field.input) return;
            field.input.addEventListener('blur', function () {
                checkField(field);
            });
        });

        signupForm.addEventListener('submit', function (e) {
            e.preventDefault();

            // 약관 동의 체크
            if (agreeCheckbox && !agreeCheckbox.checked) {
                if (termsError) termsError.hidden = false;
                agreeCheckbox.focus();
                return;
            }
            if (termsError) termsError.hidden = true;

            // 아이디/닉네임/이메일: 아직 검사 안 했거나 값이 바뀐 필드는 다시 검사
            var pending = dupFields
                .filter(function (field) { return field.input; })
                .map(function (field) {
                    var value = field.input.value.trim();
                    if (field.checkedValue === value) {
                        return Promise.resolve();
                    }
                    return checkField(field);
                });

            Promise.all(pending).then(function () {
                var firstDuplicate = dupFields.find(function (field) {
                    return field.input && field.isDuplicate;
                });
                if (firstDuplicate) {
                    firstDuplicate.input.focus();
                    return;
                }
                // 문제 없으면 실제로 제출 (form.submit()은 submit 이벤트를 다시 발생시키지 않음)
                signupForm.submit();
            });
        });
    }

    // ---------------- 게시글 에디터 (Quill) ----------------
    // 8단계 요청: 글쓰기에 에디터 추가 + 이미지 드래그 앤 드롭 삽입.
    var contentField = document.getElementById('id_content');
    if (contentField && window.Quill) {
        var postForm = contentField.closest('form');
        var uploadUrl = postForm ? postForm.getAttribute('data-image-upload-url') : null;
        var csrfInput = postForm ? postForm.querySelector('[name=csrfmiddlewaretoken]') : null;

        // 실제 제출용 textarea는 화면에서 숨기고, 그 자리에 에디터를 붙입니다.
        contentField.style.display = 'none';
        var editorEl = document.createElement('div');
        editorEl.className = 'quill-editor';
        contentField.parentNode.insertBefore(editorEl, contentField);

        var quill = new Quill(editorEl, {
            theme: 'snow',
            placeholder: '내용을 입력하세요...',
            modules: {
                toolbar: [
                    [{ header: [1, 2, 3, false] }],
                    ['bold', 'italic', 'underline', 'strike'],
                    [{ list: 'ordered' }, { list: 'bullet' }],
                    ['blockquote', 'link', 'image'],
                    ['clean'],
                ],
            },
        });

        // 글수정 화면: 기존 내용을 에디터에 미리 채워넣기
        if (contentField.value) {
            quill.root.innerHTML = contentField.value;
        }

        // 파일 하나를 서버에 업로드하고, 성공하면 에디터 커서 위치에 이미지를 삽입
        function uploadImageToEditor(file) {
            if (!uploadUrl || !file || file.type.indexOf('image/') !== 0) return;

            var formData = new FormData();
            formData.append('image', file);

            fetch(uploadUrl, {
                method: 'POST',
                headers: csrfInput ? { 'X-CSRFToken': csrfInput.value } : {},
                body: formData,
            })
                .then(function (res) { return res.json(); })
                .then(function (data) {
                    if (data.url) {
                        var range = quill.getSelection(true) || { index: quill.getLength() };
                        quill.insertEmbed(range.index, 'image', data.url, 'user');
                        quill.setSelection(range.index + 1);
                    } else if (data.error) {
                        window.alert(data.error);
                    }
                })
                .catch(function () {
                    window.alert('이미지 업로드에 실패했습니다. 잠시 후 다시 시도해주세요.');
                });
        }

        // 에디터 영역에 사진을 드래그해서 놓으면 업로드 + 삽입
        quill.root.addEventListener('drop', function (e) {
            if (e.dataTransfer && e.dataTransfer.files && e.dataTransfer.files.length) {
                var hasImage = Array.prototype.some.call(e.dataTransfer.files, function (f) {
                    return f.type.indexOf('image/') === 0;
                });
                if (hasImage) {
                    e.preventDefault();
                    Array.prototype.forEach.call(e.dataTransfer.files, uploadImageToEditor);
                }
            }
        });

        // 클립보드에서 이미지를 붙여넣는 경우도 동일하게 처리
        quill.root.addEventListener('paste', function (e) {
            if (e.clipboardData && e.clipboardData.files && e.clipboardData.files.length) {
                var hasImage = Array.prototype.some.call(e.clipboardData.files, function (f) {
                    return f.type.indexOf('image/') === 0;
                });
                if (hasImage) {
                    e.preventDefault();
                    Array.prototype.forEach.call(e.clipboardData.files, uploadImageToEditor);
                }
            }
        });

        // 툴바의 이미지 버튼: 기본 동작(URL 입력) 대신 파일 선택창을 띄워서 업로드
        quill.getModule('toolbar').addHandler('image', function () {
            var input = document.createElement('input');
            input.setAttribute('type', 'file');
            input.setAttribute('accept', 'image/jpeg,image/png,image/gif,image/webp');
            input.addEventListener('change', function () {
                if (input.files && input.files[0]) uploadImageToEditor(input.files[0]);
            });
            input.click();
        });

        // 폼 제출 직전에 에디터 내용을 실제 textarea 값으로 옮겨줌
        if (postForm) {
            postForm.addEventListener('submit', function () {
                contentField.value = quill.root.innerHTML;
            });
        }
    }

    // ---------------- 1:1 일기토 카운트다운 ----------------
    // 9단계: 서버가 내려준 "마감까지 남은 초"를 1초씩 줄여서 보여줍니다.
    // (서버 값이 진짜 기준이라, 페이지를 새로고침하면 다시 정확한 값으로 맞춰집니다)
    document.querySelectorAll('[data-duel-countdown]').forEach(function (el) {
        var remaining = parseInt(el.getAttribute('data-duel-countdown'), 10) || 0;
        var strong = el.querySelector('strong');
        if (!strong) return;

        var timer = setInterval(function () {
            remaining -= 1;
            if (remaining <= 0) {
                clearInterval(timer);
                remaining = 0;
                el.textContent = '투표가 마감되었습니다. 결과를 확인해보세요.';
                return;
            }
            var h = Math.floor(remaining / 3600);
            var m = Math.floor((remaining % 3600) / 60);
            var s = remaining % 60;
            strong.textContent = h > 0
                ? (h + '시간 ' + m + '분 ' + s + '초')
                : (m > 0 ? (m + '분 ' + s + '초') : (s + '초'));
        }, 1000);
    });

    // ---------------- 가입자 진영 비율 바 ----------------
    // 0%에서 실제 값까지 애니메이션으로 채우기
    var ratioFills = document.querySelectorAll('.party-ratio-fill');
    if (ratioFills.length) {
        requestAnimationFrame(function () {
            requestAnimationFrame(function () {
                ratioFills.forEach(function (fill) {
                    var target = fill.getAttribute('data-target-width');
                    if (target) {
                        fill.style.width = target + '%';
                    }
                });
            });
        });
    }
});
