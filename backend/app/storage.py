"""Storage com URLs assinadas (S3/R2) ou disco local em dev.

Chaves nunca vao ao cliente: uploads e entregaveis sao acessados via URL
assinada de curta duracao. Sem STORAGE_ACCESS_KEY/SECRET, usa disco local
(`STORAGE_LOCAL_DIR`, default `.local-storage`) e URLs `/v1/local-storage/...`.
"""

from __future__ import annotations

import hashlib
import hmac
import time
import uuid
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from app.config import settings


@lru_cache
def _client(endpoint: str | None = None):
    if not (settings.storage_access_key and settings.storage_secret_key):
        return None
    import boto3  # import tardio: so quando ha credenciais
    from botocore.client import Config

    return boto3.client(
        "s3",
        endpoint_url=endpoint or settings.storage_endpoint_url,
        region_name=settings.storage_region,
        aws_access_key_id=settings.storage_access_key,
        aws_secret_access_key=settings.storage_secret_key,
        config=Config(
            signature_version="s3v4",
            connect_timeout=10,
            read_timeout=60,
            retries={"max_attempts": 2, "mode": "standard"},
        ),
    )


def _internal_client():
    """Cliente para acesso server-side (api/worker) — usa o endpoint interno."""
    return _client(settings.storage_endpoint_url)


def _public_client():
    """Cliente para gerar URLs assinadas que o NAVEGADOR vai acessar.

    Em dev local (MinIO) o navegador acessa por localhost, enquanto os
    containers acessam por 'minio'. STORAGE_PUBLIC_ENDPOINT_URL cobre esse caso;
    se nao definido, usa o mesmo endpoint interno (ex.: S3/R2 em producao).
    """
    return _client(settings.storage_public_endpoint_url or settings.storage_endpoint_url)


def local_root() -> Path:
    raw = (getattr(settings, "storage_local_dir", None) or ".local-storage").strip()
    path = Path(raw)
    if not path.is_absolute():
        path = Path.cwd() / path
    path.mkdir(parents=True, exist_ok=True)
    return path


def uses_local_disk() -> bool:
    return _internal_client() is None


def new_key(project_id: uuid.UUID, kind: str, ext: str) -> str:
    return f"projects/{project_id}/{kind}/{uuid.uuid4().hex}.{ext.lstrip('.')}"


def _local_signature(key: str, method: str, expires: int) -> str:
    payload = f"{method.upper()}\n{key}\n{expires}".encode()
    return hmac.new(settings.jwt_secret.encode(), payload, hashlib.sha256).hexdigest()


def local_object_url(key: str, method: str = "GET") -> str:
    """Short-lived capability URL, including for local-disk deployments."""
    expires = int(time.time()) + settings.storage_signing_ttl
    signature = _local_signature(key, method, expires)
    return f"/v1/local-storage/{quote(key, safe='/')}?expires={expires}&signature={signature}"


def valid_local_signature(key: str, method: str, expires: int, signature: str) -> bool:
    return expires > int(time.time()) and hmac.compare_digest(
        _local_signature(key, method, expires), signature
    )


def presign_put(key: str, content_type: str) -> str:
    """URL assinada para upload (PUT)."""
    client = _public_client()
    if client is None:
        return local_object_url(key, "PUT")
    return client.generate_presigned_url(
        "put_object",
        Params={"Bucket": settings.storage_bucket, "Key": key, "ContentType": content_type},
        ExpiresIn=settings.storage_signing_ttl,
    )


def presign_get(key: str) -> str:
    """URL assinada para download (GET)."""
    client = _public_client()
    if client is None:
        return local_object_url(key)
    return client.generate_presigned_url(
        "get_object",
        Params={
            "Bucket": settings.storage_bucket,
            "Key": key,
            "ResponseCacheControl": "private, no-store",
        },
        ExpiresIn=settings.storage_signing_ttl,
    )


# --------------------------------------------------------------------------- #
# Acesso server-side (workers) — nunca exposto ao cliente.
# --------------------------------------------------------------------------- #
class StorageNotConfigured(Exception):
    pass


def _local_path(key: str) -> Path:
    root = local_root().resolve()
    path = (root / key.lstrip("/")).resolve()
    if not str(path).startswith(str(root)):
        raise StorageNotConfigured(f"chave invalida: {key}")
    return path


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """Sobe bytes diretamente (worker). Retorna a chave."""
    _ = content_type
    client = _internal_client()
    if client is None:
        path = _local_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key
    client.put_object(
        Bucket=settings.storage_bucket,
        Key=key,
        Body=data,
        ContentType=content_type,
        CacheControl="private, no-store",
    )
    return key


def delete_key(key: str | None) -> None:
    """Remove um arquivo do projeto. Arquivo ausente não interrompe a exclusão."""
    if not key or not str(key).strip():
        return
    client = _internal_client()
    if client is None:
        try:
            path = _local_path(key)
        except StorageNotConfigured:
            return
        if path.is_file():
            path.unlink()
        return
    client.delete_object(Bucket=settings.storage_bucket, Key=key)


def delete_project_objects(project_id: uuid.UUID) -> None:
    """Remove current objects, including superseded artwork no longer in the DB."""
    project_id = uuid.UUID(str(project_id))
    prefix = f"projects/{project_id}/"
    client = _internal_client()
    if client is None:
        import shutil

        root = local_root().resolve()
        directory = (root / prefix).resolve()
        if not directory.is_relative_to(root) or directory == root:
            raise StorageNotConfigured("Diretório de exclusão inválido")
        if directory.exists():
            shutil.rmtree(directory)
        return
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=settings.storage_bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            client.delete_object(Bucket=settings.storage_bucket, Key=obj["Key"])


def get_bytes(key: str) -> bytes:
    """Baixa bytes de um asset (worker)."""
    client = _internal_client()
    if client is None:
        path = _local_path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        return path.read_bytes()
    obj = client.get_object(Bucket=settings.storage_bucket, Key=key)
    return obj["Body"].read()
