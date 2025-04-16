#!/bin/bash

set -e # 만약 어떤 명령어가 실패하면 스크립트 실행을 중단

echo "Applying Kubernetes resources..."

# Docker Registry
echo "1. Applying Docker Registry..."
kubectl apply -f docker-registry.yaml
echo "✓ Docker Registry applied"

# MinIO
echo "2. Applying MinIO..."
kubectl apply -f minio.yaml
echo "✓ MinIO applied"

# Application
echo "3. Applying Application..."
kubectl apply -f app.yaml
echo "✓ Application applied"

echo "All resources have been successfully applied."