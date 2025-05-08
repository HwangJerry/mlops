# Harbor 설치 및 HTTPS 연결 가이드

이 가이드는 Kubernetes 클러스터에서 Harbor 레지스트리를 설치하고 HTTPS를 구성하는 방법을 설명합니다.

## 1. 준비 사항

- Kubernetes 클러스터가 구성되어 있어야 함
- Traefik Ingress Controller가 설치되어 있어야 함
- TLS 인증서와 키가 준비되어 있어야 함 (tls.crt, tls.key)

## 2. TLS 인증서 준비

### 인증서 설정 파일 생성

인증서 설정 파일(`openssl.cnf`)에 Harbor 도메인 및 기타 필요한 도메인을 모두 추가:

```
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no

[req_distinguished_name]
CN = fastapi.local

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = fastapi.local
DNS.2 = minio.local
DNS.3 = minio-console.local
DNS.4 = harbor.local
DNS.5 = localhost
IP.1 = 127.0.0.1
```

### 인증서 생성

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout tls.key -out tls.crt -config openssl.cnf
```

### 인증서 확인

```bash
# 인증서의 CN과 SAN을 확인
openssl x509 -in tls.crt -text -noout | findstr "Subject:"
openssl x509 -in tls.crt -text -noout | findstr "DNS"
```

## 3. 볼륨 준비 및 권한 설정

Harbor는 여러 컴포넌트(PostgreSQL, Redis 등)로 구성되며, 각각 특정 권한이 필요합니다.

### 디렉토리 생성 및 권한 설정

```bash
# 기본 디렉토리 생성
sudo mkdir -p /mnt/data/harbor
sudo mkdir -p /mnt/data/harbor/{registry,chartmuseum,jobservice,database,redis,trivy}

# PostgreSQL(database)용 권한 설정 - 보통 UID 999 사용
sudo chown -R 999:999 /mnt/data/harbor/database
sudo chmod -R 700 /mnt/data/harbor/database

# Redis용 권한 설정
sudo chown -R 999:999 /mnt/data/harbor/redis
sudo chmod -R 700 /mnt/data/harbor/redis

# Registry 및 기타 컴포넌트 권한 설정
sudo chown -R 10000:10000 /mnt/data/harbor/registry
sudo chown -R 10000:10000 /mnt/data/harbor/chartmuseum
sudo chown -R 10000:10000 /mnt/data/harbor/jobservice
sudo chown -R 10000:10000 /mnt/data/harbor/trivy
sudo chmod -R 755 /mnt/data/harbor/registry
sudo chmod -R 755 /mnt/data/harbor/chartmuseum
sudo chmod -R 755 /mnt/data/harbor/jobservice
sudo chmod -R 755 /mnt/data/harbor/trivy
```

## 4. Harbor를 위한 Kubernetes 리소스 생성

### Harbor 네임스페이스 생성

```bash
kubectl create namespace harbor
```

### TLS Secret 생성

```bash
# Harbor용 TLS Secret 생성
kubectl create secret tls harbor-tls --cert=./tls.crt --key=./tls.key -n harbor
kubectl create secret tls harbor-ingress --cert=./tls.crt --key=./tls.key -n harbor
```

> **중요**: `harbor-ingress`라는 이름의 Secret이 실제 Ingress에서 사용됩니다.

### PersistentVolume 생성

`harbor-pv.yaml` 파일:

```yaml
apiVersion: v1
kind: PersistentVolume
metadata:
  name: harbor-registry-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  hostPath:
    path: /mnt/data/harbor/registry
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: harbor-chartmuseum-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  hostPath:
    path: /mnt/data/harbor/chartmuseum
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: harbor-jobservice-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  hostPath:
    path: /mnt/data/harbor/jobservice
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: harbor-database-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  hostPath:
    path: /mnt/data/harbor/database
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: harbor-redis-pv
spec:
  capacity:
    storage: 1Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  hostPath:
    path: /mnt/data/harbor/redis
---
apiVersion: v1
kind: PersistentVolume
metadata:
  name: harbor-trivy-pv
spec:
  capacity:
    storage: 5Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: local-storage
  hostPath:
    path: /mnt/data/harbor/trivy
```

PV 적용:

```bash
kubectl apply -f harbor-pv.yaml
```

## 5. Harbor 배포를 위한 values.yaml 파일 설정

`harbor-values.yaml` 파일:

```yaml
expose:
  type: ingress
  tls:
    enabled: true
    secretName: harbor-ingress  # 실제 사용되는 Secret 이름
  ingress:
    hosts:
      core: harbor.local
    annotations:
      kubernetes.io/ingress.class: traefik
    className: traefik

externalURL: https://harbor.local

persistence:
  enabled: true
  resourcePolicy: "keep"
  persistentVolumeClaim:
    registry:
      storageClass: "local-storage"
      size: 5Gi
    chartmuseum:
      storageClass: "local-storage"
      size: 5Gi
    jobservice:
      storageClass: "local-storage"
      size: 1Gi
    database:
      storageClass: "local-storage"
      size: 1Gi
    redis:
      storageClass: "local-storage"
      size: 1Gi
    trivy:
      storageClass: "local-storage"
      size: 5Gi

# Harbor의 기본 관리자 비밀번호 설정
harborAdminPassword: "Harbor12345"

# 다른 구성요소 비밀번호 설정
database:
  password: "db123456"
  maxIdleConns: 100
  maxOpenConns: 900

# 외부 레지스트리 프록시 사용 여부
proxy:
  httpProxy:
  httpsProxy:
  noProxy: 127.0.0.1,localhost,.local

# 미러 레지스트리 설정
trivy:
  gitHubToken: ""
```

## 6. Harbor 설치

Helm으로 Harbor 설치:

```bash
# Helm 리포지토리 추가
helm repo add harbor https://helm.goharbor.io
helm repo update

# Harbor 설치
helm install harbor harbor/harbor -f harbor-values.yaml -n harbor
```

## 7. Docker 클라이언트에서 Harbor 사용 설정

### hosts 파일 설정

Windows에서는 `C:\Windows\System32\drivers\etc\hosts` 파일에 다음 줄을 추가:

```
127.0.0.1 harbor.local
```

### Docker에 Harbor의 인증서 등록

```bash
# Windows: Docker Desktop용 인증서 디렉토리 생성
mkdir -p C:\ProgramData\Docker\certs.d\harbor.local

# 인증서 복사
copy tls.crt C:\ProgramData\Docker\certs.d\harbor.local\ca.crt
```

### Docker 재시작

Docker Desktop을 재시작하여 인증서 설정을 적용합니다.

## 8. Harbor 사용하기

### Docker 로그인

```bash
docker login harbor.local -u admin -p Harbor12345
```

### 이미지 푸시 및 풀

```bash
# 이미지 태그 지정
docker tag nginx:latest harbor.local/library/nginx:v1

# 이미지 푸시
docker push harbor.local/library/nginx:v1

# 이미지 풀
docker pull harbor.local/library/nginx:v1
```

### Helm 차트 저장소로 Harbor 사용하기

```bash
# Helm 저장소 추가
helm repo add myrepo https://harbor.local/chartrepo/library --username admin --password Harbor12345 --ca-file ./tls.crt

# Helm 차트 패키징 및 푸시
helm package mychart/
curl -u "admin:Harbor12345" -X POST -F "chart=@mychart-0.1.0.tgz" https://harbor.local/api/chartrepo/library/charts --cacert ./tls.crt
```

## 9. 문제 해결

### 인증서 관련 문제

1. **Secret 이름 확인**
   Harbor Ingress는 `harbor-ingress`라는 이름의 Secret을 사용합니다. `harbor-tls`만 생성한 경우 다음 명령어로 추가 생성:
   ```bash
   kubectl create secret tls harbor-ingress --cert=./tls.crt --key=./tls.key -n harbor
   ```

2. **인증서 도메인 확인**
   ```bash
   openssl x509 -in tls.crt -text -noout | findstr "DNS"
   ```

3. **브라우저에서 인증서 신뢰 설정**
   Windows에서는 관리자 권한으로:
   ```bash
   certutil -addstore -f Root C:\Users\[사용자명]\path\to\tls.crt
   ```

### 볼륨 권한 문제 (CrashLoopBackOff)

Harbor 컴포넌트(특히 PostgreSQL)에서 "Permission denied" 오류가 발생할 경우:

1. **볼륨 권한 재설정**
   WSL2에서:
   ```bash
   sudo chown -R 999:999 /mnt/data/harbor/database
   sudo chmod -R 700 /mnt/data/harbor/database
   ```

2. **로그 확인**
   ```bash
   kubectl logs -n harbor harbor-database-0
   kubectl logs -n harbor harbor-core-[pod-id]
   ```

3. **EmptyDir로 테스트**
   권한 문제가 계속되면 `harbor-values.yaml`에서 EmptyDir 볼륨 사용:
   ```yaml
   persistence:
     enabled: false
   ```

### Docker 접속 문제

1. **인증서 경로 확인**
   ```
   C:\ProgramData\Docker\certs.d\harbor.local\ca.crt
   ```

2. **Docker 디버그 모드**
   ```bash
   docker --debug login harbor.local
   ```

3. **Harbor 상태 확인**
   ```bash
   kubectl get pod -n harbor
   ``` 