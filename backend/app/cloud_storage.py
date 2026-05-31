import os
from pathlib import Path


class StorageBackend:
    provider = "local"

    def save(self, source_path: Path, key: str) -> str:
        return str(source_path)


class LocalStorage(StorageBackend):
    provider = "local"


class S3Storage(StorageBackend):
    provider = "s3"

    def save(self, source_path: Path, key: str) -> str:
        import boto3

        bucket = os.environ["S3_BUCKET"]
        boto3.client("s3").upload_file(str(source_path), bucket, key)
        return f"s3://{bucket}/{key}"


class GCSStorage(StorageBackend):
    provider = "gcs"

    def save(self, source_path: Path, key: str) -> str:
        from google.cloud import storage

        bucket_name = os.environ["GCS_BUCKET"]
        bucket = storage.Client().bucket(bucket_name)
        bucket.blob(key).upload_from_filename(str(source_path))
        return f"gs://{bucket_name}/{key}"


class FirebaseStorage(StorageBackend):
    provider = "firebase"

    def save(self, source_path: Path, key: str) -> str:
        import firebase_admin
        from firebase_admin import credentials, storage

        bucket_name = os.environ["FIREBASE_BUCKET"]
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.ApplicationDefault(), {"storageBucket": bucket_name})
        blob = storage.bucket().blob(key)
        blob.upload_from_filename(str(source_path))
        return f"firebase://{bucket_name}/{key}"


def storage_backend() -> StorageBackend:
    provider = os.getenv("DOCUMENT_STORAGE_PROVIDER", "local").lower()
    if provider == "s3":
        return S3Storage()
    if provider == "gcs":
        return GCSStorage()
    if provider == "firebase":
        return FirebaseStorage()
    return LocalStorage()
