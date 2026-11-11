"""LIVRO UPDATE runtime: flat source art -> literal typography -> three final scenes."""

import hashlib
import json
import logging

from sqlalchemy import select

from app import storage
from app.ai_clients.base import ProviderError
from app.config import settings
from app.models import Asset, Job, ProjectStatus
from app.services import (
    book_design,
    composition_examples,
    editorial_profile,
    purchase_flow,
    spend_guard,
    visual_reference,
)
from app.services import book_profile as contract
from app.services.privacy import require_photo_authorization
from app.workers import book_mockups
from app.workers import editorial_render as render


def signature(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class VisualReviewError(ValueError):
    def __init__(self, message, *, scope):
        super().__init__(message)
        self.scope = scope


class Pipeline:
    def __init__(self, db, job, project, photos):
        from . import master_book as master

        self.master = master
        self.db, self.job, self.project, self.photos = db, job, project, photos
        self.profile = project.book_profile
        self.design = book_design.resolve(self.profile)
        self.project_only_references = editorial_profile.composed(self.profile)
        self.policy = editorial_profile.policy(self.profile)
        self.designed = bool(self.policy.get("referenceComposition"))
        self.demo = contract.test_mode(project) or settings.offline_fallback
        self.language = project.language or "pt-BR"
        self.reference_theme = " ".join(
            str(v or "")
            for v in (
                project.theme,
                self.profile.get("theme_description"),
                self.profile.get("locales", {}).get(self.language, {}).get("title"),
            )
        )
        self.last_review_scope = None
        self.last_review_issues = []
        self.last_art = None
        self.last_operation = None
        self.cover_continuity = None
        self.refs = [
            data
            for _, data in editorial_profile.references(
                project.style, self.profile["editorial"]["version"], art_only=True
            )
        ]
        if self.design or self.project_only_references:
            # Content-rich examples can leak their cast and props into unrelated books.
            self.refs = []
        self.base = {
            "renderer_revision": "2026-11-09.title-review.3",
            "visual_masters": self.design["reference_sha256"]
            if self.design
            else visual_reference.fingerprint(project.style, self.reference_theme)
            if self.designed
            else {},
            "visual_master_preset": self.design["id"]
            if self.design
            else self.profile.get("visual_master_preset"),
            "editorial": self.profile["editorial"],
            "photos": [render.digest(p) for p in photos],
            "style": project.style,
            "continuity": {
                k: self.profile.get(k)
                for k in ("visual_identity", "costume", "palette", "characters")
            },
            "language": self.language,
            "reference_manifest": contract.photo_manifest(project, photos),
            "cast_contract": {
                "protagonist": project.child_name,
                "additional_characters": self.profile.get("characters", ""),
                "additional_photo_names": [ec.get("name") for ec in project.extra_characters or []],
                "solo": not self.profile.get("characters") and not project.extra_characters,
                "rule": "Only the protagonist and explicitly requested companions. Ignore people in photo backgrounds. With no companions, show the protagonist alone; never invent a child, relative, helper or animal.",
            },
        }
        if self.design:
            self.base["book_design"] = {"id": self.design["id"], "sha256": self.design["sha256"]}
        if self.designed:
            self.base["continuity"]["scene_world"] = self.profile.get("scene_world")

    def alignment(self, title=False):
        return self.policy["typography"]["coverAlignment" if title else "bodyAlignment"]

    def text_region(self, title=False):
        return self.policy.get("referenceComposition", {}).get(
            "coverRegion" if title else "bodyRegion",
            [0.09, 0.06, 0.91, 0.29] if title else [0.07, 0.07, 0.93, 0.29],
        )

    def text_instruction(self, title=False):
        if title and self.design:
            return (
                "Título no bloco definido pelo modelo completo do Catálogo: "
                + self.design["cover"]["placement"]
            )
        if title:
            return (
                "Título centralizado dentro do bloco superior direito."
                if self.designed and self.policy["typography"]["coverPlacement"] != "upper_center"
                else "Título superior centralizado."
            )
        return (
            "Versos centralizados no topo da página, conforme o layout."
            if self.alignment() == "center"
            else "Versos alinhados à esquerda."
        )

    def cached(self, key):
        return self.db.scalar(
            select(Asset).where(
                Asset.project_id == self.project.id,
                Asset.kind == "editorial_source",
                Asset.storage_key == key,
            )
        )

    def rejected_cover_source(self, name, action, plan):
        """Recover the ORIGINAL matching source, never a blurred repair or composed cover."""
        current = self.master._payload(self.job)
        if name != "cover" or current.get("title_refresh"):
            return None
        base_inputs = {"action": action, "title": True, "plan": plan}
        # stage() only adds a requested revision when the project already has one.
        # Recompose the same possible keys so a plain cover-only retry (the normal
        # Studio path, without payload["image"]) can still find its rejected art.
        revision = self.revision_for("cover:art")
        revision_inputs = (
            {
                "requested_revision": {
                    "id": revision["art_revision"],
                    "adjustment": revision.get("art_adjustment", ""),
                }
            }
            if revision.get("art_revision")
            else {}
        )
        previous_jobs = self.db.scalars(
            select(Job)
            .where(Job.project_id == self.project.id, Job.type == "EBOOK", Job.id != self.job.id)
            .order_by(Job.created_at.desc())
            .limit(5)
        ).all()
        for previous in previous_jobs:
            task = (previous.result or {}).get("editorial_tasks", {}).get("cover:art", {})
            if not task:
                continue
            # Never resurrect a rejected scene from before a newer completed cover.
            if previous.status != "FAILED":
                return None
            payload = self.master._payload(previous)
            if payload.get("title_refresh"):
                continue
            if payload.get("adjustment", "") != current.get("adjustment", ""):
                # A new requested scene adjustment is not a retry of this source.
                continue
            candidates = [
                base_inputs,
                {**base_inputs, **revision_inputs},
                {
                    **base_inputs,
                    "requested_revision": {
                        "id": str(previous.id),
                        "adjustment": payload.get("adjustment", ""),
                    },
                },
            ]
            expected = {
                f"editorial/{self.project.id}/{signature([self.base, 'cover:art', inputs])}.png"
                for inputs in candidates
            }
            if (
                task.get("input_key") not in expected
                or task.get("failure_category") != "visual_review"
            ):
                continue
            for rejected in (previous.result or {}).get("rejected_candidates", []):
                asset = self.db.scalar(
                    select(Asset).where(
                        Asset.project_id == self.project.id,
                        Asset.kind == "editorial_rejected",
                        Asset.storage_key == rejected.get("storage_key"),
                    )
                )
                if not asset:
                    continue
                meta = asset.meta or {}
                # Legacy reports explicitly disclosed that only a crop was
                # inspected. Context hashes still have to match exactly, and
                # repaired art must pass every visual check again.
                crop_only = meta.get("review_scope") == "text_reserve" or (
                    meta.get("review_scope") is None
                    and meta.get("role") is None
                    and any(
                        "crop" in item.lower()
                        for item in meta.get("validation", {}).get("limitations", [])
                    )
                )
                if crop_only and meta.get("inspection_region"):
                    return storage.get_bytes(asset.storage_key)
        return None

    def record(self, name, state, **values):
        self.job.result = {
            **(self.job.result or {}),
            "editorial_tasks": {
                **(self.job.result or {}).get("editorial_tasks", {}),
                name: {"state": state, **values},
            },
        }
        self.db.commit()

    def _generation_guard_key(self, key):
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    def _unknown_generation(self, key):
        guards = (self.project.book_profile or {}).get("generation_outcomes_unknown") or {}
        return guards.get(self._generation_guard_key(key))

    def _remember_unknown_generation(self, key, exc, *, stage):
        profile = dict(self.project.book_profile or {})
        guards = dict(profile.get("generation_outcomes_unknown") or {})
        guards[self._generation_guard_key(key)] = {
            "stage": stage,
            "request_id": exc.request_id,
            "client_request_id": exc.client_request_id,
            "status_code": exc.status_code,
        }
        self.project.book_profile = {
            **profile,
            "generation_outcomes_unknown": dict(list(guards.items())[-128:]),
        }
        self.profile = self.project.book_profile
        self.db.commit()

    def account(self, result, label):
        self.master._account(self.db, self.job, result, label)
        self.db.commit()

    def guard(self, *, billable=True):
        require_photo_authorization(self.db, self.project.id)
        if billable:
            spend_guard.assert_vendor_allowed(self.db)

    def revision_for(self, name):
        role = (
            "01_CAPA"
            if name.startswith("cover")
            else "02_LIVRO_ABERTO"
            if name.startswith(("preview:", "spread"))
            else "03_LEITURA"
            if name == "reading"
            else None
        )
        return self.project.book_profile.get("editorial_revisions", {}).get(role, {})

    async def stage(self, name, inputs, build, *, billable=True):
        """Immutable intermediates survive worker/job retries, scoped to all relevant inputs."""
        if self.designed and name.endswith(":text"):
            # Recompose typography locally after a layout fix, retaining purchased raw art.
            inputs = {**inputs, "text_layout_revision": render.TEXT_LAYOUT_REVISION}
        revision = self.revision_for(name)
        if revision:
            if not name.endswith(":art"):
                inputs = {**inputs, "requested_revision": revision}
            elif revision.get("art_revision"):
                inputs = {
                    **inputs,
                    "requested_revision": {
                        "id": revision["art_revision"],
                        "adjustment": revision.get("art_adjustment", ""),
                    },
                }
        key = f"editorial/{self.project.id}/{signature([self.base, name, inputs])}.png"
        cached = self.cached(key)
        if (
            not cached
            and self.designed
            and name.endswith(":template")
            and "generation_job" in inputs
        ):
            # A failed composition must not purchase the same blank product scene
            # again. Reconstruct prior keys using identical photos/profile/revision
            # and inputs; only the bookkeeping job ID may differ.
            previous_ids = self.db.scalars(
                select(Job.id)
                .where(Job.project_id == self.project.id, Job.id != self.job.id)
                .order_by(Job.created_at.desc())
                .limit(20)
            ).all()
            for previous_id in previous_ids:
                previous_key = f"editorial/{self.project.id}/{signature([self.base, name, {**inputs, 'generation_job': str(previous_id)}])}.png"
                cached = self.cached(previous_key)
                if cached:
                    key = previous_key
                    break
        if cached:
            data = storage.get_bytes(key)
            if render.digest(data) != cached.meta["sha256"]:
                raise ProviderError("Arte editorial armazenada inválida", transient=False)
            self.record(name, "passed", storage_key=key, resumed=True)
            return data, cached.meta
        unknown = self._unknown_generation(key) if billable else None
        if unknown:
            raise ProviderError(
                "GENERATION_OUTCOME_UNKNOWN",
                transient=False,
                retry_safe=False,
                outcome_unknown=True,
                status_code=unknown.get("status_code"),
                request_id=unknown.get("request_id"),
                client_request_id=unknown.get("client_request_id"),
            )
        # Feedback and source art belong only to this task, never the previous scene.
        self.last_review_scope = None
        self.last_review_issues = []
        self.last_art = None
        self.last_operation = None
        previous = (self.job.result or {}).get("editorial_tasks", {}).get(name, {})
        attempts = previous.get("attempts", 0) if previous.get("input_key") == key else 0
        maximum = 1 + min(
            2,
            max(
                0,
                self.policy["production"]["retryPolicy"][
                    "proposedDefaultMaxRetriesAfterFirstAttempt"
                ],
            ),
        )
        # Current layouts solve placement locally. A genuine quality rejection
        # must not buy another image automatically.
        if self.designed or name.endswith(":art"):
            maximum = 1
        elif name in {"spread", "reading"}:
            # A mockup quality/composition failure must not buy another template
            # automatically. A new user retry is the explicit boundary for another
            # paid image-generation attempt.
            maximum = 1
        attempt = attempts
        while attempt < maximum:
            attempt += 1
            self.record(
                name,
                "running",
                attempts=attempt,
                input_key=key,
                billable=billable,
            )
            try:
                self.guard(billable=billable)
                data, meta = await build(attempt)
                require_photo_authorization(self.db, self.project.id)
                meta = {
                    **meta,
                    "storage_key": key,
                    "sha256": render.digest(data),
                    "stage": name,
                    "editorial": self.profile["editorial"],
                    "workflow": 2,
                }
                storage.put_bytes(key, data, "image/png")
                self.db.add(
                    Asset(
                        project_id=self.project.id,
                        kind="editorial_source",
                        storage_key=key,
                        meta=meta,
                    )
                )
                self.record(name, "passed", attempts=attempt, storage_key=key)
                return data, meta
            except (ValueError, ProviderError) as exc:
                if isinstance(exc, ProviderError):
                    # Network/provider retries belong to the worker. They are not
                    # visual rejections and must not consume the composition budget.
                    state = "outcome_unknown" if exc.outcome_unknown else "provider_failed"
                    if exc.outcome_unknown:
                        self._remember_unknown_generation(key, exc, stage=name)
                    self.record(
                        name,
                        state,
                        attempts=attempt - 1,
                        input_key=key,
                        provider_status=exc.status_code,
                        transient=exc.transient,
                        retry_safe=exc.retry_safe,
                        outcome_unknown=exc.outcome_unknown,
                        request_id=exc.request_id,
                        client_request_id=exc.client_request_id,
                    )
                    raise ProviderError(
                        f"Etapa editorial {name}: {exc}",
                        transient=exc.transient,
                        status_code=exc.status_code,
                        retry_safe=exc.retry_safe,
                        outcome_unknown=exc.outcome_unknown,
                        request_id=exc.request_id,
                        client_request_id=exc.client_request_id,
                    ) from exc
                logging.getLogger(__name__).warning(
                    "editorial_technical_failure stage=%s attempt=%s reason=%s",
                    name,
                    attempt,
                    str(exc)[:300],
                )
                self.record(
                    name,
                    "failed",
                    attempts=attempt,
                    input_key=key,
                    reason=type(exc).__name__,
                    detail=str(exc)[:300],
                    failure_category=(
                        "visual_review"
                        if "Revisão visual" in str(exc)
                        else "text_overflow"
                        if "não cabe" in str(exc)
                        else "text_region"
                        if "Região" in str(exc)
                        else "square_art"
                        if "quadrada" in str(exc)
                        else "invalid_render_input"
                    ),
                )
                if attempt == maximum:
                    if self.designed or isinstance(exc, VisualReviewError):
                        raise ProviderError(
                            (
                                f"Capa ou ilustração reprovada em {name}: {str(exc)[:240]}"
                                if "Revisão visual" in str(exc) or "Região do título" in str(exc)
                                else f"Falha técnica na montagem de {name}: {str(exc)[:240]}"
                            ),
                            transient=False,
                        ) from exc
                    raise ProviderError(
                        f"Etapa {name} reprovada após {maximum} tentativas; revise a composição",
                        transient=False,
                    ) from exc
        raise ProviderError(f"Etapa {name} esgotou as tentativas deste trabalho", transient=False)

    async def review(self, data, prompt, *, cover=None, technical=None, full_image_prompt=None):
        self.last_review_scope = None
        self.last_review_issues = []
        if self.demo:
            return {"status": "demo"}
        if getattr(self, "designed", False):
            # Cover/source-art contract checks are mandatory. Other assembled
            # mockups retain technical checks and await explicit user approval.
            import io

            from PIL import Image

            with Image.open(io.BytesIO(data)) as image:
                if image.format != "PNG":
                    raise ValueError("Preview must be a valid PNG")
                image.verify()
            if not prompt.startswith(("ARTE_BASE:", "CAPA_PLANA:")):
                return {
                    "status": "awaiting_user_review",
                    "reviewer": "user",
                    "method": "technical_integrity_only",
                }
        self.guard()
        template = (
            editorial_profile._root(self.profile["editorial"]["version"])
            / "prompts/03_REVISAO_VISUAL.txt"
        ).read_text(encoding="utf-8")
        if prompt.startswith(("ARTE_BASE:", "CAPA_PLANA:", "PAGINA_INTERNA:")):
            # Flat intermediates are not physical-book mockups. The generic final
            # scene rubric asks for book geometry and lettering absent at this stage.
            template = (
                "Revise somente OUTPUT conforme a tarefa declarada no início. "
                "Compare identidade, idade, anatomia e figurino com as fotos originais; "
                "confira acabamento, ação solicitada e continuidade. "
                "ARTE_BASE deve ser uma ilustração contínua sem letras; a ausência de "
                "texto é obrigatória. Avalie a reserva de leitura medida. "
                "CAPA_PLANA e PAGINA_INTERNA devem conter somente o texto literal "
                "solicitado, legível e sem sobreposição. "
                "São imagens planas: não exigir livro físico, lombada, mãos segurando "
                "um livro ou perspectiva. Não exigir título na página interna. "
                "Use os resultados técnicos para geometria e tipografia: "
                "{{TECHNICAL_VALIDATION_JSON}}. Política pertinente: {{EDITORIAL_POLICY_JSON}}. "
                "Reprove defeitos concretos ou critérios obrigatórios inconclusivos."
            )
        for marker, value in {
            "RESULT_IMAGE": "OUTPUT",
            "ORIGINAL_REFERENCE_IMAGES": self.base["reference_manifest"],
            "FINAL_COVER_IMAGE": "EXACT_COVER" if cover else None,
            "SCENE_PLAN_JSON": prompt,
            "LOCKED_TEXT_JSON": prompt,
            "EDITORIAL_POLICY_JSON": (
                {key: self.policy[key] for key in ("identity", "visual", "layout", "typography")}
                if prompt.startswith(("ARTE_BASE:", "CAPA_PLANA:", "PAGINA_INTERNA:"))
                else self.policy
            ),
            "TECHNICAL_VALIDATION_JSON": {
                "method": "deterministic typography and source projection; inspect visual result separately",
                **(technical or {}),
            },
        }.items():
            template = template.replace("{{" + marker + "}}", json.dumps(value, ensure_ascii=False))
        prompt += (
            "\n"
            + template
            + (
                "\nAvalie SOMENTE a tarefa atual: ARTE_BASE não possui letras; PAGINA_INTERNA é plana "
                "e só contém seus versos; CAPA_PLANA só o título. Regras de livro físico e capa na leitura "
                "só se aplicam aos mockups correspondentes. Adapte o resultado ao contrato da API: "
                "JSON {valid:boolean, issues:[strings], limitations:[strings]}; incerteza implica valid:false."
            )
        )
        result = (
            await self.master._pkg()
            .get_text_provider()
            .validate_editorial_preview(
                data=data,
                photos=self.photos,
                cover=cover,
                prompt=prompt,
                style_refs=self.refs,
                full_image_prompt=full_image_prompt,
                inspection_region=(technical or {})
                .get("typography", {})
                .get("ink_region_with_margin"),
            )
        )
        self.account(result, "Revisão editorial")
        report = json.loads(result.text)
        if (
            not isinstance(report, dict)
            or report.get("valid") is not True
            or report.get("issues") != []
            or not isinstance(report.get("limitations"), list)
            or any(not isinstance(item, str) for item in report["limitations"])
        ):
            logging.getLogger(__name__).warning(
                "editorial_review_rejected job=%s role=%s issues=%s",
                self.job.id,
                prompt.split(":", 1)[0],
                str(report.get("issues", []) if isinstance(report, dict) else "invalid report")[
                    :1800
                ],
            )
            require_photo_authorization(self.db, self.project.id)
            key = storage.new_key(self.project.id, "editorial-rejected", "png")
            storage.put_bytes(key, data, "image/png")
            self.db.add(
                Asset(
                    project_id=self.project.id,
                    kind="editorial_rejected",
                    storage_key=key,
                    meta={
                        "workflow": 2,
                        "validation": report,
                        "review_scope": result.meta.get("review_scope"),
                        "role": prompt.split(":", 1)[0],
                        "inspection_region": (technical or {})
                        .get("typography", {})
                        .get("ink_region_with_margin"),
                        "editorial": self.profile["editorial"],
                    },
                )
            )
            self.job.result = {
                **(self.job.result or {}),
                "rejected_candidates": [
                    *(self.job.result or {}).get("rejected_candidates", []),
                    {"storage_key": key, "report": report},
                ],
            }
            self.db.commit()
            self.last_review_scope = result.meta.get("review_scope")
            self.last_review_issues = report.get("issues", []) if isinstance(report, dict) else []
            reasons = "; ".join(str(issue) for issue in self.last_review_issues)[:400]
            raise VisualReviewError(
                "Revisão visual reprovada ou inconclusiva" + (": " + reasons if reasons else ""),
                scope=result.meta.get("review_scope") or "full_image",
            )
        return {**report, "status": "valid"}

    async def art(self, name, action, *, title=False, value=None):
        if self.designed:
            try:
                render.text(
                    self.master._offline_png("layout", palette=((255, 255, 255), (255, 255, 255))),
                    value,
                    self.profile,
                    title=title,
                    region=self.text_region(title),
                    alignment=self.alignment(title),
                    measure_only=True,
                    readable=not title,
                )
            except render.TextLayoutError as exc:
                raise ProviderError(str(exc), transient=False) from exc
        plan_key = signature([self.base, name, action])
        plan = self.profile.get("scene_plans", {}).get(plan_key)
        if not plan:
            if self.demo or self.designed:
                plan = {
                    "action": action,
                    "text_region": [0.09, 0.06, 0.91, 0.29] if title else [0.07, 0.07, 0.93, 0.29],
                    "alignment": self.alignment(title),
                    "protected_content": [],
                }
            else:
                self.guard()
                planned = (
                    await self.master._pkg()
                    .get_text_provider()
                    .plan_editorial_page(
                        action=action,
                        text=value,
                        policy={
                            **self.policy,
                            "composition_guidance": composition_examples.context(
                                "cover" if title else "page", self.alignment(title)
                            ),
                        },
                        continuity=self.base["continuity"],
                        title=title,
                    )
                )
                self.account(planned, "Planejamento de página")
                plan = json.loads(planned.text)
            if not isinstance(plan, dict):
                raise ProviderError("Plano editorial inválido", transient=False)
            if self.designed:
                plan = {
                    **plan,
                    "text_region": self.text_region(title),
                    "alignment": self.alignment(title),
                }
            render.validate_region(plan.get("text_region"))
            if plan.get("alignment") not in {"left", "center"} or not plan.get("action"):
                raise ProviderError("Planejamento editorial incompleto", transient=False)
            if title and (plan["alignment"] != "center" or plan["text_region"][1] > 0.15):
                raise ProviderError("Título fora do topo centralizado", transient=False)
            # Fit the literal copy before paying for image generation. Replan the scene,
            # not the words or font size, when a locked passage needs more space.
            for layout_attempt in range(3):
                try:
                    render.text(
                        self.master._offline_png(
                            "layout", palette=((255, 255, 255), (255, 255, 255))
                        ),
                        value,
                        self.profile,
                        title=title,
                        region=plan["text_region"],
                        alignment=plan["alignment"],
                    )
                    break
                except ValueError as exc:
                    if self.designed:
                        raise ProviderError(str(exc), transient=False) from exc
                    # Vision can propose a box too small even for a short stanza.
                    # Calibrate a larger safe box using the actual font before
                    # requesting another plan or paying for any image generation.
                    calibrated = False
                    for candidate_region in (
                        [self.text_region(title)]
                        if self.designed
                        else (
                            [[0.09, 0.06, 0.91, 0.29]]
                            if title
                            else [[0.07, 0.07, 0.93, 0.37], [0.07, 0.07, 0.93, 0.47]]
                        )
                    ):
                        try:
                            render.text(
                                self.master._offline_png(
                                    "layout", palette=((255, 255, 255), (255, 255, 255))
                                ),
                                value,
                                self.profile,
                                title=title,
                                region=candidate_region,
                                alignment=self.alignment(title),
                            )
                            plan = {
                                **plan,
                                "text_region": candidate_region,
                                "alignment": self.alignment(title),
                            }
                            calibrated = True
                            break
                        except ValueError:
                            continue
                    if calibrated:
                        break
                    if self.demo or layout_attempt == 2:
                        raise ProviderError(
                            "Texto aprovado não cabe no layout; composição bloqueada",
                            transient=False,
                        ) from exc
                    self.guard()
                    revised = (
                        await self.master._pkg()
                        .get_text_provider()
                        .plan_editorial_page(
                            action={
                                "scene": action,
                                "layout_correction": "Reserve a larger natural reading area without covering characters; do not rewrite text or shrink font",
                                "previous_region": plan["text_region"],
                            },
                            text=value,
                            policy=self.policy,
                            continuity=self.base["continuity"],
                            title=title,
                        )
                    )
                    self.account(revised, "Recomposição do layout")
                    plan = json.loads(revised.text)
                    render.validate_region(plan.get("text_region"))
                    if plan.get("alignment") not in {"left", "center"} or (
                        title and (plan["alignment"] != "center" or plan["text_region"][1] > 0.15)
                    ):
                        raise ProviderError(
                            "Recomposição fora do padrão editorial", transient=False
                        )
            contract.update(
                self.project, scene_plans={**self.profile.get("scene_plans", {}), plan_key: plan}
            )
            self.profile = self.project.book_profile
            self.db.commit()

        async def build(attempt):
            operation = "generate_flat_art"
            source_sha256 = None
            region = plan["text_region"]
            _, planned_layout = render.text(
                self.master._offline_png("layout", palette=((255, 255, 255), (255, 255, 255))),
                value,
                self.profile,
                title=title,
                region=region,
                alignment=plan["alignment"],
            )
            safe_region = planned_layout["ink_region_with_margin"]
            template = (
                editorial_profile._root(self.profile["editorial"]["version"])
                / "prompts/02_ARTE_E_CENAS.txt"
            ).read_text(encoding="utf-8")
            for marker, content in {
                "EDITORIAL_POLICY_JSON": {
                    key: self.policy[key] for key in ("identity", "visual", "layout")
                },
                "SCENE_PLAN_JSON": {
                    "action": plan["action"],
                    "continuity": self.base["continuity"],
                },
                "LOCALE": self.language,
                "ART_STAGE": "flat_cover" if title else "flat_left_page",
                "REFERENCE_MANIFEST_JSON": self.base["reference_manifest"],
                "TEXT_SAFE_REGIONS_JSON": safe_region,
                "PROTECTED_REGIONS_JSON": plan.get("protected_content", []),
                "FINAL_COVER_ASSET_ID": None,
            }.items():
                template = template.replace(
                    "{{" + marker + "}}", json.dumps(content, ensure_ascii=False)
                )
            # The supplied template documents all stages; send only the current stage's clause.
            template = "\n".join(
                line
                for line in template.splitlines()
                if not line.startswith("As referências mencionadas no manifesto")
                and (
                    not line.startswith("- ")
                    or not any(
                        tag in line
                        for tag in (
                            "flat_cover:",
                            "flat_left_page /",
                            "open_book_scene:",
                            "reading_scene:",
                        )
                    )
                    or line.startswith("- flat_cover:" if title else "- flat_left_page /")
                )
            )
            revision_role = (
                "01_CAPA"
                if name.startswith("cover")
                else "02_LIVRO_ABERTO"
                if name.startswith("preview:")
                else None
            )
            adjustment = (
                self.project.book_profile.get("editorial_revisions", {})
                .get(revision_role, {})
                .get("art_adjustment", "")
            )
            prompt = (
                template
                + "\n"
                + (
                    "Gere UMA arte PLANA quadrada, borda a borda. Sem simulação de livro, "
                    "dobras ou arte apoiada numa mesa de apresentação. O mobiliário da história "
                    "é permitido. Sem moldura, letras, números, logotipo ou marca-d'água. Fotos originais definem "
                    "identidade e idade, incluindo adultos e animais; somente elenco solicitado. "
                    "Mantenha o figurino definido. Cenário editorial suave, sem pele plástica. "
                    "Reserve naturalmente a região normalizada de texto, sem faixas ou degradês, "
                    "sem rostos, mãos ou ação importante. Personagens com destaque e proporções "
                    "naturais; não transformá-los em pequenas figuras distantes. "
                    + (
                        "COMPOSIÇÃO DE CAPA: deixe o quarto superior da imagem como ambiente "
                        "natural livre (parede, céu ou cenário suave), sem cabeça, cabelo, mãos "
                        "ou objetos importantes. O topo de QUALQUER cabeça deve começar somente "
                        "ABAIXO de 25% da altura da imagem. Enquadre a ação abaixo desse espaço "
                        "editorial, com proporções naturais; não copie o enquadramento de retrato "
                        "da foto. A foto é referência de identidade, não de composição. "
                        if title and not self.designed
                        else ""
                    )
                    + json.dumps(
                        {
                            "action": plan["action"],
                            "requested_adjustment": adjustment,
                            "text_region": safe_region,
                            "corrections_from_previous_attempt": self.last_review_issues,
                            "brief": self.base["continuity"],
                            "name": self.project.child_name,
                            "age": self.project.child_age,
                        },
                        ensure_ascii=False,
                    )
                )
            )
            if title and not self.designed:
                prompt += (
                    "\nFINAL FRAMING REQUIREMENT, overriding any reference-photo framing or "
                    "conflicting scene-plan pose: this is a square book cover with room for a "
                    "title. The TOP QUARTER (y=0 through y=256 on a 1024px canvas) must show "
                    "ONLY natural background. Place the entire head and hair BELOW y=280, "
                    "with the main person and action in the lower three quarters. Show the "
                    "same person at natural proportions. Change camera framing and pose, "
                    "preserve identity and clothing. No lettering, banner or artificial panel."
                )
            prompt += (
                "\nFINAL OUTPUT: ONE continuous generated scene only. Reference images are "
                "INPUTS, never elements to print in the scene. Do NOT include the original "
                "photograph, inset portraits, thumbnails, comparison pictures, reference sheets, "
                "photo frames, white dividers, collages or before/after panels anywhere in the "
                "output. All input photographs remain invisible references. No letters or text."
            )
            if self.designed:
                prompt += (
                    "\nART DIRECTION: "
                    + self.policy["visual"]["artDirection"]
                    + f"\nThe FIRST {len(self.photos)} images are the original identity photographs; "
                    f"the LAST {len(self.refs)} images show STYLE ONLY, not cast or text to copy. "
                    + (
                        (
                            "COVER DESIGN: reserve the measured upper-center title region across "
                            "the cover width. Compose prominent recognizable people and meaningful "
                            "action below it, with natural proportions and no overlap with faces. "
                            "Use vibrant luminous colors, natural skin and balanced contrast."
                            if self.policy["typography"]["coverPlacement"] == "upper_center"
                            else (
                                "COVER DESIGN: compose the recognizable person prominently on the LEFT, "
                                "head near the upper-left, and the meaningful activity and illustrated "
                                "objects on the RIGHT and lower area. Reserve ONLY the measured upper-right "
                                "title block. Do not create an empty strip across the whole top or move "
                                "the entire person down. Use a rich, coherent illustrated environment, "
                                "natural expression, soft light and inviting color."
                            )
                        )
                        if title
                        else "INTERIOR DESIGN: four short centered verses occupy the upper central "
                        "reading space; illustrate the specific action below. Show the task and "
                        "its changing result, not just a portrait beside a laptop. Keep the same "
                        "illustrated setting, objects, outfit and palette across the two pages. "
                        "For computer learning use a creative visual activity, flowers/colors and "
                        "clear drawing/saving icons when appropriate; no coding unless requested."
                    )
                )
            prompt += (
                "\nCOMPOSITION EXAMPLES GUIDE (layout only, not identity or story content): "
                + json.dumps(
                    composition_examples.context(
                        "cover" if title else "page", self.alignment(title)
                    ),
                    ensure_ascii=False,
                )
            )
            if self.designed:
                prompt += (
                    "\nFINAL PAGE CONTRACT: this image IS the entire printed page, edge to edge. "
                    "The server overlays the exact approved text directly on its measured quiet "
                    "background region. Continue the illustrated environment behind and around "
                    "that region; never create a separate panel, blank paper band, inset picture "
                    "or ivory frame. Keep people large and recognizable, with the likeness, age, "
                    "facial features and skin tone from the project's original photos. "
                    "Use the selected finish consistently across cover, pages and reading scene; "
                    "never apply a generic watercolor/sepia filter to the person's face. "
                    "Reserve ONLY the measured text rectangle, not an additional empty strip. "
                    "Never draw letters, borders or a physical book."
                )
            if self.design:
                prompt = (
                    book_design.prompt(
                        self.design,
                        "cover"
                        if title
                        else "preview_page"
                        if name.startswith("preview:")
                        else "illustrated_page",
                        action,
                        text_region=safe_region,
                    )
                    + "\nGenerate ONE square flat full-bleed illustration, no book mockup, spine, letters or example words. Respect the measured text rectangle as natural quiet scenery, free of faces, hair and hands. Use the original project photos and continuity manifest: "
                    + json.dumps(self.base["reference_manifest"], ensure_ascii=False)
                    + "\nPROJECT CONTINUITY: "
                    + json.dumps(self.base["continuity"], ensure_ascii=False)
                )
                revision = self.revision_for(name)
                prompt += "\n" + json.dumps(
                    {
                        "requested_adjustment": revision.get(
                            "art_adjustment", revision.get("adjustment", "")
                        )
                    },
                    ensure_ascii=False,
                )
            visual_master = (
                None
                if self.project_only_references
                else book_design.reference(self.design, "cover" if title else "page")
                if self.design
                else (
                    visual_reference.load(
                        "cover" if title else "page", self.project.style, self.reference_theme
                    )
                    if self.designed
                    else None
                )
            )
            if visual_master:
                prompt += (
                    "\nLAST ATTACHED IMAGE is the selected catalog design only, never a cast photo. "
                    "Use its composition and the finish prescribed above. Original project photos "
                    "define identity; any approved project cover defines this book's continuity. "
                    "Never copy the example words or draw its physical binding on this flat artwork."
                    if self.design
                    else (
                        "\nLAST ATTACHED IMAGE = VISUAL MASTER, for composition, finish and visual identity "
                        "of the book series ONLY. Match its lifelike faces integrated in softly illustrated "
                        "surroundings, rich coordinated color and full-page scene. It is NOT a cast photo. "
                        "Do NOT copy its face, person, name, words, computer, flowers or props unless "
                        "requested in the current story. ORIGINAL project photos alone define people. "
                        "The master may show a physical book/spread: generate only ONE flat page, "
                        "without its spine, fold, border or existing lettering. Respect this page's "
                        "measured text region and current action. Any preceding approved cover "
                        "reference defines this project's wardrobe, palette and illustrated setting; "
                        "keep that continuity while illustrating the new action."
                    )
                )
            prompt += "\nAUTHORIZED CAST: " + json.dumps(
                self.base["cast_contract"], ensure_ascii=False
            )
            if title:
                prompt += "\nSINGLE FRONT COVER ONLY: one continuous square front face, no open book, spread, central gutter, diptych or two facing pages."
                prompt += (
                    "\nRECOMPOSE THE SCENE: original photos define identity and clothing only. "
                    "Change pose, framing and setting to depict the requested activity. "
                    "Do not reproduce a selfie, pasted photograph, rectangular portrait, "
                    "white frame, separate paper panel, drop-shadow inset or background from the source photo. "
                    "The illustration fills the entire canvas and the title reserve is part of that same scenery. "
                    "\nMANDATORY COVER FRAMING — takes precedence over tight framing in any "
                    "photo, scene plan or earlier composition instruction. Use a medium-wide "
                    "story scene viewed at the protagonist's eye level, showing the whole head, "
                    "shoulders, torso, both arms and the objects needed for the requested activity. "
                    "The face is recognizable at a natural size; avoid a face-filling close-up, "
                    "selfie, passport portrait or oversized head. A single person's complete head "
                    "including hair or hat should occupy roughly 20–24% of the canvas height. "
                    "Do not crop the hat, hair, hands or activity at the canvas edges. "
                    "Coordinates below are normalized from 0 to 1, with origin at top-left. "
                    "The server will place the title inside this exact rectangle: "
                    + json.dumps(safe_region)
                    + ". Keep all characters, their clothing, hair, hats, hands and meaningful "
                    "objects outside it, with generous visible breathing room. "
                    + (
                        f"Place the very TOP of every head, INCLUDING the entire hat or hair, "
                        f"at or below y={max(0.40, safe_region[3] + 0.16):.3f}. "
                        "Arrange faces, torsos and the activity in the lower part of the scene. "
                        if self.alignment(True) == "center" and self.text_region(True)[0] < 0.25
                        else (
                            f"Place the character group on the LEFT, with its rightmost head/hair "
                            f"edge left of x={max(0.0, safe_region[0] - 0.08):.3f}; if it cannot "
                            f"fit naturally beside the title, place the entire heads below "
                            f"y={max(0.40, safe_region[3] + 0.16):.3f} instead. "
                        )
                    )
                    + "Fill the title area with the SAME room, wall, sky or vegetation that "
                    "continues behind the rest of the scene, with natural depth and lighting. "
                    "It is scenery, never a blank white band, separate panel, frame or inserted photo. "
                    "Show ONE concrete activity from the requested story, with a readable action "
                    "and visible relevant result; use only objects justified by that activity. "
                    "Only explicitly requested companions may appear. Do not invent a helper, "
                    "relative, animal, helicopter or other vehicle to decorate the scene. "
                    "Preserve facial identity, age, skin tone and natural proportions from the "
                    "project photos while changing their pose and background. Incidental logos "
                    "or words on clothing must become plain fabric in the same color. "
                    "Background and illustration reach all four edges of this ONE flat cover. "
                    "Do not draw any title or lettering at this art stage; the server composes "
                    "the exact project title into the reserved scenery afterward."
                )
            if not title:
                prompt += (
                    "\nFINAL INTERIOR FRAMING: reserve the measured reading rectangle "
                    + json.dumps(safe_region)
                    + " in normalized [left, top, right, bottom] coordinates as natural quiet "
                    "background. Place ALL heads, hair, faces, hands and the important action "
                    f"below y={max(0.38, safe_region[3] + 0.12):.3f}, including hats and raised hands. "
                    "Use a medium-wide view with the whole head, shoulders and meaningful activity "
                    "visible. Keep the camera far enough away to fit the action naturally; "
                    "do not solve the layout by cropping the head or shrinking only the face. "
                    "Preserve identity, age and natural proportions. Continue the same setting "
                    "behind the text and around the activity, with no horizontal visual division. "
                    "Do not draw text, blank panels, banners or artificial strips."
                )
            if self.project_only_references:
                prompt += "\nPROJECT-ONLY REFERENCES: all attached images belong to this project. The catalog supplies written layout and finish rules only; its example people, vehicles and story objects are not references for this scene."
            if self.demo:
                raw = self.master._offline_png(name, palette=((235, 243, 250), (255, 250, 242)))
            else:
                provider = self.master._pkg().get_image_provider()
                # Persist purchased pixels before QA. Layout retries and later jobs
                # with identical inputs must not purchase the same illustration again.
                source_context = [
                    self.base,
                    name,
                    prompt,
                    self.revision_for(name).get("art_revision"),
                ]
                candidate_key = (
                    f"editorial/{self.project.id}/{signature(source_context)}.candidate.png"
                )
                cached_candidate = self.db.scalar(
                    select(Asset).where(
                        Asset.project_id == self.project.id,
                        Asset.kind == "editorial_candidate",
                        Asset.storage_key == candidate_key,
                    )
                )
                recovered = self.rejected_cover_source(name, action, plan) if title else None
                if cached_candidate:
                    try:
                        raw = storage.get_bytes(candidate_key)
                    except Exception as exc:
                        # A missing purchased asset is not permission to buy another.
                        raise ProviderError(
                            "Arte original armazenada indisponível", transient=False
                        ) from exc
                    if render.digest(raw) != (cached_candidate.meta or {}).get("sha256"):
                        raise ProviderError("Arte original armazenada inválida", transient=False)
                    operation = "reuse_original_art"
                elif recovered:
                    raw = recovered
                    operation = "recover_original_art"
                else:
                    result = await provider.generate_scene(
                        prompt=prompt,
                        character_ref=self.photos[0],
                        photo=self.photos[0],
                        extra_refs=self.photos[1:]
                        + self.refs
                        + ([self.cover_continuity] if not title and self.cover_continuity else [])
                        + ([visual_master] if visual_master else []),
                        style=(
                            self.policy["visual"]["artDirection"]
                            if self.designed and self.project.style != "cartoon"
                            else contract.art_direction(self.project.style)
                        ),
                    )
                    self.account(result, name)
                    raw = result.image_bytes
                render.square(raw)
                if not cached_candidate:
                    require_photo_authorization(self.db, self.project.id)
                    storage.put_bytes(candidate_key, raw, "image/png")
                    self.db.add(
                        Asset(
                            project_id=self.project.id,
                            kind="editorial_candidate",
                            storage_key=candidate_key,
                            meta={"sha256": render.digest(raw), "stage": name, "reviewed": False},
                        )
                    )
                    self.db.commit()
                source_sha256 = render.digest(raw)
                self.last_operation = operation
            self.last_art = raw
            render.square(raw)
            page_composition = None
            if self.designed:
                # The generated scene already owns the full page. Preserve every pixel;
                # literal typography is overlaid without shrinking or framing the artwork.
                page_composition = {
                    "method": "full_bleed_text_overlay",
                    "source_sha256": render.digest(raw),
                    "art_box_normalized": [0, 0, 1, 1],
                    "cropped": False,
                    "scale": 1,
                }
            if not title and not self.demo and not self.designed:
                correction = None
                for layout_attempt in range(3):
                    self.guard()
                    observed = (
                        await self.master._pkg()
                        .get_text_provider()
                        .plan_editorial_page(
                            action={
                                "scene": action,
                                "reading_area": "Use observed quiet background, preferably upper left; ignore the initial region if it contains hands or action",
                                "layout_correction": correction,
                            },
                            text=value,
                            policy=self.policy,
                            continuity=self.base["continuity"],
                            title=False,
                            scene_image=raw,
                        )
                    )
                    self.account(observed, "Layout sobre a arte real")
                    try:
                        observed_plan = json.loads(observed.text)
                        if not isinstance(observed_plan, dict):
                            raise ValueError("Plano de texto inválido")
                        region = render.validate_region(observed_plan.get("text_region"))
                        if observed_plan.get("alignment") != "left":
                            raise ValueError("Texto interno precisa de alinhamento à esquerda")
                        render.text(raw, value, self.profile, region=region, alignment="left")
                        break
                    except ValueError:
                        correction = {
                            "previous_region": region,
                            "failure": "The exact text did not fit the proposed region or layout was invalid. Reserve a larger natural quiet area, left aligned, without changing text or reducing font size.",
                            "font_width_ratio": 0.032,
                            "line_height": 1.2,
                        }
                        if layout_attempt == 2:
                            # The model's proposed boxes can be invalid. Keep the
                            # preflight-fitted plan and test the measured candidate
                            # regions below against the actual image before rejecting it.
                            region = plan["text_region"]
                            break
            local_layout = None
            regions = [region]
            for region_attempt, region in enumerate(regions):
                try:
                    candidate, layout = render.text(
                        raw,
                        value,
                        self.profile,
                        title=title,
                        region=region,
                        alignment=self.alignment(title),
                        readable=self.designed and not title,
                    )
                    qa = await self.review(
                        raw,
                        "ARTE_BASE: plana quadrada sem qualquer texto, títulos ou mockup. "
                        "Examine a imagem INTEIRA: proibir fotografias de referência inseridas, "
                        "miniaturas, retratos em cantos, capas de exemplo, painéis, divisórias, "
                        "colagens e qualquer palavra. Deve existir somente uma cena contínua. "
                        "Critério obrigatório: o retângulo ink_region_with_margin deve estar livre "
                        "de cabelo, cabeça, rosto, mãos e ação importante, incluindo sua margem "
                        "inferior. Coordenadas normalizadas [esquerda, topo, direita, base], origem "
                        "no canto superior esquerdo. Avalie apenas a reserva medida, não a caixa "
                        "maior usada para quebra de linhas. Reprove qualquer invasão da reserva. "
                        + json.dumps({"ink_region_with_margin": layout["ink_region_with_margin"]})
                        + json.dumps(
                            {
                                "identity": self.base["continuity"],
                                "style": self.project.style,
                                **({"expected_action": action} if self.designed else {}),
                            }
                        ),
                        technical={"typography": layout},
                        full_image_prompt=(
                            "Full-bleed picture-book artwork with natural quiet background "
                            "prepared for a later text overlay; no reading panel or inset illustration. "
                            if page_composition
                            else ""
                        )
                        + "ARTE_BASE: One flat continuous illustration, without "
                        "letters, insets, photographs, collages or physical-book mockups. "
                        "Check identity, age, anatomy, outfit, style and the specific requested action. "
                        + json.dumps(
                            {
                                "identity": self.base["continuity"],
                                "cast_contract": self.base["cast_contract"],
                                "style": self.project.style,
                                "expected_action": action,
                            },
                            ensure_ascii=False,
                        ),
                    )
                    # A candidate region is usable only after both visual checks pass.
                    composition_review = await self.review(
                        candidate,
                        ("CAPA_PLANA" if title else "PAGINA_INTERNA")
                        + ": texto literal "
                        + (
                            "Ilustração de ponta a ponta, texto integrado ao fundo natural da cena, sem quadro ou faixa separada. "
                            if page_composition
                            else ""
                        )
                        + json.dumps(value, ensure_ascii=False)
                        + ". Sem texto sobre cabelo, rosto, mãos ou ação importante. "
                        + (
                            "Na capa Amor de Bisavó, o título deve fazer parte da imagem, "
                            "integrado ao cenário natural no alto à direita, sem faixa ou quadro. "
                            "Reprove texto sobre QUALQUER parte dos personagens, incluindo "
                            "corpo, roupas e braços, ou sem espaço de respiro ao redor das letras. "
                            if title and self.design and self.design["id"] == "family"
                            else ""
                        )
                        + self.text_instruction(title),
                        technical={"typography": layout},
                    )
                    break
                except VisualReviewError as exc:
                    # Only a structured reserve collision permits moving text.
                    # Identity, anatomy, lettering and quality failures stay blocked.
                    if exc.scope != "text_reserve":
                        raise
                    if region_attempt == 0:
                        regions.extend(
                            render.reading_region_candidates(
                                raw,
                                value,
                                self.profile,
                                region,
                                title=title,
                                alignment=self.alignment(title),
                            )[1:]
                        )
                    if region_attempt == len(regions) - 1:
                        raise
                    local_layout = {
                        "method": "text_only_reserve_repair",
                        "source_pixels_unchanged": True,
                        "original_region": plan["text_region"],
                    }
            return raw, {
                "validation": qa,
                "composition_review": composition_review,
                "composition_sha256": render.digest(candidate),
                "text_region": region,
                "operation": operation,
                "source_sha256": source_sha256,
                "page_composition": page_composition,
                "local_reading_layout": local_layout,
                "composition_guide_sha256": composition_examples.signature(),
                "references": self.base["photos"],
                "plan": {**plan, "text_region": region, "alignment": self.alignment(title)},
            }

        raw, meta = await self.stage(
            name + ":art",
            {
                "action": action,
                "title": title,
                "plan": plan,
                **(
                    {
                        "art_contract": 8,
                        "cover_continuity_sha256": render.digest(self.cover_continuity)
                        if self.cover_continuity
                        else None,
                    }
                    if not title
                    else {}
                ),
            },
            build,
        )

        async def compose(attempt):
            data, layout = render.text(
                raw,
                value,
                self.profile,
                title=title,
                region=meta["text_region"],
                alignment=meta["plan"]["alignment"],
                readable=self.designed and not title,
            )
            if meta.get("composition_sha256") == render.digest(data):
                # This exact text composition already passed inspection while its
                # source art was selected. Changed words produce a different hash.
                qa = meta["composition_review"]
            else:
                qa = await self.review(
                    data,
                    f"{'CAPA_PLANA' if title else 'PAGINA_INTERNA'}: texto literal "
                    + json.dumps(value, ensure_ascii=False)
                    + ". Somente esse texto. Tipografia conforme os dados técnicos verificados, sem obstruir pessoas ou ação, sem tarjas; identidade e anatomia corretas. "
                    + (
                        self.text_instruction(True)
                        if title
                        else "Sem títulos internos ou simulação de livro físico."
                    ),
                    technical={"typography": layout},
                )
            if title and self.designed and not self.demo:
                # Only the exact reserve crop and final cover review can confirm
                # overlap. Expanded Haar boxes are not hair/hat segmentation.
                layout["title_clearance"] = {
                    "method": "mandatory_visual_title_review",
                    "status": qa["status"],
                    "local_estimate": render.title_area_evidence(raw, layout),
                }
            return data, {
                "validation": qa,
                "art_key": meta["storage_key"],
                "art_sha256": render.digest(raw),
                "layout": layout,
                "local_reading_layout": meta.get("local_reading_layout"),
            }

        data, composed_meta = await self.stage(
            name + ":text",
            {
                "art": render.digest(raw),
                "text": value,
                **(
                    {"reading_layout_contract": 2, "region": meta["text_region"]}
                    if self.designed and not title
                    else {}
                ),
            },
            compose,
        )
        return data, {
            **composed_meta,
            "art_bytes": raw,
            **(
                {"book_design": {"id": self.design["id"], "sha256": self.design["sha256"]}}
                if self.design
                else {}
            ),
        }

    async def catalog_page(self, name, action, *, mode, value="", passages=None):
        """Construct the page role prescribed by the selected complete catalog book."""
        design = self.design
        if not design:
            raise ProviderError(
                "Escolha o padrão completo do Catálogo antes de gerar", transient=False
            )
        region = design["interior"]["region"]
        if mode == "reading":
            # Literal copy must fit before any image is purchased. Text lives on its
            # own reading page; no face-placement heuristic changes this structure.
            render.text(
                self.master._offline_png("layout", palette=((255, 255, 255), (255, 255, 255))),
                value,
                self.profile,
                region=region,
                alignment=design["interior"]["alignment"],
                measure_only=True,
            )
        art_action = (
            {
                "theme": self.project.theme,
                "role": "quiet decorative reading page; no people, no animals, no main action",
            }
            if mode == "reading"
            else action
        )
        revision = self.revision_for(name)
        adjustment = revision.get("art_adjustment", revision.get("adjustment", ""))
        if adjustment:
            art_action = {"scene": art_action, "requested_adjustment": adjustment}
        if mode == "reading" and isinstance(action, dict):
            requested = action.get("requested_scene")
            if isinstance(requested, dict) and requested.get("requested_adjustment"):
                art_action = {
                    **art_action,
                    "requested_adjustment": requested["requested_adjustment"],
                    "request_id": requested.get("request_id"),
                }

        async def generate(_attempt):
            prompt = book_design.prompt(
                design,
                mode + "_page",
                art_action,
                text_region=region if mode == "reading" else None,
            )
            prompt += "\nGenerate ONE square FLAT page only. The reference shows the complete book: extract only the requested page role, never draw the book, fold, binding, frame, lettering, example names or text. "
            prompt += (
                "Create a warm naturally quiet paper reading page, with discreet thematic decorations near the outer edges only. The measured reading rectangle must be plain, clear and free of people or objects. No portrait or narrative scene in this reading area. "
                if mode == "reading"
                else "One prominent full-page story illustration with the project's cast and the requested action. No reserved reading strip, no letters and no printed words. "
            )
            prompt += (
                "All attached images are original project photos or this project's approved cover. They alone define identity, wardrobe, palette and continuity. No catalog people, scenery or story props may be copied. AUTHORIZED CAST: "
                + json.dumps(self.base["cast_contract"], ensure_ascii=False)
            )
            if self.demo:
                raw = self.master._offline_png(name, palette=((248, 242, 229), (225, 236, 220)))
            else:
                self.guard()
                result = (
                    await self.master._pkg()
                    .get_image_provider()
                    .generate_scene(
                        prompt=prompt,
                        character_ref=self.photos[0],
                        photo=self.photos[0],
                        extra_refs=self.photos[1:]
                        + ([self.cover_continuity] if self.cover_continuity else []),
                        style=design["finish"],
                    )
                )
                self.account(result, name)
                raw = result.image_bytes
            render.square(raw)
            qa = await self.review(
                raw, "Integridade do arquivo; avaliação visual pertence ao usuário"
            )
            return raw, {
                "validation": qa,
                "book_design": {"id": design["id"], "sha256": design["sha256"]},
                "page_role": mode,
            }

        raw, source_meta = await self.stage(
            name + ":art",
            {
                "page_role": mode,
                "action": art_action,
                "cover": render.digest(self.cover_continuity) if self.cover_continuity else None,
            },
            generate,
        )

        async def compose(_attempt):
            if mode == "reading":
                data, layout = render.text(
                    raw,
                    value,
                    self.profile,
                    region=region,
                    alignment=design["interior"]["alignment"],
                    readable=True,
                )
            else:
                data, layout = raw, {"text": "", "lines": [], "illustration_only": True}
            qa = await self.review(
                data, "Integridade do arquivo; avaliação visual pertence ao usuário"
            )
            return data, {
                "validation": qa,
                "layout": layout,
                "art_key": source_meta["storage_key"],
                "art_sha256": render.digest(raw),
                "book_design": source_meta["book_design"],
                "page_role": mode,
                "passages": passages or [],
            }

        data, meta = await self.stage(
            name + ":text",
            {
                "art": render.digest(raw),
                "text": value,
                "page_role": mode,
                "passages": passages or [],
            },
            compose,
        )
        return data, {**meta, "art_bytes": raw}

    async def catalog_spread(self, name, left, right, actions):
        mode = self.design["interior"]["mode"]
        if self.design["id"] == "family" or self.design.get("preview_interior"):
            interior = book_design.preview_interior(self.design)
            original_policy = self.policy
            self.policy = {
                **self.policy,
                "referenceComposition": {
                    **self.policy["referenceComposition"],
                    "bodyRegion": interior["region"],
                },
                "typography": {
                    **self.policy["typography"],
                    "bodyAlignment": interior["alignment"],
                },
            }
            try:
                first, _ = await self.art(name + ":left", actions[0], value=left)
                second, _ = await self.art(name + ":right", actions[1], value=right)
            finally:
                self.policy = original_policy
        elif mode == "two_scenes":
            first, _ = await self.art(name + ":left", actions[0], value=left)
            second, _ = await self.art(name + ":right", actions[1], value=right)
        else:
            reading, _ = await self.catalog_page(
                name + ":reading",
                actions,
                mode="reading",
                value=left + "\n\n" + right,
                passages=[1, 2],
            )
            illustration, _ = await self.catalog_page(
                name + ":illustration", actions, mode="illustration", passages=[1, 2]
            )
            first, second = (
                (reading, illustration) if mode == "text_left" else (illustration, reading)
            )
        return await self.mockup("spread", [first, second])

    async def mockup(self, name, artworks, *, cover=None):
        if name == "spread":

            async def build_local(_attempt):
                data, composition = book_mockups.open_book_spread(
                    *artworks,
                    presentation=(self.design or {}).get("presentation"),
                    cover=self.cover_continuity,
                )
                return data, {
                    "validation": {
                        "status": "awaiting_user_review",
                        "reviewer": "user",
                        "method": "technical_integrity_only",
                    },
                    "composition": composition,
                    "presentation": "open_book_deterministic",
                }

            return await self.stage(
                name,
                {
                    "sources": [render.digest(p) for p in artworks],
                    "surface_contract": 7,
                },
                build_local,
                billable=False,
            )

        async def build(attempt):
            reading = len(artworks) == 1
            prompt = (
                "Uma cena fotográfica natural, ambiente acolhedor. "
                + (
                    "Protagonista original segura um livro físico quadrado de capa dura, ligeiramente aberto, em primeiro plano. A capa dianteira fica legível para a câmera e a contracapa aparece num ângulo natural. Ambiente tranquilo de fundo desfocado, somente o elenco solicitado nas fotos e na ficha. A foto define somente identidade, não copie seu cenário. Capa PLANA voltada para a câmera, vista quase frontal. Mãos naturais segurando somente as bordas, sem ocultar o centro da capa. "
                    if reading
                    else "Foto de produto: um livro aberto A 180 GRAUS sobre uma mesa, visto de cima, com duas páginas quadradas PLANAS iguais. Sem páginas curvas, sem pessoas nem mãos. "
                )
                + (
                    "A superfície imprimível da capa deve ser inteiramente MAGENTA VIVO uniforme #ff00ff. "
                    if reading
                    else "A página ESQUERDA deve ser inteiramente MAGENTA VIVO uniforme #ff00ff; a página DIREITA deve ser inteiramente CIANO VIVO uniforme #00ffff. "
                )
                + "Essas cores são marcações temporárias que o compositor substituirá pelas artes finais. Superfícies lisas e foscas, sem letras, imagens, textura ou reflexo forte. "
                + (
                    "Livro físico encadernado: capa dura com espessura, lombada lateral visível, "
                    "vinco de abertura, bloco de páginas brancas na borda inferior e contracapa. "
                    "Nunca uma folha avulsa, placa fina, cartaz ou cartão. Vista levemente em três "
                    "quartos, mantendo o plano frontal retangular legível. Cantos arredondados e "
                    "bordas limpas; mãos apoiam o peso do volume pelas laterais e por baixo. "
                    "A marcação cobre somente a face impressa da capa, sem vazamentos na lombada, "
                    "nas páginas, na roupa ou nos dedos. O compositor aplicará as artes finais. "
                    if reading
                    else "Cantos e contornos inteiramente visíveis. O compositor aplicará as artes finais. "
                )
                + "Não invente personagens. Fotos originais definem identidade. "
                + json.dumps(
                    {
                        "continuity": self.base["continuity"] if reading else {},
                        "requested_adjustment": self.revision_for(name).get("adjustment", ""),
                        "references": self.base["reference_manifest"] if reading else [],
                    },
                    ensure_ascii=False,
                )
            )
            if not reading:
                prompt += "\nCOMPOSITION EXAMPLES GUIDE: " + json.dumps(
                    composition_examples.context("open_book"), ensure_ascii=False
                )
            if reading and self.designed:
                prompt += (
                    "\nENQUADRAMENTO OBRIGATÓRIO: fotografia de produto em plano médio ABERTO, "
                    "pessoa sentada, cabeça inteira, cadeira, cintura e colo visíveis. Livro "
                    "físico de 20x20 cm, capa dura com lombada, espessura e cantos arredondados. "
                    "O livro tem escala natural em relação a quem o segura, bem visível entre as "
                    "mãos e o colo, com presença de produto como na referência do Catálogo. "
                    "Nunca uma placa que cobre o tronco ou os rostos. "
                    "Mãos proporcionais apoiam as laterais, sem dedos esticados. "
                    "O figurino da personagem impressa pertence ao livro; a roupa da pessoa "
                    "externa pode ser casual e natural, sem obrigação de copiar o figurino impresso. "
                    "Fundo acolhedor luminoso e coerente, sem pessoas adicionadas ao elenco. A marcação magenta "
                    "fica somente na superfície frontal imprimível; bordas, lombada e mãos são "
                    "neutras, sem reflexos coloridos. Região aproximada da capa: "
                    + json.dumps(self.policy["referenceComposition"]["holdingSurfaceRegion"])
                )
            if self.design:
                prompt = book_design.prompt(
                    self.design,
                    "holding" if reading else "open_book",
                    "Build a physical book presentation matching the same catalog model, to receive the finished project artwork.",
                )
                prompt += (
                    f"\nGenerate a natural photographic scene with ONLY the requested project cast, based on the ORIGINAL identity photos. Use a medium-wide view with the person's whole head, torso, forearms, hands and lap visible. Show a real {15 if self.project.book_size == 'P' else 20}x{15 if self.project.book_size == 'P' else 20} cm hardback in a natural three-quarter view, slightly open, with two distinct rigid boards joined by a plausible spine and hinge, a continuous thick page block with fine layered paper edges, and consistent perspective and scale. Establish the book's size relative to the person's hands and torso before posing the fingers; never enlarge the book to fill the frame. Hands support its weight from below and at the outer edges, fingers naturally wrapping around the boards with correct occlusion and contact shadows. The thumb rests on a visible board edge and the other fingers curl behind it; never paste a hand flat over the printed face or bend a rigid board through the fingers. Keep the book close to the lap or torso; no floating book, flat poster, tablet, fused fingers or disconnected covers. Match lighting, focus, grain and shadows across the person and book. The front printable cover must be a single clearly visible MAGENTA plane #ff00ff. All board edges, spine, rear cover, pages and fingers remain neutral, without registration-color reflections. No printed words or example faces. "
                    if reading
                    else "\nGenerate the physical open-book product scene matching this same catalog model: two equal flat square pages, a natural central gutter, visible hardback edges and page-block thickness. The left printable page is MAGENTA #ff00ff and the right is CYAN #00ffff. No people, hands, printed words or example artwork. The real finished project pages will be inserted locally. "
                )
                prompt += json.dumps(
                    {
                        "project_identity": self.base["reference_manifest"],
                        "continuity": self.base["continuity"] if reading else {},
                        "requested_adjustment": self.revision_for(name).get("adjustment", ""),
                    },
                    ensure_ascii=False,
                )
            prompt += "\nAUTHORIZED CAST: " + json.dumps(
                self.base["cast_contract"] if reading else {"people": "none"}, ensure_ascii=False
            )
            template_reference = (
                None
                if self.project_only_references
                else book_design.reference(self.design, "holding" if reading else "page")
                if self.design
                else (
                    visual_reference.load(
                        "holding" if reading else "page", self.project.style, self.reference_theme
                    )
                    if self.designed
                    else None
                )
            )
            if template_reference:
                prompt += "\nÚLTIMA REFERÊNCIA: exemplo do CATÁLOGO, apenas acabamento e estrutura física do livro. Nunca copie as pessoas, palavras, capa ou cenário do exemplo. Fotos originais do projeto definem identidade e elenco. Mantenha a marcação temporária somente nas faces imprimíveis."
            if self.demo:
                visible_masks = None
                geometry_source = "manual"
                keying_fallback_reason = None
                raw = self.master._offline_png(name, palette=((248, 240, 220), (230, 240, 250)))
                geometry = {
                    "valid": True,
                    "issues": [],
                    "surfaces": [[[0.2, 0.2], [0.8, 0.2], [0.8, 0.8], [0.2, 0.8]]]
                    if reading
                    else [
                        [[0.05, 0.25], [0.49, 0.25], [0.49, 0.75], [0.05, 0.75]],
                        [[0.51, 0.25], [0.95, 0.25], [0.95, 0.75], [0.51, 0.75]],
                    ],
                    "occlusions": [],
                }
            else:

                async def generate_template(_attempt):
                    result = (
                        await self.master._pkg()
                        .get_image_provider()
                        .generate_scene(
                            prompt=prompt,
                            character_ref=self.photos[0] if reading else template_reference or b"",
                            photo=self.photos[0] if reading else None,
                            extra_refs=(self.photos[1:] if reading else [])
                            + ([template_reference] if reading and template_reference else []),
                            reference_role="character" if reading else "cover",
                            style="fotografia editorial natural",
                            landscape=not reading,
                        )
                    )
                    self.account(result, name)
                    return result.image_bytes, {"operation": "generate_marked_template"}

                raw, template_meta = await self.stage(
                    name + ":template",
                    {
                        "attempt": attempt,
                        "generation_job": str(self.job.id),
                        "template_contract": 5 if reading else 2,
                        "catalog_reference_sha256": render.digest(template_reference)
                        if template_reference
                        else None,
                        "revision": self.profile.get("editorial_revisions", {}).get(
                            "03_LEITURA" if reading else "02_LIVRO_ABERTO"
                        ),
                    },
                    generate_template,
                )
                geometry_source = "keyed_pixels"
                keying_fallback_reason = None
                try:
                    geometry, visible_masks = render.keyed_surfaces(raw, len(artworks))
                except ValueError as keying_error:
                    # Reuse the already-generated photo. Vision measures its
                    # actual print planes only when pixel keying cannot do so;
                    # this avoids another billable image-generation attempt.
                    located = (
                        await self.master._pkg()
                        .get_text_provider()
                        .locate_book_surfaces(data=raw, count=len(artworks))
                    )
                    self.account(located, "Localização das superfícies do mockup")
                    try:
                        proposed = json.loads(located.text)
                    except (TypeError, json.JSONDecodeError) as exc:
                        raise ValueError(
                            "A localização das páginas do livro retornou um resultado inválido"
                        ) from exc
                    geometry = render.validate_geometry(proposed, len(artworks))
                    visible_masks = None
                    geometry_source = "vision"
                    keying_fallback_reason = str(keying_error)[:240]
            data, provenance = render.mockup(
                raw,
                artworks,
                geometry,
                visible_masks=visible_masks,
                physical_book=reading and self.designed,
                geometry_source=geometry_source,
            )
            expected = {
                key: self.profile["locales"][self.language][key]
                for key in ("title", "left", "right")
            }
            qa = await self.review(
                data,
                (
                    "LEITURA: capa final exata aplicada, pessoas externas fotográficas, mãos naturais, identidade original. Livro físico realista: escala proporcional às mãos e ao corpo, perspectiva coerente, duas capas rígidas conectadas pela lombada, bloco de folhas com espessura, dedos apoiando o peso com oclusão e sombras de contato. Reprove aparência de placa, livro flutuante, capas desconectadas ou perspectiva incompatível. "
                    if reading
                    else "LIVRO_ABERTO: duas páginas quadradas iguais; texto literal esquerdo e direito, sem título adicional, cenas coerentes. "
                )
                + json.dumps(expected, ensure_ascii=False),
                cover=cover,
            )
            return data, {
                "validation": qa,
                "composition": provenance,
                "geometry": geometry,
                "surface_detection": {
                    "method": geometry_source,
                    **(
                        {"keying_fallback_reason": keying_fallback_reason}
                        if keying_fallback_reason
                        else {}
                    ),
                },
                **({"template_key": template_meta["storage_key"]} if not self.demo else {}),
            }

        inputs = {
            "sources": [render.digest(p) for p in artworks],
            "surface_contract": 9 if name == "reading" else 6,
        }
        try:
            return await self.stage(name, inputs, build)
        except ProviderError as exc:
            if name != "reading":
                raise
            failure = str(exc).lower()
            reason = (
                "outcome_unknown"
                if exc.outcome_unknown
                else "moderation"
                if "moderation" in failure or "safety" in failure
                else "rate_limit"
                if exc.status_code == 429
                else "provider_unavailable"
                if exc.status_code and exc.status_code >= 500
                else "quality_review"
                if "revisão visual" in failure
                else "provider_failure"
            )
            return await self.book_only_fallback(artworks[0], reason=reason)

    async def book_only_fallback(self, cover_art, *, reason="provider_failure"):
        data, composition = book_mockups.book_only(cover_art)

        async def build_fallback(_attempt):
            return data, {
                "validation": {
                    "status": "awaiting_user_review",
                    "reviewer": "user",
                    "method": "technical_integrity_only",
                },
                "composition": composition,
                "presentation": "book_only_fallback",
                "fallback_reason_category": reason,
            }

        return await self.stage(
            "reading",
            {
                "sources": [render.digest(cover_art)],
                "surface_contract": 10,
                "presentation": "book_only_fallback",
                "fallback_revision": 1,
            },
            build_fallback,
            billable=False,
        )


async def preview(db, job, project):
    from . import master_book as master

    require_photo_authorization(db, project.id)
    photos = master._photos(db, project)
    reference_theme = " ".join(
        str(v or "")
        for v in (
            project.theme,
            project.book_profile.get("theme_description"),
            project.book_profile.get("locales", {})
            .get(project.language or "pt-BR", {})
            .get("title"),
        )
    )
    family = visual_reference.catalog_family(project.style, reference_theme)
    if not project.book_profile.get("book_design") and visual_reference.load(
        "cover", project.style, reference_theme
    ):
        contract.update(
            project,
            visual_master_preset="catalog-adventure-v1"
            if family == "adventure"
            else "andre-editorial-v1"
            if family in {"creative", "family"}
            else None,
        )
    contract.update(project, languages=[project.language or "pt-BR"])
    await master._prepare(db, job, project, photos)
    payload = master._payload(job)
    selected = payload.get("image")
    if selected:
        revisions = dict(project.book_profile.get("editorial_revisions", {}))
        previous = revisions.get(selected, {})
        revisions[selected] = {
            "id": str(job.id),
            "adjustment": payload.get("adjustment", ""),
            "art_revision": previous.get("art_revision")
            if payload.get("title_refresh")
            else str(job.id),
            "art_adjustment": previous.get("art_adjustment", "")
            if payload.get("title_refresh")
            else payload.get("adjustment", ""),
        }
        if selected == "01_CAPA":
            revisions["03_LEITURA"] = {"parent_revision": str(job.id)}
        contract.update(project, editorial_revisions=revisions)
    pipe = Pipeline(db, job, project, photos)
    purchase_flow.update(
        project, preview_ready_at=None, preview_approved_at=None, stage="preview_generating"
    )
    locale = project.book_profile["locales"][pipe.language]
    if pipe.designed:
        # Check ALL known copy before purchasing the first illustration or mockup.
        # A later overflowing page must not waste a successfully purchased cover.
        try:
            render.validate_preview_copy(pipe.profile, locale)
        except render.TextLayoutError as exc:
            raise ProviderError(str(exc), transient=False) from exc
    calibration = project.book_profile.get("cover_calibration") or {}
    approval = payload.get("approved_cover_sha256")
    calibration_context = signature(
        [pipe.base, locale["title"], project.book_profile.get("theme_description")]
    )
    if approval:
        if (
            approval != calibration.get("sha256")
            or calibration.get("context") != calibration_context
        ):
            raise ProviderError(
                "A capa mudou; revise a capa atual antes de continuar", transient=False
            )
        flat = storage.get_bytes(calibration["flat_key"])
        if render.digest(flat) != calibration["flat_sha256"]:
            raise ProviderError("Arquivo da capa alterado; gere a capa novamente", transient=False)
        flat_meta = calibration["flat_meta"]
    else:
        cover_action = {
            "theme": project.book_profile.get("theme_description") or project.theme,
            "narrative_actions": project.book_profile.get("preview_actions", {}).get(
                pipe.language, {}
            ),
            "instruction": "Depict one concrete activity from this project's story in a single continuous front cover. Original photos define identity, not the scene or camera framing.",
        }
        flat, flat_meta = await pipe.art(
            "cover",
            cover_action,
            title=True,
            value=locale["title"],
        )
    if pipe.designed and flat_meta.get("art_key"):
        pipe.cover_continuity = storage.get_bytes(flat_meta["art_key"])
    cover = render.front(flat, profile=project.book_profile)
    role = "01_CAPA"
    all_meta = {}
    selected = master._payload(job).get("image")
    cover_only = payload.get("cover_only", False) or bool(
        calibration
        and not approval
        and (project.book_profile.get("stage") == "cover_ready" or selected in (None, "01_CAPA"))
    )
    roles = ("01_CAPA",) if cover_only else editorial_profile.ROLES
    for role in roles:
        if role == "01_CAPA":
            data, meta = cover, {k: v for k, v in flat_meta.items() if k != "art_bytes"}
            # Source is immutable and must never be replaced by the presentation PNG in PDFs.
            meta["flat_cover_sha256"] = render.digest(flat)
            meta["flat_cover_key"] = flat_meta["storage_key"]
        elif role == "02_LIVRO_ABERTO":
            existing = master._assets(db, project, workflow=1, language=pipe.language, role=role)
            if (
                selected == "01_CAPA"
                and existing
                and existing[-1].meta.get("editorial") == project.book_profile["editorial"]
                and all(
                    existing[-1].meta.get("texts", {}).get(k) == locale[k]
                    for k in ("left", "right")
                )
            ):
                # The spread has no visible title. Refresh its provenance without charging
                # for unchanged artwork when only the cover title was edited.
                existing[-1].meta = {**existing[-1].meta, "texts": locale}
                all_meta[f"{pipe.language}:{role}"] = {
                    "state": existing[-1].meta["validation"]["status"]
                }
                master._publish_progress(
                    db, job, stage=role, done=2, total=3, language=pipe.language
                )
                continue
            actions = project.book_profile.get("preview_actions", {}).get(pipe.language, {})
            if pipe.design:
                data, meta = await pipe.catalog_spread(
                    "preview",
                    locale["left"],
                    locale["right"],
                    [
                        actions.get("left") or locale["left"],
                        actions.get("right") or locale["right"],
                    ],
                )
            else:
                left, _ = await pipe.art(
                    "preview:left", actions.get("left") or locale["left"], value=locale["left"]
                )
                right, _ = await pipe.art(
                    "preview:right", actions.get("right") or locale["right"], value=locale["right"]
                )
                data, meta = await pipe.mockup("spread", [left, right])
        else:
            existing = master._assets(db, project, workflow=1, language=pipe.language, role=role)
            prior_fallback = next(
                (
                    asset
                    for asset in reversed(existing)
                    if asset.meta.get("presentation") == "book_only_fallback"
                    and asset.meta.get("editorial") == project.book_profile["editorial"]
                ),
                None,
            )
            current_cover_sha256 = render.digest(cover)
            if prior_fallback and selected != "03_LEITURA":
                if prior_fallback.meta.get("cover_sha256") == current_cover_sha256:
                    all_meta[f"{pipe.language}:{role}"] = {
                        "state": prior_fallback.meta["validation"]["status"],
                        "presentation": "book_only_fallback",
                    }
                    master._publish_progress(
                        db, job, stage=role, done=3, total=3, language=pipe.language
                    )
                    continue
                data, meta = await pipe.book_only_fallback(
                    flat,
                    reason=prior_fallback.meta.get("fallback_reason_category", "previous_fallback"),
                )
            else:
                data, meta = await pipe.mockup("reading", [flat], cover=flat)
            meta = {**meta, "cover_sha256": render.digest(cover)}
        kind = {"01_CAPA": "cover", "02_LIVRO_ABERTO": "page_image", "03_LEITURA": "in_hand"}[role]
        meta = {
            **meta,
            "editorial": project.book_profile["editorial"],
            "texts": locale,
            **(
                {"book_design": {"id": pipe.design["id"], "sha256": pipe.design["sha256"]}}
                if pipe.design
                else {}
            ),
        }
        meta.pop("workflow", None)
        existing = master._assets(db, project, workflow=1, language=pipe.language, role=role)
        if (
            not existing
            or existing[-1].meta.get("storage_key") != meta.get("storage_key")
            or render.digest(storage.get_bytes(existing[-1].storage_key)) != render.digest(data)
        ):
            master._store(
                db,
                project,
                kind,
                data,
                language=pipe.language,
                role=role,
                name=contract.filename(pipe.language, role, locale["title"]),
                **meta,
            )
        all_meta[f"{pipe.language}:{role}"] = {"state": meta["validation"]["status"]}
        master._publish_progress(
            db, job, stage=role, done=roles.index(role) + 1, total=3, language=pipe.language
        )
    if cover_only:
        contract.update(
            project,
            stage="cover_ready",
            cover_calibration={
                "sha256": render.digest(cover),
                "flat_key": flat_meta["storage_key"],
                "flat_sha256": render.digest(flat),
                "flat_meta": {k: v for k, v in flat_meta.items() if k != "art_bytes"},
                "context": calibration_context,
            },
        )
        purchase_flow.update(
            project, preview_ready_at=None, preview_approved_at=None, stage="preview_generating"
        )
        job.result = {
            **(job.result or {}),
            "scenes": all_meta,
            "preview_complete": False,
            "cover_only": True,
        }
        master._set_status(db, project, ProjectStatus.EBOOK_READY)
        return
    contract.update(project, stage="preview_ready")
    purchase_flow.update(
        project,
        preview_ready_at=purchase_flow.timestamp(),
        preview_approved_at=None,
        stage="preview_ready",
    )
    job.result = {**(job.result or {}), "scenes": all_meta, "preview_complete": True}
    master._set_status(db, project, ProjectStatus.EBOOK_READY)
