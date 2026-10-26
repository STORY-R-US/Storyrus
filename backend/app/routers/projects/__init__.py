"""Projetos e disparo das etapas do pipeline (respostas 202 assincronas).

Fatiado em módulos (STO-35): photos / steps / approvals / print.
Comportamento e rotas idênticos ao monolito anterior.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage, story_templates
from app.database import get_db
from app.deps import get_current_user, require_adult_user, require_registered_user
from app.models import Asset, AssetKind, Job, Project, User
from app.schemas import JobOut, ProjectCreateIn, ProjectOut, StoryTemplateOut
from app.services import book_profile
from app.services.preview_mark import display_key

from . import approvals, book_flow, photos, purchase, steps
from . import print as print_mod
from .common import get_owned_project, purge_project

router = APIRouter(prefix="/v1/projects", tags=["projects"])


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    body: ProjectCreateIn,
    user: User = Depends(require_adult_user),
    db: Session = Depends(get_db),
) -> Project:
    project = Project(
        user_id=user.id,
        style=body.style.value,
        theme=body.theme,
        book_size=body.book_size,
        cover_type=body.cover_type,
        extra_theme=(body.extra_theme or None),
        child_name=(body.child_name or None),
        child_age=body.child_age,
        dedication=(body.dedication or None),
        child_trait=(body.child_trait or None),
        child_interest=(body.child_interest or None),
        language=(body.language or "pt-BR"),
        purchase_flow={"title": body.title, "theme_description": body.theme_description},
        book_profile=book_profile.initial_profile(body) if body.gender or body.languages else None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("", response_model=list[ProjectOut])
def list_projects(
    response: Response, user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Project]:
    response.headers["Cache-Control"] = "private, no-store"
    return list(
        db.scalars(
            select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())
        )
    )


# Rota literal declarada ANTES de /{project_id} para não ser capturada como UUID.
@router.get("/story-templates", response_model=list[StoryTemplateOut])
def list_story_templates(
    user: User = Depends(get_current_user),
) -> list[dict]:
    """Catálogo de histórias prontas da plataforma (traduzidas e personalizáveis)."""
    return story_templates.list_templates()


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: uuid.UUID,
    user: User = Depends(require_registered_user),
    db: Session = Depends(get_db),
) -> Response:
    """O responsável apaga o projeto, a foto e os arquivos gerados."""
    project = get_owned_project(db, user, project_id)
    try:
        purge_project(db, project.id)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Project:
    return get_owned_project(db, user, project_id)


@router.get("/{project_id}/assets")
def project_assets(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """URLs (assinadas) dos resultados de cada etapa, para a plataforma exibir."""
    project = get_owned_project(db, user, project_id)

    def url_for(key: str | None) -> str | None:
        return storage.presign_get(key) if key else None

    def shown(asset) -> str | None:
        return storage.presign_get(display_key(db, asset)) if asset is not None else None

    character_url = None
    if project.character_ref and project.character_ref.get("storage_key"):
        character_url = url_for(project.character_ref["storage_key"])

    realistic = db.scalar(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.REALISTIC.value)
        .order_by(Asset.created_at.desc())
    )
    realistic_url = url_for(realistic.storage_key) if realistic else None

    photos = db.scalars(
        select(Asset).where(Asset.project_id == project.id, Asset.kind == AssetKind.PHOTO.value)
    ).all()
    pages = db.scalars(
        select(Asset).where(
            Asset.project_id == project.id, Asset.kind == AssetKind.PAGE_IMAGE.value
        )
    ).all()
    pages = sorted(pages, key=lambda a: ((a.meta or {}).get("page") or 0, str(a.created_at)))
    page_images = [shown(a) for a in pages]

    cover = db.scalar(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.COVER.value)
        .order_by(Asset.created_at.desc())
    )
    cover_url = shown(cover)

    in_hand = db.scalar(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.IN_HAND.value)
        .order_by(Asset.created_at.desc())
    )
    in_hand_url = shown(in_hand)

    ebook_url = url_for(project.ebook_url) if project.ebook_url else None

    storyboard = db.scalar(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.STORYBOARD.value)
        .order_by(Asset.created_at.desc())
    )
    storyboard_url = url_for(storyboard.storage_key) if storyboard else None

    video_url = None
    if project.video_url:
        video_url = (
            project.video_url
            if str(project.video_url).startswith("http")
            else url_for(project.video_url)
        )

    narrated_video_url = None
    if project.narrated_video_url:
        narrated_video_url = (
            project.narrated_video_url
            if str(project.narrated_video_url).startswith("http")
            else url_for(project.narrated_video_url)
        )
    else:
        narrated_asset = db.scalar(
            select(Asset)
            .where(
                Asset.project_id == project.id,
                Asset.kind == AssetKind.NARRATED_VIDEO.value,
            )
            .order_by(Asset.created_at.desc())
        )
        if narrated_asset:
            narrated_video_url = url_for(narrated_asset.storage_key)

    # Personagens extras (URLs assinadas)
    extra_characters_out = []
    for ec in project.extra_characters or []:
        char_key = ec.get("character_storage_key")
        if char_key:
            extra_characters_out.append(
                {
                    "name": ec.get("name", ""),
                    "url": url_for(char_key) or "",
                }
            )

    preview_assets = [
        a
        for a in db.scalars(
            select(Asset)
            .where(Asset.project_id == project.id)
            .order_by(Asset.created_at, Asset.id)
        ).all()
        if (a.meta or {}).get("workflow") == 1
        and (a.meta or {}).get("role") in {"01_CAPA", "02_LIVRO_ABERTO", "03_LEITURA"}
    ]
    language = project.language or "pt-BR"
    clean_cover = next(
        (
            a
            for a in preview_assets
            if (a.meta or {}).get("role") == "01_CAPA"
            and (a.meta or {}).get("language") == language
        ),
        None,
    ) or next((a for a in preview_assets if (a.meta or {}).get("role") == "01_CAPA"), None)
    paid_book = (project.purchase_flow or {}).get("stage") in {"generating_book", "book_ready"}
    book_cover_url = url_for(clean_cover.storage_key) if clean_cover and paid_book else None

    return {
        "previews": [
            {
                **{key: value for key, value in (a.meta or {}).items() if key != "watermark_key"},
                "url": shown(a),
            }
            for a in preview_assets
        ],
        "page_versions": [
            {**(a.meta or {}), "url": url_for(a.storage_key)}
            for a in pages
            if (a.meta or {}).get("workflow") == 1
            and (a.meta or {}).get("role") in {"sem_texto", "com_texto"}
        ],
        "character_url": character_url,
        "realistic_url": realistic_url,
        "extra_characters": extra_characters_out,
        "page_images": page_images,
        "cover_url": cover_url,
        "book_cover_url": book_cover_url,
        "in_hand_url": in_hand_url,
        "ebook_url": ebook_url,
        "storyboard_url": storyboard_url,
        "video_url": video_url,
        "narrated_video_url": narrated_video_url,
        "photo_count": len(photos),
    }


@router.get("/{project_id}/jobs", response_model=list[JobOut])
def list_jobs(
    project_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Job]:
    get_owned_project(db, user, project_id)
    jobs = list(
        db.scalars(select(Job).where(Job.project_id == project_id).order_by(Job.created_at.asc()))
    )
    if any(job.status in ("PENDING", "RUNNING") for job in jobs):
        try:
            from app.workers.api_pump import kick

            kick()
        except Exception:  # noqa: BLE001 - listar jobs nao pode falhar se o pump nao acordar
            pass
    return jobs


# Ordem de include preserva o monolito: photos → steps → approvals → print.
router.include_router(photos.router)
router.include_router(steps.router)
router.include_router(approvals.router)
router.include_router(book_flow.router)
router.include_router(print_mod.router)

router.include_router(purchase.router)
