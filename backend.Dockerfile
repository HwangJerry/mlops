FROM python:3.10.13-slim

# 기본 설정
WORKDIR /code

# pip 업그레이드
RUN python -m pip install --upgrade pip

# Poetry 설치
RUN pip install poetry

# Poetry 기본 설정 (가상환경 off)
RUN poetry config virtualenvs.create false

# pyproject.toml 및 잠금 파일 복사
COPY pyproject.toml poetry.lock* /code/

# app 디렉토리 복사 (pyproject.toml에서 모듈 참조 시 필요)
COPY ./app /code/app

# 모델 디렉토리 생성
RUN mkdir -p /code/models/t5-small

# 의존성 설치 (루트 패키지는 제외)
RUN poetry install --no-root --no-interaction --no-ansi --only main

# 포트 오픈
EXPOSE 80

# 명확한 실행 경로 명시
ENTRYPOINT ["uvicorn", "app.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000"]