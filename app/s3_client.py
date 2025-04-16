import os
import boto3
from botocore.client import Config

import logging
logger = logging.getLogger(__name__)


class MinioS3Client:
    def __init__(
        self,
        # endpoint_url: str = "http://localhost:30090", # for local
        endpoint_url: str = "http://minio-service:9000",
        access_key: str = "console",
        secret_key: str = "console123",
        bucket_name: str = "mlops",
        region_name: str = "us-east-1"
    ):
        self.bucket_name = bucket_name
        self.s3 = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region_name,
            config=Config(signature_version="s3v4"),
        )
    

    def list_files(self, prefix: str = "model/t5-small/") -> list[str]:
        """MinIO에서 지정된 prefix 경로의 파일 목록을 가져옴"""
        paginator = self.s3.get_paginator("list_objects_v2")
        files = []
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                files.append(obj["Key"])
        return files
    
    def exists(self, prefix: str = "model/t5-small/") -> bool:
        response = self.s3.list_objects_v2(
            Bucket=self.bucket_name, Prefix=prefix, MaxKeys=1
        )
        return "Contents" in response

    def download_from_minio(self, prefix: str = "model/t5-small/", local_dir: str = "models/t5-small/") -> None:
        """MinIO에서 지정된 prefix 경로의 파일들을 로컬 디렉토리에 다운로드"""
        paginator = self.s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket_name, Prefix=prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                filename = key[len(prefix):].lstrip("/")
                local_path = os.path.join(local_dir, filename)

                os.makedirs(os.path.dirname(local_path), exist_ok=True)
                logger.info(f"Downloading: {key} → {local_path}")
                self.s3.download_file(self.bucket_name, key, local_path)

    def upload_to_minio(self, local_dir: str = "models/t5-small/", prefix: str = "model/t5-small/") -> None:
        """로컬 디렉토리의 모든 파일을 지정된 prefix로 업로드"""
        for root, _, files in os.walk(local_dir):
            for file in files:
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, local_dir)
                s3_key = os.path.join(prefix, relative_path).replace("\\", "/")  # for Windows

                logger.info(f"Uploading: {full_path} → {s3_key}")
                self.s3.upload_file(full_path, self.bucket_name, s3_key)