# Kubernetes 환경에서 HTTPS 구축 가이드

이 가이드는 Kubernetes 클러스터에서 Traefik Ingress Controller를 사용하여 HTTPS를 구성하는 방법을 설명합니다.

## 1. Traefik Ingress Controller 설치

Traefik을 80/443 포트로 리스닝하도록 설치:

```bash
# Traefik Helm 리포지토리 추가
helm repo add traefik https://traefik.github.io/charts
helm repo update

# Traefik 설치 (80/443 포트 사용)
helm install traefik traefik/traefik --namespace kube-system \
  --set service.type=LoadBalancer \
  --set service.spec.loadBalancerIP=127.0.0.1 \
  --set ports.web.port=80 \
  --set ports.websecure.port=443 \
  --set ports.web.targetPort=80 \
  --set ports.websecure.targetPort=443 \
  --set ingressClass.enabled=true \
  --set ingressClass.isDefaultClass=true \
  --set "additionalArguments={--entrypoints.web.address=:80,--entrypoints.websecure.address=:443}"
```

## 2. TLS 인증서 생성

인증서를 생성하기 위한 OpenSSL 설정 파일 생성 (`openssl.cnf`):

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
DNS.4 = localhost
IP.1 = 127.0.0.1
```

자체 서명 인증서 생성:

```bash
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout tls.key -out tls.crt -config openssl.cnf
```

중요: 인증서의 Common Name(CN)과 Subject Alternative Name(SAN)에 사용할 모든 도메인을 반드시 포함해야 합니다.

## 3. Kubernetes TLS Secret 생성

각 서비스별로 TLS Secret 생성:

```bash
# fastapi 서비스용 TLS Secret
kubectl create secret tls fastapi-tls --cert=./tls.crt --key=./tls.key -n default

# minio 서비스용 TLS Secret
kubectl create secret tls minio-tls --cert=./tls.crt --key=./tls.key -n default

# minio-console 서비스용 TLS Secret
kubectl create secret tls minio-console-tls --cert=./tls.crt --key=./tls.key -n default
```

## 4. Ingress 리소스 생성

TLS를 지원하는 Ingress 리소스 예시:

```yaml
# fastapi-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: fastapi-ingress
  namespace: default
spec:
  ingressClassName: traefik
  rules:
    - host: fastapi.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: fastapi-service
                port:
                  number: 8000
  tls:
    - hosts:
        - fastapi.local
      secretName: fastapi-tls
```

```yaml
# minio-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: minio-ingress
  namespace: default
spec:
  ingressClassName: traefik
  rules:
    - host: minio.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: minio-service
                port:
                  number: 9000
    - host: minio-console.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: minio-service
                port:
                  number: 43529
  tls:
    - hosts:
        - minio.local
      secretName: minio-tls
    - hosts:
        - minio-console.local
      secretName: minio-console-tls
```

## 5. 호스트 파일 설정

Windows에서는 `C:\Windows\System32\drivers\etc\hosts` 파일에 다음 줄을 추가:

```
127.0.0.1 fastapi.local
127.0.0.1 minio.local
127.0.0.1 minio-console.local
```

## 6. 인증서 신뢰 설정 (Windows)

자체 서명 인증서를 신뢰하기 위해 다음 단계를 따릅니다:

### 관리자 권한 명령 프롬프트에서:

```bash
certutil -addstore -f Root "C:\경로\tls.crt"
```

### 또는 GUI 방식으로:

1. 인증서 파일(tls.crt)을 더블클릭
2. "인증서 설치" 선택
3. "저장소 위치": "로컬 컴퓨터" 선택 (관리자 권한 필요)
4. "인증서 저장소" 항목에서 "신뢰할 수 있는 루트 인증 기관" 선택
5. "마침" 클릭하고 보안 경고에서 "예" 선택

설치 후 반드시 **브라우저를 완전히 재시작**해야 합니다.

## 7. 문제 해결

### 인증서 경고가 계속 나타나는 경우:

1. 인증서의 CN과 SAN을 확인:
   ```bash
   openssl x509 -in tls.crt -text -noout | findstr "Subject:"
   openssl x509 -in tls.crt -text -noout | findstr "DNS"
   ```

2. 인증서에 모든 도메인이 포함되어 있는지 확인
   - 모든 접속 도메인은 인증서의 SAN에 포함되어야 함

3. 브라우저 캐시 삭제 및 재시작
   - 시크릿 모드/프라이빗 브라우징으로 테스트

4. 인증서가 올바른 경로에 설치되었는지 확인

### DNS 해석 문제:

`DNS_PROBE_FINISHED_NXDOMAIN` 오류가 발생하면:
1. hosts 파일이 올바르게 설정되었는지 확인
2. hosts 파일에 대한 권한 문제가 없는지 확인
3. DNS 캐시 초기화:
   ```bash
   ipconfig /flushdns
   ```

### Ingress가 작동하지 않는 경우:

1. Traefik 파드가 실행 중인지 확인:
   ```bash
   kubectl get pod -n kube-system | findstr traefik
   ```

2. Traefik 서비스 확인:
   ```bash
   kubectl get svc -n kube-system | findstr traefik
   ```

3. Ingress 리소스 확인:
   ```bash
   kubectl get ingress -A
   kubectl describe ingress [ingress-name] -n [namespace]
   ``` 