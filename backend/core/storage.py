import os
import shutil
import hashlib
import logging
from abc import ABC, abstractmethod
from typing import BinaryIO, Optional
from core.config import settings

logger = logging.getLogger(__name__)

class StorageInterface(ABC):
    @abstractmethod
    def save(self, file_obj: BinaryIO, filename: str) -> str:
        """Saves file and returns the storage key"""
        pass
        
    @abstractmethod
    def get(self, storage_key: str) -> str:
        """Returns the local path or accessible URL to the file"""
        pass
        
    @abstractmethod
    def delete(self, storage_key: str) -> bool:
        """Deletes the file"""
        pass

class LocalStorage(StorageInterface):
    """Local disk storage for MVP and development environments."""
    def __init__(self, base_dir: str = "storage"):
        self.base_dir = os.path.abspath(base_dir)
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, file_obj: BinaryIO, filename: str) -> str:
        file_obj.seek(0)
        file_hash = hashlib.sha256(file_obj.read()).hexdigest()
        file_obj.seek(0)
        
        extension = os.path.splitext(filename)[1]
        storage_key = f"{file_hash}{extension}"
        file_path = os.path.join(self.base_dir, storage_key)
        
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file_obj, f)
            
        return storage_key

    def get(self, storage_key: str) -> str:
        return os.path.join(self.base_dir, storage_key)
        
    def delete(self, storage_key: str) -> bool:
        file_path = os.path.join(self.base_dir, storage_key)
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

class S3Storage(StorageInterface):
    """Amazon S3 Cloud Object Storage provider for enterprise production."""
    def __init__(self, bucket_name: Optional[str] = None, region: Optional[str] = None):
        self.bucket_name = bucket_name or settings.S3_BUCKET_NAME or "recruitment-cv-storage"
        self.region = region or settings.S3_REGION
        self._s3_client = None
        self._local_fallback = LocalStorage()

        try:
            import boto3
            self._s3_client = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        except Exception as e:
            logger.warning(f"Boto3 S3 client initialization failed ({e}); falling back to LocalStorage.")
            self._s3_client = None

    def save(self, file_obj: BinaryIO, filename: str) -> str:
        if not self._s3_client:
            return self._local_fallback.save(file_obj, filename)

        file_obj.seek(0)
        file_hash = hashlib.sha256(file_obj.read()).hexdigest()
        file_obj.seek(0)

        extension = os.path.splitext(filename)[1]
        storage_key = f"resumes/{file_hash}{extension}"

        self._s3_client.upload_fileobj(file_obj, self.bucket_name, storage_key)
        return storage_key

    def get(self, storage_key: str) -> str:
        if not self._s3_client:
            return self._local_fallback.get(storage_key)
        
        # Generate presigned URL for secure temporary download (1 hour)
        return self._s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket_name, "Key": storage_key},
            ExpiresIn=3600
        )

    def delete(self, storage_key: str) -> bool:
        if not self._s3_client:
            return self._local_fallback.delete(storage_key)
        try:
            self._s3_client.delete_object(Bucket=self.bucket_name, Key=storage_key)
            return True
        except Exception as e:
            logger.error(f"Failed to delete S3 object {storage_key}: {e}")
            return False

class GCSStorage(StorageInterface):
    """Google Cloud Storage (GCS) provider for GCP deployments."""
    def __init__(self, bucket_name: Optional[str] = None):
        self.bucket_name = bucket_name or settings.GCS_BUCKET_NAME or "recruitment-cv-bucket"
        self._gcs_client = None
        self._local_fallback = LocalStorage()

        try:
            from google.cloud import storage
            self._gcs_client = storage.Client()
        except Exception as e:
            logger.warning(f"Google Cloud Storage client unavailable ({e}); falling back to LocalStorage.")
            self._gcs_client = None

    def save(self, file_obj: BinaryIO, filename: str) -> str:
        if not self._gcs_client:
            return self._local_fallback.save(file_obj, filename)

        file_obj.seek(0)
        file_hash = hashlib.sha256(file_obj.read()).hexdigest()
        file_obj.seek(0)

        extension = os.path.splitext(filename)[1]
        storage_key = f"resumes/{file_hash}{extension}"

        bucket = self._gcs_client.bucket(self.bucket_name)
        blob = bucket.blob(storage_key)
        blob.upload_from_file(file_obj)
        return storage_key

    def get(self, storage_key: str) -> str:
        if not self._gcs_client:
            return self._local_fallback.get(storage_key)
        bucket = self._gcs_client.bucket(self.bucket_name)
        blob = bucket.blob(storage_key)
        return blob.generate_signed_url(expiration=3600)

    def delete(self, storage_key: str) -> bool:
        if not self._gcs_client:
            return self._local_fallback.delete(storage_key)
        try:
            bucket = self._gcs_client.bucket(self.bucket_name)
            blob = bucket.blob(storage_key)
            blob.delete()
            return True
        except Exception as e:
            logger.error(f"Failed to delete GCS object {storage_key}: {e}")
            return False

def get_storage_provider() -> StorageInterface:
    """Storage provider factory based on application configuration."""
    backend = settings.STORAGE_BACKEND.lower()
    if backend == "s3":
        return S3Storage()
    elif backend in ["gcs", "google"]:
        return GCSStorage()
    return LocalStorage()
