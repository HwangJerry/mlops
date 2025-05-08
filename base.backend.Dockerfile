FROM python:3.10.11-slim

WORKDIR /mlops

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# rye 설치
RUN curl -sSf https://rye.astral.sh/get | RYE_INSTALL_OPTION="--yes" bash

# 프로젝트 파일 복사
COPY pyproject.toml requirements.lock ./

# rye를 사용하여 의존성 설치
ENV PATH="/root/.rye/shims:${PATH}"
RUN rye sync

# 가상환경 경로를 환경변수로 설정
ENV VIRTUAL_ENV=/mlops/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"