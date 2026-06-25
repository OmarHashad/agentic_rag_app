from datetime import timedelta
from typing import BinaryIO

from minio import Minio
from minio.error import S3Error

from backend.core.config import MINIO_BUCKET


def upload_fileobj(
    client: Minio,
    object_key: str,
    data: BinaryIO,
    length: int,
    content_type: str,
) -> None:
    client.put_object(
        MINIO_BUCKET,
        object_key,
        data,
        length,
        content_type=content_type,
    )


def get_presigned_download_url(client: Minio, object_key: str) -> str:
    return client.presigned_get_object(
        MINIO_BUCKET,
        object_key,
        expires=timedelta(minutes=15),
    )


def object_exists(client: Minio, object_key: str) -> bool:
    try:
        client.stat_object(MINIO_BUCKET, object_key)
        return True
    except S3Error:
        return False


def get_presigned_upload_url(client: Minio, object_key: str) -> str:
    return client.presigned_put_object(
        MINIO_BUCKET,
        object_key,
        expires=timedelta(minutes=15),
    )


def get_object_metadata(client: Minio, object_key: str):
    return client.stat_object(MINIO_BUCKET, object_key)
