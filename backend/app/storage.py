"""Storage com URLs assinadas (S3/R2) ou disco local em dev.

Chaves nunca vao ao cliente: uploads e entregaveis sao acessados via URL
assinada de curta duracao. Sem STORAGE_ACCESS_KEY/SECRET, usa disco local
(`STORAGE_LOCAL_DIR`, default `.local-storage`) e URLs `/v1/local-storage/...`.
"""

from __future__ import annotations

import uuid
from functools import lru_cache
from pathlib import Path

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


def local_object_url(key: str) -> str:
    """Path relativo servido pela API (proxy Vite encaminha /v1)."""
    return f"/v1/local-storage/{key.lstrip('/')}"


def presign_put(key: str, content_type: str) -> str:
    """URL assinada para upload (PUT)."""
    client = _public_client()
    if client is None:
        return local_object_url(key)
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
        Params={"Bucket": settings.storage_bucket, "Key": key},
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
    client.put_object(Bucket=settings.storage_bucket, Key=key, Body=data, ContentType=content_type)
    return key


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
