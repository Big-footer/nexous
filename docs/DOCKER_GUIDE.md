# NEXOUS Docker 가이드

## 🐳 빠른 시작

### 1. 이미지 빌드
```bash
docker build -t nexous:latest .
```

### 2. 컨테이너 실행
```bash
# Help 확인
docker run --rm nexous:latest --help

# 환경 변수와 함께 실행
docker run --rm \
  -e OPENAI_API_KEY="sk-..." \
  -v $(pwd)/outputs:/app/outputs \
  nexous:latest run example.yaml
```

---

## 📦 Docker Compose 사용

### 기본 실행
```bash
# 빌드 및 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

### 개발 모드
```bash
# 개발 서비스 실행 (코드 hot-reload)
docker-compose run --rm nexous-dev bash
```

---

## 🔧 고급 사용법

### 환경 변수 설정

```.env` 파일 생성:
```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

Docker Compose에서 자동으로 로드됩니다.

### 볼륨 마운트

**프로젝트 파일:**
```bash
docker run --rm \
  -v $(pwd)/projects:/app/projects \
  nexous:latest run /app/projects/my-project.yaml
```

**출력 결과:**
```bash
docker run --rm \
  -v $(pwd)/outputs:/app/outputs \
  nexous:latest run example.yaml
```

### 인터랙티브 모드
```bash
# Bash 쉘 접근
docker run -it --rm nexous:latest bash

# Python 인터프리터
docker run -it --rm nexous:latest python
```

---

## 🚀 GitHub Container Registry 사용

### 이미지 Pull
```bash
docker pull ghcr.io/big-footer/nexous:latest
```

### 이미지 실행
```bash
docker run --rm \
  -e OPENAI_API_KEY="sk-..." \
  ghcr.io/big-footer/nexous:latest --help
```

---

## 🔍 문제 해결

### 이미지 크기 확인
```bash
docker images nexous
```

### 컨테이너 로그 확인
```bash
docker logs <container_id>
```

### 캐시 제거 후 재빌드
```bash
docker build --no-cache -t nexous:latest .
```

### 권한 문제
컨테이너는 non-root 사용자(nexous)로 실행됩니다. 
호스트의 볼륨 권한 확인:
```bash
# 출력 디렉토리 권한 설정
chmod -R 777 outputs/
```

---

## 📊 모니터링

### 리소스 사용량
```bash
docker stats nexous
```

### Health Check
```bash
docker inspect --format='{{.State.Health.Status}}' nexous
```

---

## 🔒 보안 Best Practices

### 1. API 키 관리
- ❌ Dockerfile에 직접 입력 금지
- ✅ `.env` 파일 사용
- ✅ 환경 변수로 전달

### 2. 이미지 스캔
```bash
# Trivy로 취약점 스캔
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image nexous:latest
```

### 3. Non-root 실행
이미지는 기본적으로 non-root 사용자로 실행됩니다.

---

## 📝 예제

### Example 1: 단일 프로젝트 실행
```bash
docker run --rm \
  --env-file .env \
  -v $(pwd)/projects/example.yaml:/app/input.yaml \
  -v $(pwd)/outputs:/app/outputs \
  nexous:latest run /app/input.yaml
```

### Example 2: 개발 환경
```bash
docker-compose run --rm nexous-dev bash
# 컨테이너 안에서
pytest -v
python -m nexous.cli.main --help
```

### Example 3: CI/CD 통합
```yaml
# GitHub Actions
- name: Run NEXOUS in Docker
  run: |
    docker run --rm \
      -e OPENAI_API_KEY=${{ secrets.OPENAI_API_KEY }} \
      nexous:latest run example.yaml
```
