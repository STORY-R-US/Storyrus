"""Serve bytes do storage local (dev sem R2/MinIO)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response, status

from app import storage

router = APIRouter(prefix="/v1/local-storage", tags=["storage"])


def _mime_for(key: str) -> str:
    low = key.lower()
    if low.endswith(".jpg") or low.endswith(".jpeg"):
        return "image/jpeg"
    if low.endswith(".webp"):
        return "image/webp"
    if low.endswith(".gif"):
        return "image/gif"
    if low.endswith(".pdf"):
        return "application/pdf"
    return "image/png"


@router.get("/{key:path}")
def get_local_object(key: str, expires: int = 0, signature: str = "") -> Response:
    if not storage.uses_local_disk():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "storage local desligado")
    if not storage.valid_local_signature(key, "GET", expires, signature):
        raise HTTPException(403, "Link ausente, inválido ou expirado")
    try:
        data = storage.get_bytes(key)
    except FileNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "objeto ausente") from None
    except storage.StorageNotConfigured as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return Response(content=data, media_type=_mime_for(key))


@router.put("/{key:path}", status_code=204)
async def put_local_object(
    key: str, request: Request, expires: int = 0, signature: str = ""
) -> Response:
    """PUT do fluxo mobile (presign_put → storage local)."""
    if not storage.uses_local_disk():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "storage local desligado")
    if not storage.valid_local_signature(key, "PUT", expires, signature):
        raise HTTPException(403, "Link ausente, inválido ou expirado")
    data = await request.body()
    if len(data) > 10_000_000:
        raise HTTPException(413, "Arquivo muito grande (máximo 10 MB)")
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "corpo vazio")
    try:
        storage.put_bytes(
            key, data, request.headers.get("content-type") or "application/octet-stream"
        )
    except storage.StorageNotConfigured as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return Response(status_code=204)
