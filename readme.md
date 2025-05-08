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

# K8s 환경의 Harbor(HTTPS) 사용 가이드

## 1. Harbor 소개

Harbor는 CNCF의 졸업 프로젝트로, 기업용 컨테이너 이미지 레지스트리입니다. 다음과 같은 주요 기능을 제공합니다:

- RBAC(역할 기반 접근 제어)
- LDAP/AD 통합
- 컨테이너 이미지 취약점 스캐닝 (Trivy 통합)
- 컨테이너 이미지 서명 및 검증
- 멀티 테넌시
- 이미지 복제
- **Helm 차트 저장소** (ChartMuseum 통합)
- API 및 웹 인터페이스

## 2. Harbor 접속 방법

Harbor는 HTTPS를 통해 접근할 수 있으며, 자체 서명된 인증서를 사용합니다.

### 웹 UI 접속
- URL: https://localhost:30445
- 사용자: admin
- 비밀번호: Harbor12345

### Docker CLI로 이미지 Push/Pull

```bash
# 1. Docker에 Harbor 인증서 신뢰 설정 (Windows)
# %USERPROFILE%\.docker\certs.d\localhost_30445 디렉토리에 ca.crt 파일 복사

# 2. Harbor 로그인
docker login localhost:30445 -u admin -p Harbor12345

# 3. 이미지 태그 설정
docker tag {이미지명}:{태그} localhost:30445/{프로젝트명}/{이미지명}:{태그}
# 예: docker tag mlops-backend:latest localhost:30445/mlops/mlops-backend:latest

# 4. 이미지 Push
docker push localhost:30445/{프로젝트명}/{이미지명}:{태그}
# 예: docker push localhost:30445/mlops/mlops-backend:latest

# 5. 이미지 Pull
docker pull localhost:30445/{프로젝트명}/{이미지명}:{태그}
# 예: docker pull localhost:30445/mlops/mlops-backend:latest
```

## 3. Helm Charts 관리

Harbor는 ChartMuseum을 통해 Helm 차트 저장소 기능을 제공합니다.

### Harbor UI를 통한 Helm 차트 관리

1. Harbor UI에 로그인
2. 프로젝트 생성 또는 선택
3. "Helm Charts" 탭으로 이동
4. "UPLOAD" 버튼을 클릭하여 Helm 차트(.tgz) 업로드

### Helm CLI를 통한 관리

```bash
# 1. Harbor에 Helm 저장소 추가
helm repo add myrepo https://localhost:30445/chartrepo/{프로젝트명} --username admin --password Harbor12345 --insecure-skip-tls-verify

# 2. 저장소 업데이트
helm repo update

# 3. 차트 패키징
helm package ./mychart

# 4. 차트 Push (OCI 저장소로 사용 시)
helm push mychart-0.1.0.tgz oci://localhost:30445/{프로젝트명}

# 5. 차트 Pull (OCI 저장소로 사용 시)
helm pull oci://localhost:30445/{프로젝트명}/mychart --version 0.1.0

# 6. 차트 설치
helm install myrelease myrepo/mychart
```

## 4. ArgoCD와 Harbor 연동

ArgoCD에 Harbor를 Helm 차트 저장소로 추가하여 GitOps 워크플로우를 구현할 수 있습니다.

### 1. ArgoCD에 저장소 추가

ArgoCD UI 또는 CLI를 통해 Harbor Helm 저장소를 추가합니다:

```bash
argocd repo add https://localhost:30445/chartrepo/{프로젝트명} --name harbor-helm --username admin --password Harbor12345 --type helm --insecure-skip-tls-verify
```

### 2. ArgoCD 애플리케이션 생성

```yaml
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: my-app
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://localhost:30445/chartrepo/{프로젝트명}
    targetRevision: 0.1.0
    chart: mychart
    helm:
      values: |
        replicaCount: 2
  destination:
    server: https://kubernetes.default.svc
    namespace: default
  syncPolicy:
    automated:
      prune: true
      selfHeal: true
```

## 5. 트러블슈팅

### 인증서 관련 이슈

Harbor는 자체 서명된 인증서를 사용합니다. 클라이언트에서 인증서 경고가 발생하는 경우:

1. Docker: `%USERPROFILE%\.docker\certs.d\localhost_30445` 디렉토리에 `ca.crt` 파일 복사
2. Helm: `--insecure-skip-tls-verify` 플래그 사용
3. Curl: `-k` 또는 `--insecure` 플래그 사용

### 권한 이슈

1. 프로젝트 접근 권한이 있는지 확인
2. 사용자의 RBAC 권한 확인
3. 로봇 계정 생성 및 사용 고려

# Harbor 설치 및 사용 가이드

## 설치 정보
Harbor가 성공적으로 설치되었습니다. 다음 URL로 접근할 수 있습니다:
- HTTP: http://localhost:30085
- HTTPS: https://harbor.local:30445

기본 계정 정보:
- 사용자명: admin
- 비밀번호: Harbor12345

## 접속 설정
1. 호스트 파일 수정 (Windows의 경우 C:\Windows\System32\drivers\etc\hosts):
   ```
   127.0.0.1 harbor.local
   ```

## Docker 사용법
Docker로 이미지를 Push하기 위한 설정:

1. 인증서 신뢰 설정 (Windows):
   ```powershell
   mkdir -p $env:USERPROFILE\.docker\certs.d\harbor.local:30445
   Copy-Item .\tls.crt $env:USERPROFILE\.docker\certs.d\harbor.local:30445\ca.crt
   ```

2. Docker 로그인:
   ```
   docker login harbor.local:30445 -u admin -p Harbor12345
   ```

3. 이미지 태그 및 푸시:
   ```
   docker tag nginx:latest harbor.local:30445/library/nginx:latest
   docker push harbor.local:30445/library/nginx:latest
   ```

## Helm 차트 저장소 사용법
1. Harbor에 로그인하여 Helm Chart 프로젝트 생성

2. Helm 저장소 추가:
   ```
   helm repo add myrepo https://harbor.local:30445/chartrepo/library --username admin --password Harbor12345 --ca-file ./tls.crt
   ```

3. Helm 차트 패키징 및 푸시:
   ```
   helm package ./mychart
   helm push mychart-0.1.0.tgz myrepo
   ```

## OCI 저장소로 사용하기
Helm OCI 형식으로 차트 푸시:
```
helm registry login harbor.local:30445 -u admin -p Harbor12345
helm package ./mychart
helm push mychart-0.1.0.tgz oci://harbor.local:30445/library/
```

## Harbor UI 기능
- 프로젝트 관리
- 사용자 및 역할 관리
- 취약점 스캔
- 복제 설정
- 로그 관리
- 시스템 설정