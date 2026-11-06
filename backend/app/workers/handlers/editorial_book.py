"""LIVRO UPDATE runtime: flat source art -> literal typography -> three final scenes."""

import hashlib
import json
import logging

from sqlalchemy import select

from app import storage
from app.ai_clients.base import ProviderError
from app.config import settings
from app.models import Asset, Job, ProjectStatus
from app.services import book_profile as contract
from app.services import (
    composition_examples,
    editorial_profile,
    purchase_flow,
    spend_guard,
    visual_reference,
)
from app.services.privacy import require_photo_authorization
from app.workers import editorial_render as render


def signature(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class Pipeline:
    def __init__(self, db, job, project, photos):
        from . import master_book as master

        self.master = master
        self.db, self.job, self.project, self.photos = db, job, project, photos
        self.profile = project.book_profile
        self.policy = editorial_profile.policy(self.profile)
        self.designed = bool(self.policy.get("referenceComposition"))
        self.demo = contract.test_mode(project) or settings.offline_fallback
        self.language = project.language or "pt-BR"
        self.last_review_scope = None
        self.last_review_issues = []
        self.last_art = None
        self.cover_continuity = None
        self.refs = [
            data
            for _, data in editorial_profile.references(
                project.style, self.profile["editorial"]["version"], art_only=True
            )
        ]
        self.base = {
            "renderer_revision": "2026-11-06.full-bleed.1",
            "visual_masters": visual_reference.fingerprint(project.style) if self.designed else {},
            "visual_master_preset": self.profile.get("visual_master_preset"),
            "editorial": self.profile["editorial"],
            "photos": [render.digest(p) for p in photos],
            "style": project.style,
            "continuity": {
                k: self.profile.get(k)
                for k in ("visual_identity", "costume", "palette", "characters")
            },
            "language": self.language,
            "reference_manifest": contract.photo_manifest(project, photos),
        }
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

    def should_reframe_art(self, *, title, attempt):
        """Repair the first reserve collision instead of repeating the same framing.

        This applies to covers and interior pages with either layout. Repeated
        translation would crop too much of the action, so the final attempt
        returns to generation if the repair did not pass review.
        """
        return bool(
            attempt == 2
            and self.last_art
            and (
                getattr(self, "last_review_scope", None) == "text_reserve"
                or any(
                    token in " ".join(self.last_review_issues).lower()
                    for token in (
                        "text",
                        "regi",
                        "sobrepo",
                        "reserve",
                        "ink_region",
                        "tít",
                        "cabelo",
                        "cabeça",
                        "hair",
                        "head",
                        "overlap",
                    )
                )
            )
        )

    def cached(self, key):
        return self.db.scalar(
            select(Asset).where(
                Asset.project_id == self.project.id,
                Asset.kind == "editorial_source",
                Asset.storage_key == key,
            )
        )

    def record(self, name, state, **values):
        self.job.result = {
            **(self.job.result or {}),
            "editorial_tasks": {
                **(self.job.result or {}).get("editorial_tasks", {}),
                name: {"state": state, **values},
            },
        }
        self.db.commit()

    def account(self, result, label):
        self.master._account(self.db, self.job, result, label)
        self.db.commit()

    def guard(self):
        require_photo_authorization(self.db, self.project.id)
        spend_guard.assert_vendor_allowed(self.db)

    async def stage(self, name, inputs, build):
        """Immutable intermediates survive worker/job retries, scoped to all relevant inputs."""
        revisions = self.project.book_profile.get("editorial_revisions", {})
        role = (
            "01_CAPA"
            if name.startswith("cover")
            else "02_LIVRO_ABERTO"
            if name.startswith(("preview:", "spread"))
            else "03_LEITURA"
            if name == "reading"
            else None
        )
        if revisions.get(role):
            revision = revisions[role]
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
        # Feedback and source art belong only to this task, never the previous scene.
        self.last_review_scope = None
        self.last_review_issues = []
        self.last_art = None
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
        if self.designed:
            maximum = 1
        for attempt in range(attempts + 1, maximum + 1):
            self.record(name, "running", attempts=attempt, input_key=key)
            try:
                self.guard()
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
                    self.record(
                        name,
                        "provider_failed",
                        attempts=attempt - 1,
                        input_key=key,
                        provider_status=exc.status_code,
                        transient=exc.transient,
                    )
                    raise
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
                    if self.designed:
                        raise ProviderError(
                            f"Falha técnica na montagem de {name}: {str(exc)[:240]}",
                            transient=False,
                        ) from exc
                    raise ProviderError(
                        f"Etapa {name} reprovada após {maximum} tentativas; revise a composição",
                        transient=False,
                    ) from exc
        raise ProviderError(f"Etapa {name} esgotou as tentativas deste trabalho", transient=False)

    async def review(self, data, prompt, *, cover=None, technical=None, full_image_prompt=None):
        if self.demo:
            return {"status": "demo"}
        if getattr(self, "designed", False):
            # A render-ready file is not a visual approval. Only the user decides
            # whether likeness, finish and composition satisfy their expectations.
            import io

            from PIL import Image

            with Image.open(io.BytesIO(data)) as image:
                if image.format != "PNG":
                    raise ValueError("Preview must be a valid PNG")
                image.verify()
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
            raise ValueError("Revisão visual reprovada ou inconclusiva")
        return {**report, "status": "valid"}

    async def art(self, name, action, *, title=False, value=None):
        plan_key = signature([self.base, name, action])
        plan = self.profile.get("scene_plans", {}).get(plan_key)
        if not plan:
            if self.demo:
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
            if not title:
                prompt += (
                    "\nFINAL INTERIOR FRAMING: reserve the measured reading rectangle "
                    + json.dumps(safe_region)
                    + " in normalized [left, top, right, bottom] coordinates as natural quiet "
                    "background. Place ALL heads, hair, faces, hands and the important action "
                    f"below y={safe_region[3] + 0.04:.3f}. Reframe the camera and pose to fit "
                    "the scene below that boundary; preserve identity and natural proportions. "
                    "Do not draw text, blank panels, banners or artificial strips."
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
            visual_master = (
                visual_reference.load("cover" if title else "page", self.project.style)
                if self.designed
                else None
            )
            if visual_master:
                prompt += (
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
            if self.demo:
                raw = self.master._offline_png(name, palette=((235, 243, 250), (255, 250, 242)))
            else:
                provider = self.master._pkg().get_image_provider()
                if self.should_reframe_art(title=title, attempt=attempt) and hasattr(
                    provider, "reframe_editorial_art"
                ):
                    operation = "outpaint_reframed_art"
                    logging.getLogger(__name__).info(
                        "editorial_reframe stage=%s attempt=%s reserve=%s",
                        name,
                        attempt,
                        safe_region,
                    )
                    source_sha256 = render.digest(self.last_art)
                    result = await provider.reframe_editorial_art(
                        art=self.last_art,
                        photos=self.photos,
                        top_fraction=min(0.3, safe_region[3] + 0.04),
                        prompt="Preserve a identidade, figurino e acabamento da cena original. "
                        + json.dumps(
                            {
                                "text_region": safe_region,
                                "corrections": self.last_review_issues,
                            },
                            ensure_ascii=False,
                        ),
                    )
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
            regions = (
                [region]
                if title or self.designed
                else [region, [0.07, 0.07, 0.50, 0.40], [0.07, 0.07, 0.93, 0.29]]
            )
            for region_attempt, region in enumerate(regions):
                try:
                    candidate, layout = render.text(
                        raw,
                        value,
                        self.profile,
                        title=title,
                        region=region,
                        alignment=self.alignment(title),
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
                            "Full-bleed picture-book illustration with text over natural quiet "
                            "background; no separate reading panel or inset illustration. "
                            if page_composition
                            else ""
                        )
                        + "ARTE_BASE: One flat continuous illustration, without "
                        "letters, insets, photographs, collages or physical-book mockups. "
                        "Check identity, age, anatomy, outfit, style and the specific requested action. "
                        + json.dumps(
                            {
                                "identity": self.base["continuity"],
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
                        + self.text_instruction(title),
                        technical={"typography": layout},
                    )
                    break
                except ValueError:
                    if region_attempt == len(regions) - 1:
                        raise
            return raw, {
                "validation": qa,
                "composition_review": composition_review,
                "composition_sha256": render.digest(candidate),
                "text_region": region,
                "operation": operation,
                "source_sha256": source_sha256,
                "page_composition": page_composition,
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
            return data, {
                "validation": qa,
                "art_key": meta["storage_key"],
                "art_sha256": render.digest(raw),
                "layout": layout,
            }

        data, composed_meta = await self.stage(
            name + ":text", {"art": render.digest(raw), "text": value}, compose
        )
        return data, {**composed_meta, "art_bytes": raw}

    async def mockup(self, name, artworks, *, cover=None):
        async def build(attempt):
            reading = len(artworks) == 1
            prompt = (
                "Uma cena fotográfica natural, ambiente acolhedor. "
                + (
                    "Protagonista original segura um livro fechado quadrado em primeiro plano. Ambiente tranquilo de fundo desfocado, SEM outras pessoas. A foto define somente identidade, não copie seu cenário. Capa PLANA voltada para a câmera, vista quase frontal. Mãos naturais segurando somente as bordas, sem ocultar o centro da capa. "
                    if reading
                    else "Foto de produto: um livro aberto A 180 GRAUS sobre uma mesa, visto de cima, com duas páginas quadradas PLANAS iguais. Sem páginas curvas, sem pessoas nem mãos. "
                )
                + (
                    "A superfície imprimível da capa deve ser inteiramente MAGENTA VIVO uniforme #ff00ff. "
                    if reading
                    else "A página ESQUERDA deve ser inteiramente MAGENTA VIVO uniforme #ff00ff; a página DIREITA deve ser inteiramente CIANO VIVO uniforme #00ffff. "
                )
                + "Essas cores são marcações temporárias que o compositor substituirá pelas artes finais. Superfícies lisas e foscas, sem letras, imagens, textura ou reflexo forte. "
                "Cantos e contornos inteiramente visíveis. O compositor aplicará as artes finais. "
                "Não invente personagens. Fotos originais definem identidade. "
                + json.dumps(
                    {
                        "continuity": self.base["continuity"] if reading else {},
                        "references": self.base["reference_manifest"] if reading else [],
                        "requested_adjustment": self.project.book_profile.get(
                            "editorial_revisions", {}
                        )
                        .get("03_LEITURA" if reading else "02_LIVRO_ABERTO", {})
                        .get("adjustment", ""),
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
                    "O livro deve ocupar APENAS cerca de um terço da largura total da imagem "
                    "(28–36%), junto ao peito inferior/colo, nunca uma placa que cobre o tronco. "
                    "Mãos proporcionais apoiam as laterais, sem dedos esticados. "
                    "O figurino da personagem impressa pertence ao livro; a roupa da pessoa "
                    "externa pode ser casual e natural, sem obrigação de copiar o figurino impresso. "
                    "Fundo acolhedor luminoso e coerente, sem outras pessoas. A marcação magenta "
                    "fica somente na superfície frontal imprimível; bordas, lombada e mãos são "
                    "neutras, sem reflexos coloridos. Região aproximada da capa: "
                    + json.dumps(self.policy["referenceComposition"]["holdingSurfaceRegion"])
                )
            if self.demo:
                visible_masks = None
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
                            character_ref=self.photos[0] if reading else b"",
                            photo=self.photos[0] if reading else None,
                            extra_refs=self.photos[1:] if reading else [],
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
                        "template_contract": 3 if reading else 2,
                        "revision": self.profile.get("editorial_revisions", {}).get(
                            "03_LEITURA" if reading else "02_LIVRO_ABERTO"
                        ),
                    },
                    generate_template,
                )
                geometry, visible_masks = render.keyed_surfaces(raw, len(artworks))
            data, provenance = render.mockup(raw, artworks, geometry, visible_masks=visible_masks)
            expected = {
                key: self.profile["locales"][self.language][key]
                for key in ("title", "left", "right")
            }
            qa = await self.review(
                data,
                (
                    "LEITURA: capa final exata aplicada, pessoas externas fotográficas, mãos naturais, identidade original. "
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
                **({"template_key": template_meta["storage_key"]} if not self.demo else {}),
            }

        return await self.stage(
            name,
            {
                "sources": [render.digest(p) for p in artworks],
                "surface_contract": 5 if name == "reading" else 4,
            },
            build,
        )


async def preview(db, job, project):
    from . import master_book as master

    require_photo_authorization(db, project.id)
    photos = master._photos(db, project)
    if visual_reference.load("cover", project.style):
        contract.update(project, visual_master_preset="andre-editorial-v1")
    elif project.style == "cartoon":
        contract.update(project, visual_master_preset=None)
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
        flat, flat_meta = await pipe.art(
            "cover",
            project.book_profile.get("theme_description"),
            title=True,
            value=locale["title"],
        )
    if pipe.designed and flat_meta.get("art_key"):
        pipe.cover_continuity = storage.get_bytes(flat_meta["art_key"])
    cover = render.front(flat, profile=project.book_profile)
    role = "01_CAPA"
    all_meta = {}
    selected = master._payload(job).get("image")
    cover_only = payload.get("cover_only", False)
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
            left, _ = await pipe.art(
                "preview:left", actions.get("left") or locale["left"], value=locale["left"]
            )
            right, _ = await pipe.art(
                "preview:right", actions.get("right") or locale["right"], value=locale["right"]
            )
            data, meta = await pipe.mockup("spread", [left, right])
        else:
            data, meta = await pipe.mockup("reading", [flat], cover=flat)
            meta = {**meta, "cover_sha256": render.digest(cover)}
        kind = {"01_CAPA": "cover", "02_LIVRO_ABERTO": "page_image", "03_LEITURA": "in_hand"}[role]
        meta = {**meta, "editorial": project.book_profile["editorial"], "texts": locale}
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
