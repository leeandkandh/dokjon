# 독존(dokjon) 배포 가이드 — Git 저장 → AWS Ubuntu → www.dokjon.com

이 문서는 로드맵 13(Git) ~ 15(도메인/운영) 단계를 실제로 진행하는 순서입니다.
터미널 명령은 위에서 아래로 그대로 따라 하면 됩니다. `<이렇게 꺾쇠 괄호>`로 표시한 부분만
실제 값으로 바꾸세요.

---

## 0. 지금 상태 요약

- 로컬 PC(`C:\dev\dokjon`)에 git 저장소는 이미 초기화되어 있지만(`.git` 폴더 있음), 아직
  GitHub 같은 원격 저장소에는 연결되어 있지 않습니다.
- `config/settings.py`는 이번에 `.env`의 `SECRET_KEY` / `DEBUG` / `ALLOWED_HOSTS` /
  `CSRF_TRUSTED_ORIGINS` 값으로 운영 모드로 전환되도록 이미 수정해뒀습니다. 로컬 개발
  PC에서는 `.env`에 이 값들을 넣지 않으면 지금처럼 그대로 개발 모드로 동작합니다.
- `requirements.txt`에 `gunicorn`, `whitenoise`를 추가했습니다.
- `.env.example`(Git에 올라가는 견본)에 운영에 필요한 키 목록을 정리해뒀습니다.

---

## 1. Git — 로컬 커밋 + GitHub 원격 저장소 연결

### 1-1. 로컬에서 지금까지 작업을 커밋

PowerShell(또는 Git Bash)에서 `C:\dev\dokjon` 폴더로 이동한 뒤:

```powershell
cd C:\dev\dokjon
git status          # 뭐가 바뀌었는지 먼저 확인
git add .
git commit -m "9단계: 포인트/댓글/추천/일기토 + 14단계 배포 준비(운영 설정)"
```

`git status`에서 `.env`, `venv/`, `db.sqlite3`, `staticfiles/`, `media/`, `__pycache__/`가
목록에 안 보이면 `.gitignore`가 제대로 작동하는 것입니다(정상).

> git이 사용자 정보를 처음 묻는다면(“Please tell me who you are”):
> ```powershell
> git config --global user.name "본인 이름"
> git config --global user.email "본인 이메일"
> ```

### 1-2. GitHub에 빈 저장소 만들기

1. https://github.com → 우측 상단 `+` → **New repository**
2. Repository name: `dokjon` (또는 원하는 이름)
3. **Public/Private** 원하는 대로 선택 — **단, `.env`는 이미 gitignore되어 있어서 비밀번호가
   올라가지 않으니 Private이 아니어도 안전합니다.**
4. "Add a README", "Add .gitignore" 체크박스는 **모두 체크 해제**(이미 로컬에 있음) →
   **Create repository**

### 1-3. 로컬 저장소를 GitHub에 연결하고 push

GitHub이 만들어준 빈 저장소 페이지에 나오는 주소를 그대로 쓰세요 (예시):

```powershell
git remote add origin https://github.com/<깃허브아이디>/dokjon.git
git branch -M main
git push -u origin main
```

이후로는 새로 작업할 때마다:
```powershell
git add .
git commit -m "설명"
git push
```

---

## 2. AWS — EC2(Ubuntu) 인스턴스 준비

### 2-1. 인스턴스 생성

1. AWS 콘솔 → **EC2** → **Launch instance**
2. Name: `dokjon-server`
3. AMI(운영체제): **Ubuntu Server 24.04 LTS** (또는 22.04 LTS)
4. Instance type: 처음 시작이면 `t3.small`(회원 적고 트래픽 적으면 `t2.micro`/`t3.micro`도 가능,
   프리티어 대상은 `t2.micro`/`t3.micro`)
5. Key pair: **Create new key pair** → 이름 지정 → `.pem` 파일 다운로드 (SSH 접속에 필요, 잘
   보관)
6. **Network settings → Edit** → 보안 그룹 인바운드 규칙에 아래 3개 추가:
   - SSH (22) — My IP (본인 IP만 허용 권장)
   - HTTP (80) — Anywhere (0.0.0.0/0)
   - HTTPS (443) — Anywhere (0.0.0.0/0)
7. Storage: 기본 8GB로는 빠듯할 수 있어 20GB 정도로 늘리는 걸 권장
8. **Launch instance**

### 2-2. 고정 IP(Elastic IP) 연결

인스턴스를 껐다 켜면 퍼블릭 IP가 바뀌어서 도메인 연결이 끊깁니다. 반드시 고정 IP를 답니다.

1. EC2 콘솔 → **Elastic IPs** → **Allocate Elastic IP address** → Allocate
2. 방금 만든 EIP 선택 → **Actions → Associate Elastic IP address** → 위에서 만든 인스턴스 선택
   → Associate
3. 이제 이 IP(`<EC2_고정IP>`)가 서버 주소입니다. 아래에서 계속 이 값을 씁니다.

### 2-3. SSH 접속

```bash
# .pem 파일이 있는 폴더에서
chmod 400 dokjon-key.pem   # Mac/Linux. Windows는 속성에서 읽기전용으로 바꿔도 되고, 보통은 그냥 접속됩니다
ssh -i dokjon-key.pem ubuntu@<EC2_고정IP>
```

**아래 3~7단계는 전부 이 SSH 접속 상태(서버 안)에서 실행합니다.**

---

## 3. 서버 기본 패키지 설치

```bash
sudo apt update && sudo apt upgrade -y

sudo apt install -y python3-pip python3-venv python3-dev \
    postgresql postgresql-contrib libpq-dev \
    nginx git curl
```

---

## 4. PostgreSQL 데이터베이스 만들기

```bash
sudo -u postgres psql
```

psql 프롬프트(`postgres=#`)에서:

```sql
CREATE DATABASE dokjon_db;
CREATE USER dokjon_user WITH PASSWORD '<강력한_비밀번호>';
ALTER ROLE dokjon_user SET client_encoding TO 'utf8';
ALTER ROLE dokjon_user SET default_transaction_isolation TO 'read committed';
ALTER ROLE dokjon_user SET timezone TO 'Asia/Seoul';
GRANT ALL PRIVILEGES ON DATABASE dokjon_db TO dokjon_user;
\q
```

(로컬 PC의 `.env`와는 별개로, 서버 전용 DB 계정을 새로 만드는 걸 권장합니다. `postgres`
슈퍼유저를 앱에서 직접 쓰지 않는 게 안전합니다.)

---

## 5. 프로젝트 배포

```bash
cd ~
git clone https://github.com/<깃허브아이디>/dokjon.git
cd dokjon

python3 -m venv venv
source venv/bin/activate

pip install --upgrade pip
pip install -r requirements.txt
```

### 5-1. 운영용 `.env` 작성

```bash
cp .env.example .env
nano .env
```

아래처럼 채웁니다 (SECRET_KEY는 아래 명령으로 새로 생성):

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

`.env` 최종 내용 예시:
```
DB_NAME=dokjon_db
DB_USER=dokjon_user
DB_PASSWORD=<4단계에서 만든 비밀번호>
DB_HOST=localhost
DB_PORT=5432

SECRET_KEY=<방금 생성한 랜덤 값>
DEBUG=False
ALLOWED_HOSTS=dokjon.com,www.dokjon.com,<EC2_고정IP>
CSRF_TRUSTED_ORIGINS=https://dokjon.com,https://www.dokjon.com
```

### 5-2. 마이그레이션 / 정적파일 / 관리자 계정

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 5-3. media 폴더 권한

```bash
mkdir -p media
sudo chown -R ubuntu:www-data ~/dokjon
```

---

## 6. gunicorn을 systemd 서비스로 등록 (서버 재부팅해도 자동 실행)

```bash
sudo nano /etc/systemd/system/dokjon.service
```

아래 내용을 그대로 붙여넣기 (사용자 이름이 `ubuntu`가 아니면 그에 맞게 수정):

```ini
[Unit]
Description=dokjon gunicorn daemon
After=network.target

[Service]
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/dokjon
ExecStart=/home/ubuntu/dokjon/venv/bin/gunicorn \
    --access-logfile - \
    --workers 3 \
    --bind unix:/home/ubuntu/dokjon/dokjon.sock \
    config.wsgi:application

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl start dokjon
sudo systemctl enable dokjon
sudo systemctl status dokjon   # active (running) 확인
```

---

## 7. nginx 리버스 프록시 설정

```bash
sudo nano /etc/nginx/sites-available/dokjon
```

```nginx
server {
    listen 80;
    server_name dokjon.com www.dokjon.com;

    client_max_body_size 10M;   # 게시글 첨부 이미지(장당 5MB) 업로드 여유

    location /static/ {
        alias /home/ubuntu/dokjon/staticfiles/;
    }

    location /media/ {
        alias /home/ubuntu/dokjon/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:/home/ubuntu/dokjon/dokjon.sock;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/dokjon /etc/nginx/sites-enabled/
sudo nginx -t     # 문법 오류 없는지 확인 ("syntax is ok" 나와야 함)
sudo systemctl restart nginx
```

이 시점에서 브라우저로 `http://<EC2_고정IP>`에 접속하면 (도메인 연결 전이라도) 이미 화면이
떠야 합니다. 안 뜨면 아래 "문제 해결" 참고.

---

## 8. 도메인(dokjon.com) 연결

도메인을 구매한 곳(가비아/후이즈/Route 53 등)의 DNS 관리 화면에서:

| 타입 | 호스트 | 값(Value) |
|---|---|---|
| A | @ (또는 dokjon.com) | `<EC2_고정IP>` |
| A | www | `<EC2_고정IP>` |

저장 후 전파까지 보통 몇 분~1시간 정도 걸립니다(길면 최대 24시간).
`nslookup dokjon.com`(또는 https://www.whatsmydns.net )으로 확인 가능합니다.

---

## 9. SSL 인증서 발급 (https, Let's Encrypt)

DNS가 EC2 IP로 정상 연결된 걸 확인한 뒤:

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d dokjon.com -d www.dokjon.com
```

- 이메일 입력, 약관 동의
- "Redirect HTTP to HTTPS?" 물어보면 **2 (Redirect)** 선택 — http로 들어와도 자동으로
  https로 전환됩니다.

인증서는 90일마다 만료되는데, certbot이 설치하는 타이머가 자동 갱신해줍니다. 확인:
```bash
sudo systemctl status certbot.timer
```

이제 `https://www.dokjon.com`으로 정상 접속되면 배포 완료입니다.

---

## 10. 이후 코드 업데이트 배포 절차

로컬에서 코드 수정 → git push 했다면, 서버에서:

```bash
cd ~/dokjon
source venv/bin/activate
git pull
pip install -r requirements.txt   # 새 패키지가 추가됐을 때만
python manage.py migrate          # 새 마이그레이션이 있을 때만
python manage.py collectstatic --noinput
sudo systemctl restart dokjon
```

---

## 11. 문제 해결(트러블슈팅) 체크리스트

- **502 Bad Gateway**: gunicorn이 안 떠 있음 → `sudo systemctl status dokjon`,
  `sudo journalctl -u dokjon -n 50`로 에러 로그 확인
- **CSS/이미지가 안 뜸**: `collectstatic`을 안 돌렸거나, nginx의 `/static/` alias 경로가
  실제 `staticfiles/` 폴더 경로와 다름
- **"DisallowedHost" 에러**: `.env`의 `ALLOWED_HOSTS`에 접속 도메인이 빠져 있음
- **CSRF 오류(로그인/글쓰기 안 됨)**: `.env`의 `CSRF_TRUSTED_ORIGINS`에 `https://` 포함해서
  정확히 등록했는지 확인
- **정적파일 새 배포 후에도 예전 CSS가 보임**: whitenoise가 파일명에 해시를 붙이므로 보통
  캐시 문제가 없지만, 브라우저 강력 새로고침(Ctrl+Shift+R)으로 확인
- **500 에러인데 원인을 모르겠음**: 급할 때만 서버 `.env`에서 잠깐 `DEBUG=True`로 바꾸고
  재현 → 원인 확인 후 **반드시 다시 False로 되돌리기** (운영에서 DEBUG=True는 보안 위험)

---

## 참고: 나중에 고려하면 좋은 것 (지금 당장 필수는 아님)

- 미디어(업로드 이미지) S3로 이전 — 서버 디스크 용량/백업 이슈 예방
- RDS(관리형 PostgreSQL)로 이전 — DB 백업/장애 대응 자동화
- GitHub Actions로 push 시 자동 배포(CI/CD)
- 로그 모니터링(CloudWatch) / 알림
