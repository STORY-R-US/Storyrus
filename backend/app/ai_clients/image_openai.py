"""ImageProvider: OpenAI GPT Image (gpt-image-1).

Avatar, cena, realistic e refine_* usam a Images API (generations/edits).
Sem Gemini, Fal ou PuLID neste caminho.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import logging
import random
import re

import httpx
from PIL import Image, ImageFilter

from app.ai_clients.base import MAX_REFRAME_TOP_FRACTION, ImageResult, ProviderError
from app.ai_clients.book_prompts import (
    REFINE_IDENTITY_AVATAR_PROMPT,
    REFINE_IDENTITY_PROMPT,
    REFINE_SCENE_PROMPT,
    SCENE_GEN_PREFIX,
)
from app.ai_clients.resilience import billing_exhausted
from app.config import settings
from app.observability.opik_trace import track, update_span
from app.services.pricing import openai_image_cost

logger = logging.getLogger(__name__)

_OPENAI_BASE = "https://api.openai.com/v1"
_TRANSIENT_STATUS = frozenset({429, 500, 502, 503, 504})


def _error_from_response(resp: httpx.Response) -> ProviderError:
    raw_body = resp.text or ""
    try:
        payload = resp.json()
    except (ValueError, TypeError):
        payload = None

    api_error = payload.get("error") if isinstance(payload, dict) else None
    request_id = str(resp.headers.get("x-request-id") or "").strip()
    if isinstance(api_error, dict):
        message = str(api_error.get("message") or "")
        request_id = request_id or str(api_error.get("request_id") or "").strip()
        if not request_id:
            match = re.search(r"\breq_[A-Za-z0-9]+\b", message)
            request_id = match.group(0) if match else ""
        details = {"request_id": request_id} if request_id else {}
        details.update(
            {
                key: api_error[key]
                for key in ("type", "code", "param", "moderation_details")
                if key in api_error and api_error[key] is not None
            }
        )
        if message:
            details["message"] = message[:1000]
        body = json.dumps(details, ensure_ascii=False, separators=(",", ":"))[:1600]
    else:
        body = raw_body[:300]
    transient = resp.status_code in _TRANSIENT_STATUS and not billing_exhausted(body)
    return ProviderError(
        f"OpenAI {resp.status_code}: {body}",
        transient=transient,
        status_code=resp.status_code,
    )


def _retry_delay(attempt: int) -> float:
    base = settings.openai_retry_base_s
    cap = settings.openai_retry_max_s
    raw = min(cap, base * (2 ** max(0, attempt - 1)))
    return random.uniform(0, raw) if raw > 0 else 0.0


def _rehearsal_image(label: str) -> ImageResult | None:
    """Período de testes: imagem local, sem nenhuma chamada à OpenAI."""
    if not settings.skip_openai:
        return None
    from app.workers.handlers.common import _offline_png

    return ImageResult(
        image_bytes=_offline_png(
            (label or "Imagem genérica")[:80],
            palette=((235, 243, 250), (255, 250, 242)),
        ),
        cost_usd=0,
        meta={"provider": "demo", "rehearsal": True},
    )


def _retry_after_s(resp: httpx.Response) -> float | None:
    raw = resp.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        value = float(str(raw).strip())
    except ValueError:
        return None
    if value <= 0:
        return None
    return min(value, settings.openai_retry_max_s)


def _parse_b64_response(data: dict) -> tuple[bytes, str, dict]:
    items = data.get("data") or []
    if not items:
        raise ProviderError("OpenAI: resposta sem imagem", transient=False)
    first = items[0]
    b64 = first.get("b64_json")
    if not b64:
        raise ProviderError("OpenAI: data[0] sem b64_json", transient=False)
    mime = "image/png"
    out_fmt = (data.get("output_format") or first.get("output_format") or "png").lower()
    if out_fmt == "jpeg":
        mime = "image/jpeg"
    elif out_fmt == "webp":
        mime = "image/webp"
    usage = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return base64.b64decode(b64), mime, usage


class OpenAIImageProvider:
    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        timeout: float | None = None,
        model: str | None = None,
    ):
        self._api_key = api_key or settings.openai_api_key
        self._timeout = timeout if timeout is not None else settings.openai_timeout_s
        self._model = model or settings.openai_image_model

    def _headers(self) -> dict[str, str]:
        if not self._api_key:
            raise ProviderError("OPENAI_API_KEY ausente", transient=False)
        return {
            "Authorization": f"Bearer {self._api_key}",
        }

    @track(name="openai_generate", type="llm", capture_input=False, capture_output=False)
    async def _generate_text(self, prompt: str, *, size: str, aspect_hint: str = "") -> ImageResult:
        body = {
            "model": self._model,
            "prompt": prompt,
            "size": size,
            "quality": settings.openai_image_quality,
        }
        update_span(metadata={"provider": "openai", "model": self._model, "mode": "generate"})
        return await self._post_json("/images/generations", body)

    async def _generate_with_refs(
        self, prompt: str, images: list[bytes], *, size: str
    ) -> ImageResult:
        refs = [img for img in images if img]
        if not refs:
            return await self._generate_text(prompt, size=size)
        files: list[tuple[str, tuple[str, bytes, str]]] = []
        for idx, img in enumerate(refs):
            ext, mime = "png", "image/png"
            if img.startswith(b"\xff\xd8\xff"):
                ext, mime = "jpg", "image/jpeg"
            elif img.startswith(b"RIFF") and img[8:12] == b"WEBP":
                ext, mime = "webp", "image/webp"
            files.append(("image[]" if len(refs) > 1 else "image", (f"ref{idx}.{ext}", img, mime)))
        data = {
            "model": self._model,
            "prompt": prompt,
            "size": size,
            "quality": settings.openai_image_quality,
        }
        if self._model in {"gpt-image-1", "gpt-image-1.5"}:
            data["input_fidelity"] = "high"
        update_span(
            metadata={
                "provider": "openai",
                "model": self._model,
                "mode": "edit",
                "ref_count": len(refs),
            }
        )
        return await self._post_multipart("/images/edits", data=data, files=files)

    async def _post_json(self, path: str, body: dict) -> ImageResult:
        rehearsal = _rehearsal_image(str(body.get("prompt") or "Imagem genérica"))
        if rehearsal is not None:
            return rehearsal
        url = f"{_OPENAI_BASE}{path}"
        last_error: ProviderError | None = None
        attempts = max(1, int(settings.openai_max_retries))

        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(url, headers=self._headers(), json=body)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = ProviderError(str(exc), transient=True)
                if attempt >= attempts:
                    raise last_error
                await asyncio.sleep(_retry_delay(attempt))
                continue

            if resp.status_code >= 400:
                last_error = _error_from_response(resp)
                if not last_error.transient or attempt >= attempts:
                    raise last_error
                delay = _retry_after_s(resp) or _retry_delay(attempt)
                logger.warning(
                    "OpenAI %s (tentativa %s/%s); retry em %.1fs",
                    resp.status_code,
                    attempt,
                    attempts,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            data = resp.json()
            image_bytes, mime, usage = _parse_b64_response(data)
            cost = openai_image_cost(usage if usage else None)
            update_span(
                output={"ok": True, "mime": mime, "attempts": attempt},
                metadata={"cost_usd": cost, "usage": usage, "attempts": attempt},
            )
            return ImageResult(
                image_bytes=image_bytes,
                mime_type=mime,
                cost_usd=cost,
                meta={
                    "provider": "openai",
                    "model": self._model,
                    "attempts": attempt,
                    "usage": usage,
                },
            )

        assert last_error is not None
        raise last_error

    async def _post_multipart(
        self,
        path: str,
        *,
        data: dict,
        files: list[tuple[str, tuple[str, bytes, str]]],
    ) -> ImageResult:
        rehearsal = _rehearsal_image(str(data.get("prompt") or "Imagem genérica"))
        if rehearsal is not None:
            return rehearsal
        url = f"{_OPENAI_BASE}{path}"
        last_error: ProviderError | None = None
        attempts = max(1, int(settings.openai_max_retries))

        for attempt in range(1, attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    resp = await client.post(
                        url,
                        headers=self._headers(),
                        data=data,
                        files=files,
                    )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = ProviderError(str(exc), transient=True)
                if attempt >= attempts:
                    raise last_error
                await asyncio.sleep(_retry_delay(attempt))
                continue

            if resp.status_code >= 400:
                last_error = _error_from_response(resp)
                if not last_error.transient or attempt >= attempts:
                    raise last_error
                delay = _retry_after_s(resp) or _retry_delay(attempt)
                logger.warning(
                    "OpenAI %s (tentativa %s/%s); retry em %.1fs",
                    resp.status_code,
                    attempt,
                    attempts,
                    delay,
                )
                await asyncio.sleep(delay)
                continue

            payload = resp.json()
            image_bytes, mime, usage = _parse_b64_response(payload)
            cost = openai_image_cost(usage if usage else None)
            return ImageResult(
                image_bytes=image_bytes,
                mime_type=mime,
                cost_usd=cost,
                meta={
                    "provider": "openai",
                    "model": self._model,
                    "attempts": attempt,
                    "usage": usage,
                },
            )

        assert last_error is not None
        raise last_error

    async def generate_character(
        self, *, prompt: str, reference_images: list[bytes], style: str
    ) -> ImageResult:
        refs = [img for img in (reference_images or []) if img]
        text = (
            f"Estilo pedido: '{style}'. {prompt}"
            if refs
            else f"Gere a partir do texto. Nao ha foto anexa. Estilo pedido: '{style}'. {prompt}"
        )
        return await self._generate_with_refs(text, refs, size=settings.openai_image_size_portrait)

    async def reframe_editorial_art(
        self,
        *,
        art,
        photos,
        top_fraction,
        prompt,
        preserve_complete_scene=False,
        clear_through_fraction=None,
    ):
        """Make a billable-API-free reserve by extending only the scene's edge background."""
        image = Image.open(io.BytesIO(art)).convert("RGBA")
        if image.width != image.height or not 0.05 <= top_fraction <= MAX_REFRAME_TOP_FRACTION:
            raise ValueError("Enquadramento editorial inválido")
        width, height = image.size
        clear_through_fraction = (
            max(0.0, top_fraction - 0.06)
            if clear_through_fraction is None
            else float(clear_through_fraction)
        )
        if not 0 <= clear_through_fraction < 1:
            raise ValueError("Reserva editorial inválida")
        shift = max(
            round(height * top_fraction),
            round(height * clear_through_fraction) + 2,
        )
        if shift >= height:
            raise ValueError("Reserva editorial inválida")

        if preserve_complete_scene:
            side = image.height - shift
            left = (image.width - side) // 2
            source = image.resize((side, side), Image.Resampling.LANCZOS)
            source_box = (left, shift, left + side, height)
        else:
            left = 0
            source = image
            source_box = (0, shift, width, height)

        # Reuse only narrow outer strips, where a centered protagonist is not
        # placed. This produces a calm, scene-matched title reserve without
        # asking the image model to invent another head or hairline.
        rgb_source = source.convert("RGB")
        sample_width = max(1, round(rgb_source.width * 0.06))
        sample_height = max(1, round(rgb_source.height * 0.24))
        blur_radius = max(1, round(width * 0.006))
        left_sample = rgb_source.crop((0, 0, sample_width, sample_height))
        right_sample = rgb_source.crop(
            (rgb_source.width - sample_width, 0, rgb_source.width, sample_height)
        )
        left_background = left_sample.resize((width, shift), Image.Resampling.BICUBIC).filter(
            ImageFilter.GaussianBlur(blur_radius)
        )
        right_background = right_sample.resize((width, shift), Image.Resampling.BICUBIC).filter(
            ImageFilter.GaussianBlur(blur_radius)
        )
        horizontal = Image.new("L", (width, 1))
        horizontal.putdata([round(255 * x / max(1, width - 1)) for x in range(width)])
        extension = Image.composite(
            left_background,
            right_background,
            horizontal.resize((width, shift), Image.Resampling.BICUBIC),
        )

        # Feather the join only below the verified empty text reserve. The
        # source is never blended into the protected crop itself.
        clear_through = round(height * clear_through_fraction)
        feather_height = min(round(height * 0.035), max(0, shift - clear_through - 2))
        if feather_height >= 2:
            left_edge = rgb_source.getpixel((0, 0))
            right_edge = rgb_source.getpixel((rgb_source.width - 1, 0))
            for offset in range(feather_height):
                y = shift - feather_height + offset
                source_row = Image.new("RGB", (width, 1), left_edge)
                source_row.paste(rgb_source.crop((0, 0, rgb_source.width, 1)), (left, 0))
                if source_box[2] < width:
                    source_row.paste(
                        Image.new("RGB", (width - source_box[2], 1), right_edge),
                        (source_box[2], 0),
                    )
                source_row = source_row.crop((0, 0, width, 1))
                current_row = extension.crop((0, y, width, y + 1))
                alpha = (offset + 1) / (feather_height + 1)
                extension.paste(Image.blend(current_row, source_row, alpha), (0, y))

        canvas = Image.new("RGB", image.size)
        canvas.paste(extension, (0, 0))
        if preserve_complete_scene and left:
            left_fill = rgb_source.crop((0, 0, 1, rgb_source.height)).resize(
                (left, rgb_source.height), Image.Resampling.BICUBIC
            )
            canvas.paste(left_fill.filter(ImageFilter.GaussianBlur(blur_radius)), (0, shift))
        if preserve_complete_scene and source_box[2] < width:
            right_width = width - source_box[2]
            right_fill = rgb_source.crop(
                (rgb_source.width - 1, 0, rgb_source.width, rgb_source.height)
            ).resize((right_width, rgb_source.height), Image.Resampling.BICUBIC)
            canvas.paste(
                right_fill.filter(ImageFilter.GaussianBlur(blur_radius)),
                (source_box[2], shift),
            )
        canvas.paste(rgb_source, source_box[:2])

        output = io.BytesIO()
        canvas.save(output, "PNG")
        return ImageResult(
            image_bytes=output.getvalue(),
            cost_usd=0.0,
            meta={
                "provider": "local",
                "operation": "deterministic_title_reserve_reframe",
                "billable": False,
                "protected_source_pixels": True,
                "generated_top_fraction": shift / height,
                "clear_through_fraction": clear_through_fraction,
            },
        )

    async def generate_scene(
        self,
        *,
        prompt: str,
        character_ref: bytes,
        style: str,
        photo: bytes | None = None,
        extra_refs: list[bytes] | None = None,
        reference_role: str = "character",
        landscape: bool = False,
    ) -> ImageResult:
        extras = [img for img in (extra_refs or []) if img]
        size = "1536x1024" if landscape else settings.openai_image_size_square
        if photo:
            # Original photographs always outrank any generated avatar or cover.
            from app.services.book_profile import IDENTITY

            role = "CAPA aprovada" if reference_role == "cover" else "avatar ou continuidade visual"
            secondary = [character_ref] if character_ref and character_ref != photo else []
            reference_note = f"SEGUNDA imagem: {role}. " if secondary else ""
            text = (
                f"PRIMEIRA imagem: FOTO ORIGINAL, fonte definitiva da identidade. "
                f"{reference_note}Referencias seguintes: fotos adicionais e "
                f"continuidade, conforme a ficha. {IDENTITY}\nEstilo: {style}.\n{prompt}"
            )
            return await self._generate_with_refs(text, [photo] + secondary + extras, size=size)
        if reference_role == "cover":
            # Preserve the product prompt: this reference is a book cover,
            # never an avatar or an instruction to illustrate the real person.
            text = f"{prompt}\nEstilo da fotografia: {style}."
            return await self._generate_with_refs(text, [character_ref] + extras, size=size)
        identity = (
            "A primeira imagem e o AVATAR (unica fonte de verdade do rosto, "
            "cabelo, idade e proporcoes). NAO copie a roupa dele. "
        )
        if extras:
            identity += "As imagens seguintes sao referencias de figurino, ficha ou estilo. "
        text = (
            f"{SCENE_GEN_PREFIX}{identity}"
            f"Ilustre no estilo '{style}', identico ao estilo da referencia. "
            f"Cena: {prompt}"
        )
        images = [character_ref] + extras
        return await self._generate_with_refs(text, images, size=settings.openai_image_size_square)

    async def generate_realistic(
        self, *, photo: bytes, prompt: str, negative: str = "", style: str = "realistic"
    ) -> ImageResult:
        text = prompt
        if negative:
            text += f"\n\nNegative prompt (evite/avoid): {negative}"
        text += f"\nEstilo: {style}"
        return await self._generate_with_refs(
            text, [photo], size=settings.openai_image_size_portrait
        )

    async def refine_identity(
        self, *, photo: bytes, illustration: bytes, style: str = "realistic"
    ) -> ImageResult:
        """Corrige o rosto da ilustracao para ficar fiel a foto.

        Ordem: (1) foto/recorte = verdade; (2) personagem a corrigir.
        """
        if not photo or not illustration:
            raise ProviderError("refine_identity OpenAI exige foto e ilustracao", transient=False)
        prompt = REFINE_IDENTITY_AVATAR_PROMPT if "CGI" in (style or "") else REFINE_IDENTITY_PROMPT
        return await self._generate_with_refs(
            prompt,
            [photo, illustration],
            size=settings.openai_image_size_portrait,
        )

    async def refine_scene(
        self,
        *,
        character_ref: bytes,
        scene: bytes,
        style: str = "realistic",
        photo: bytes | None = None,
    ) -> ImageResult:
        """Corrige a cabeca na cena usando o avatar (nao a foto crua).

        Ordem: (1) avatar; (2) cena. `photo` e ignorado de proposito.
        """
        if not character_ref or not scene:
            raise ProviderError("refine_scene OpenAI exige avatar e cena", transient=False)
        if photo:
            from app.services.book_profile import IDENTITY

            return await self._generate_with_refs(
                f"{IDENTITY} Corrija somente a identidade na TERCEIRA imagem (cena); "
                "PRIMEIRA = foto original, SEGUNDA = avatar de continuidade. Preserve "
                f"figurino, pose, expressao, enquadramento e cenario. Estilo: {style}.",
                [photo, character_ref, scene],
                size=settings.openai_image_size_square,
            )
        return await self._generate_with_refs(
            REFINE_SCENE_PROMPT,
            [character_ref, scene],
            size=settings.openai_image_size_square,
        )
