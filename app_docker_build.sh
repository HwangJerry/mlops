#!/bin/bash

if [ $# -eq 0 ]; then
    TAG="latest"
else
    TAG="$1"
fi

IMAGE_NAME="localhost:30010/ghkdwp018/mlops-app"

echo "Building Docker image: ${IMAGE_NAME}:${TAG}"

docker build -t "${IMAGE_NAME}:${TAG}" -f backend.Dockerfile .

if [ $? -eq 0 ]; then
    echo "Successfully built ${IMAGE_NAME}:${TAG}"
else
    echo "Failed to build Docker image"
    exit 1
fi