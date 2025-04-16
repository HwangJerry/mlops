# 0. python 개발환경 세팅
> poetry와 pyenv를 이용하여 환경을 구축합니다.
0. `pyenv install 3.10.13` # (원하는 python 버전 설치)
1. `pyenv local 3.10.13` # 프로젝트 별 python 버전 고정 (.python-version 파일 생성)
2. `poetry init --name my-project --dependency fastapi --no-interaction` # pyproject.toml 생성 (requirements.txt 상위버전)
3. `poetry env use $(pyenv which python)` # poetry 가상환경 사용
4. `poetry add fastapi uvicorn torch` # install 말고 add로 해야 pyproject.toml 자동 관리됨

# 1. FastAPI를 활용한 ML 서버 구독
`poetry run uvicorn app.main:app --reload` # fastAPI 로컬 서버 구동 완료

# 2. Dockerize
1. backend.Dockerfile을 root 경로에 작성
2. `docker build -t mlops-app:latest -f backend.Dockerfile .` # Dockerfile이 있는 경로에서 수행 (build context를 .로 선언했으므로)
3. `docker run -d -p 8000:8000 --name mlops-backend mlops-app:latest`
위 과정 거치고 http://localhost:8000/docs 접속해서 API Test 수행

# 3. MinIO; Model Repository 구축
1. `kubectl apply -f minio.yaml` # 로컬에 model repository 구축

# 4. Local Docker registry 구축
1. `kubectl apply -f docker-registry.yaml` # 로컬에 docker registry 구축