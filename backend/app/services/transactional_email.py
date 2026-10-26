"""E-mails transacionais via Resend.

Sem RESEND_API_KEY o envio é no-op e o link fica nos logs (dev devolve o token).
Em prod, falta de chave gera warning no boot e em cada skip.
"""

from __future__ import annotations

import logging
from html import escape
from urllib.parse import urlencode

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

RESEND_API_URL = "https://api.resend.com/emails"
_DEFAULT_FROM = "Story R Us <noreply@storyrus.ai>"

# Paleta alinhada aos mockups Story R Us
_COLOR_INK = "#1A2B3C"
_COLOR_MUTED = "#6B7280"
_COLOR_CTA = "#FF7F5E"
_COLOR_BG = "#FFF9F3"


def email_configured() -> bool:
    """True quando há chave Resend para envio real."""
    return bool((settings.resend_api_key or "").strip())


def resolved_from_email() -> str:
    """From efetivo — env vazio no Render não pode zerar o remetente."""
    raw = (settings.transactional_from_email or "").strip()
    return raw or _DEFAULT_FROM


def warn_if_email_unconfigured() -> None:
    """Chamar no boot da API: em prod, e-mail sem chave = esqueci-senha/verify mudos."""
    raw_from = (settings.transactional_from_email or "").strip()
    if not raw_from:
        logger.warning(
            "TRANSACTIONAL_FROM_EMAIL vazio — usando fallback %s "
            "(no Render, preencha o From ou deixe o valor do Blueprint)",
            _DEFAULT_FROM,
        )
    if email_configured():
        logger.info(
            "transactional_email_ready from=%s",
            resolved_from_email(),
        )
        return
    if settings.app_env == "prod":
        logger.warning(
            "RESEND_API_KEY ausente: confirmação de cadastro e esqueci-senha "
            "não enviam e-mail (só logs). Defina no Render + domínio verificado no Resend."
        )
    else:
        logger.info("RESEND_API_KEY ausente: envio transacional desligado (dev ok)")


def public_web_origin() -> str:
    return (settings.public_web_origin or "https://storyrus.ai").rstrip("/")


def email_asset_url(filename: str) -> str:
    return f"{public_web_origin()}/email/{filename}"


def build_verify_email_url(token: str, email: str | None = None) -> str:
    origin = public_web_origin()
    query: dict[str, str] = {"token": token}
    if email:
        query["email"] = email.strip()
    return f"{origin}/verificar-email?{urlencode(query)}"


def build_password_reset_url(token: str, email: str | None = None) -> str:
    origin = public_web_origin()
    query: dict[str, str] = {"token": token}
    if email:
        query["email"] = email.strip()
    return f"{origin}/redefinir-senha?{urlencode(query)}"


def build_preview_ready_url() -> str:
    """Onde o cliente acompanha o livro depois do aviso por e-mail (Meus Pedidos)."""
    return f"{public_web_origin()}/pedidos"


def _branded_html(
    *,
    hero_file: str,
    hero_alt: str,
    heading: str,
    description_html: str,
    cta_label: str,
    cta_url: str,
    disclaimer: str,
) -> str:
    hero_src = email_asset_url(hero_file)
    footer_src = email_asset_url("email-footer.jpg")
    site = "www.storyrus.ai"
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{heading}</title>
</head>
<body style="margin:0;padding:0;background:{_COLOR_BG};font-family:Arial,Helvetica,sans-serif;color:{_COLOR_INK};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_COLOR_BG};">
    <tr>
      <td align="center" style="padding:24px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;overflow:hidden;">
          <tr>
            <td align="center" style="padding:0;">
              <a href="{cta_url}" style="text-decoration:none;">
                <img src="{hero_src}" width="600" alt="{hero_alt}" style="display:block;width:100%;max-width:600px;height:auto;border:0;" />
              </a>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:28px 32px 8px 32px;">
              <h1 style="margin:0;font-size:28px;line-height:1.25;font-weight:700;color:{_COLOR_INK};">{heading}</h1>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:12px 36px 8px 36px;">
              <p style="margin:0;font-size:15px;line-height:1.55;color:{_COLOR_INK};font-weight:400;">{description_html}</p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:24px 32px 8px 32px;">
              <a href="{cta_url}" style="display:inline-block;background:{_COLOR_CTA};color:#ffffff;text-decoration:none;font-size:16px;font-weight:700;padding:14px 28px;border-radius:999px;">
                {cta_label}
              </a>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:16px 36px 8px 36px;">
              <p style="margin:0;font-size:12px;line-height:1.45;color:{_COLOR_MUTED};">{disclaimer}</p>
            </td>
          </tr>
          <tr>
            <td align="center" style="padding:12px 0 0 0;">
              <img src="{footer_src}" width="600" alt="{site}" style="display:block;width:100%;max-width:600px;height:auto;border:0;" />
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _post_email(
    *,
    to_emails: list[str],
    subject: str,
    text: str,
    html: str,
    attachments: list[tuple[str, bytes]] | None = None,
) -> bool:
    api_key = (settings.resend_api_key or "").strip()
    if not api_key:
        level = logging.WARNING if settings.app_env == "prod" else logging.INFO
        logger.log(
            level,
            "transactional_email_skipped to=%s subject=%s reason=no_resend_api_key",
            ",".join(to_emails),
            subject,
        )
        return False
    from_email = resolved_from_email()
    payload: dict = {
        "from": from_email,
        "to": to_emails,
        "subject": subject,
        "text": text,
        "html": html,
    }
    if attachments:
        import base64

        payload["attachments"] = [
            {
                "filename": name,
                "content": base64.b64encode(blob).decode("ascii"),
            }
            for name, blob in attachments
            if name and blob
        ]
    try:
        resp = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=60.0,
        )
        if resp.status_code >= 300:
            logger.warning(
                "transactional_email_failed to=%s status=%s body=%s from=%s",
                ",".join(to_emails),
                resp.status_code,
                resp.text[:300],
                from_email,
            )
            return False
        logger.info(
            "transactional_email_sent to=%s subject=%s from=%s",
            ",".join(to_emails),
            subject,
            from_email,
        )
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("transactional_email_error to=%s err=%s", ",".join(to_emails), exc)
        return False


def send_email(*, to_email: str, subject: str, text: str, html: str) -> bool:
    return _post_email(to_emails=[to_email], subject=subject, text=text, html=html)


def send_email_many(
    *,
    to_emails: list[str],
    subject: str,
    text: str,
    html: str,
    attachments: list[tuple[str, bytes]] | None = None,
) -> bool:
    recipients = [part for part in (to_emails or []) if str(part).strip()]
    if not recipients:
        logger.info("transactional_email_no_recipients subject=%s", subject)
        return False
    return _post_email(
        to_emails=recipients,
        subject=subject,
        text=text,
        html=html,
        attachments=attachments,
    )


def send_verify_email(*, to_email: str, token: str) -> bool:
    url = build_verify_email_url(token, email=to_email)
    if not email_configured():
        logger.info("verify_email_link to=%s url=%s", to_email, url)
    subject = "Confirme Seu E-mail — Story R Us"
    text = (
        "Confirme Seu E-mail\n\n"
        "Falta só um passo para começar sua jornada com a STORY R US. "
        "Confirme seu e-mail para ativar sua conta e acompanhar a criação "
        "de histórias personalizadas inesquecíveis.\n\n"
        f"Confirmar Meu E-mail: {url}\n\n"
        f"O link vale por {settings.email_verify_ttl_min} minutos.\n"
        "Se você não criou esta conta, pode ignorar esta mensagem com segurança.\n\n"
        "www.storyrus.ai"
    )
    html = _branded_html(
        hero_file="confirm-hero.jpg",
        hero_alt="Story R Us — Confirme Seu E-mail",
        heading="Confirme Seu E-mail",
        description_html=(
            "Falta só um passo para começar sua jornada com a "
            "<strong>STORY R US</strong>. Confirme seu e-mail para ativar "
            "sua conta e acompanhar a criação de histórias personalizadas "
            "inesquecíveis."
        ),
        cta_label="Confirmar Meu E-mail →",
        cta_url=url,
        disclaimer=("Se você não criou esta conta, pode ignorar esta mensagem com segurança."),
    )
    return send_email(to_email=to_email, subject=subject, text=text, html=html)


def send_password_reset_email(*, to_email: str, token: str) -> bool:
    url = build_password_reset_url(token, email=to_email)
    if not email_configured():
        logger.info("password_reset_link to=%s url=%s", to_email, url)
    subject = "Esqueceu Sua Senha? — Story R Us"
    text = (
        "Esqueceu Sua Senha?\n\n"
        "Sem problemas! Clique no link abaixo para redefinir sua senha e "
        "voltar a acessar sua conta na STORY R US com segurança.\n\n"
        f"Redefinir Minha Senha: {url}\n\n"
        f"O link vale por {settings.password_reset_ttl_min} minutos. "
        "Se você não solicitou esta redefinição, pode ignorar esta mensagem "
        "com segurança.\n\n"
        "www.storyrus.ai"
    )
    html = _branded_html(
        hero_file="reset-hero.jpg",
        hero_alt="Story R Us — Esqueceu Sua Senha?",
        heading="Esqueceu Sua Senha?",
        description_html=(
            "Sem problemas! Clique no botão abaixo para redefinir sua senha "
            "e voltar a acessar sua conta na <strong>STORY R US</strong> "
            "com segurança."
        ),
        cta_label="Redefinir Minha Senha →",
        cta_url=url,
        disclaimer=(
            "Se você não solicitou esta redefinição, pode ignorar esta mensagem com segurança."
        ),
    )
    return send_email(to_email=to_email, subject=subject, text=text, html=html)


def new_order_notify_recipients() -> list[str]:
    """Destinatários do aviso de pedido novo (csv em NEW_ORDER_NOTIFY_EMAILS)."""
    raw = (settings.new_order_notify_emails or "").strip()
    return [part.strip() for part in raw.split(",") if part.strip()]


def _new_order_html(
    *,
    rows: list[tuple[str, str]],
    summary: str,
    order_url: str,
    heading: str = "Novo pedido aberto",
    lead: str = "Um pedido novo apareceu no painel Story R Us.",
) -> str:
    site = "www.storyrus.ai"
    rows_html = "".join(
        f"<tr>"
        f'<td style="padding:6px 12px 6px 0;color:{_COLOR_MUTED};font-size:14px;">{escape(label)}</td>'
        f'<td style="padding:6px 0;color:{_COLOR_INK};font-size:14px;font-weight:600;">'
        f"{escape(value)}</td>"
        f"</tr>"
        for label, value in rows
    )
    summary_html = escape(summary).replace("\n", "<br />")
    cta = ""
    if order_url:
        cta = (
            f'<p style="margin:20px 0 0 0;"><a href="{escape(order_url, quote=True)}" '
            f'style="display:inline-block;background:{_COLOR_CTA};color:#ffffff;text-decoration:none;'
            f'font-size:15px;font-weight:700;padding:12px 24px;border-radius:999px;">'
            "Abrir o painel →</a></p>"
        )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>Novo pedido</title>
</head>
<body style="margin:0;padding:0;background:{_COLOR_BG};font-family:Arial,Helvetica,sans-serif;color:{_COLOR_INK};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_COLOR_BG};">
    <tr>
      <td align="center" style="padding:24px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;">
          <tr>
            <td style="padding:28px 32px;">
              <h1 style="margin:0 0 4px 0;font-size:22px;line-height:1.3;color:{_COLOR_INK};">{escape(heading)}</h1>
              <p style="margin:0 0 18px 0;font-size:14px;color:{_COLOR_MUTED};">{escape(lead)}</p>
              <table role="presentation" cellpadding="0" cellspacing="0" border="0">{rows_html}</table>
              <p style="margin:18px 0 0 0;font-size:14px;font-weight:700;color:{_COLOR_INK};">Resumo do pedido</p>
              <p style="margin:6px 0 0 0;font-size:14px;line-height:1.55;color:{_COLOR_INK};">{summary_html}</p>
              {cta}
              <p style="margin:22px 0 0 0;font-size:12px;color:{_COLOR_MUTED};">{site}</p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_new_order_email(
    *,
    child_name: str,
    summary: str,
    client_name: str = "",
    client_email: str = "",
    order_url: str = "",
) -> bool:
    """Avisa o time interno quando um pedido novo abre no painel (best-effort)."""
    recipients = new_order_notify_recipients()
    if not recipients:
        logger.info("new_order_email_skipped reason=no_recipients")
        return False
    name = (child_name or "").strip() or "sem nome"
    url = (order_url or "").strip() or f"{public_web_origin()}/pedidos"
    subject = f"Novo pedido — {name}"
    rows: list[tuple[str, str]] = [("Criança", name)]
    if (client_name or "").strip():
        rows.append(("Cliente", client_name.strip()))
    if (client_email or "").strip():
        rows.append(("E-mail", client_email.strip()))
    summary_text = (summary or "").strip() or "(sem resumo)"
    text = "\n".join(
        [
            "Novo pedido aberto na Story R Us.",
            "",
            *[f"{label}: {value}" for label, value in rows],
            "",
            "Resumo do pedido:",
            summary_text,
            "",
            f"Ver no painel: {url}",
        ]
    )
    html = _new_order_html(rows=rows, summary=summary_text, order_url=url)
    return send_email_many(to_emails=recipients, subject=subject, text=text, html=html)


def _preview_ready_html(*, child_name: str, preview_url: str) -> str:
    site = "www.storyrus.ai"
    who = ""
    if (child_name or "").strip():
        who = f" de <strong>{escape(child_name.strip())}</strong>"
    cta = (
        f'<p style="margin:22px 0 0 0;"><a href="{escape(preview_url, quote=True)}" '
        f'style="display:inline-block;background:{_COLOR_CTA};color:#ffffff;text-decoration:none;'
        f'font-size:16px;font-weight:700;padding:14px 28px;border-radius:999px;">'
        "Ver meu pedido →</a></p>"
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>A prévia ficou pronta</title>
</head>
<body style="margin:0;padding:0;background:{_COLOR_BG};font-family:Arial,Helvetica,sans-serif;color:{_COLOR_INK};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{_COLOR_BG};">
    <tr>
      <td align="center" style="padding:24px 12px;">
        <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;width:100%;background:#ffffff;border-radius:16px;">
          <tr>
            <td style="padding:28px 32px;">
              <h1 style="margin:0 0 8px 0;font-size:24px;line-height:1.3;color:{_COLOR_INK};">A prévia ficou pronta! 🎉</h1>
              <p style="margin:0;font-size:15px;line-height:1.55;color:{_COLOR_INK};">
                A história e as ilustrações{who} já foram criadas. Acompanhe seu livro em Meus Pedidos.
              </p>
              {cta}
              <p style="margin:22px 0 0 0;font-size:12px;color:{_COLOR_MUTED};">
                Você recebeu este e-mail porque criou um livro na Story R Us. {site}
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def send_preview_ready_email(
    *,
    to_email: str,
    child_name: str = "",
    preview_url: str = "",
) -> bool:
    """Avisa o cliente que a prévia (história + imagens) ficou pronta (best-effort)."""
    email = (to_email or "").strip()
    if not email:
        logger.info("preview_ready_email_skipped reason=no_email")
        return False
    name = (child_name or "").strip()
    url = (preview_url or "").strip() or build_preview_ready_url()
    subject = (
        f"A prévia do livro de {name} ficou pronta — Story R Us"
        if name
        else "Sua prévia ficou pronta — Story R Us"
    )
    text = "\n".join(
        [
            "A prévia ficou pronta!",
            "",
            (
                f"A história e as ilustrações de {name} já foram criadas."
                if name
                else "A história e as ilustrações do seu livro já foram criadas."
            ),
            "Acompanhe seu livro em Meus Pedidos.",
            "",
            f"Ver meu pedido: {url}",
            "",
            "www.storyrus.ai",
        ]
    )
    html = _preview_ready_html(child_name=name, preview_url=url)
    return send_email(to_email=email, subject=subject, text=text, html=html)


def _book_title(project) -> str:
    profile = project.book_profile if isinstance(project.book_profile, dict) else {}
    title = str(profile.get("title") or "").strip()
    if title:
        return title
    text = (project.story_text or "").strip()
    for line in text.splitlines():
        cleaned = line.strip()
        if cleaned.lower().startswith("título:") or cleaned.lower().startswith("titulo:"):
            return cleaned.split(":", 1)[1].strip() or "Livro Story R Us"
    return "Livro Story R Us"


def _size_label(book_size: str | None) -> str:
    return {"M": "20 × 20 cm", "P": "15 × 15 cm"}.get(book_size or "", book_size or "—")


def _cover_label(cover_type: str | None) -> str:
    return {"soft": "Capa flexível", "hard": "Capa dura"}.get(cover_type or "", cover_type or "—")


def _shop_attachments(db, project, order) -> list[tuple[str, bytes]]:
    """Capa/contracapa separadas e miolo espelhado. Sem as páginas, usa o PDF do livro."""
    built = _shop_pdfs(db, project, order)
    if built:
        return built
    from app import storage

    key = (getattr(project, "ebook_url", None) or "").strip()
    if not key:
        return []
    try:
        blob = storage.get_bytes(key)
    except Exception:
        logger.warning("print_shop_pdf_missing code=%s", order.code)
        return []
    if not blob.startswith(b"%PDF"):
        return []
    return [(f"{order.code}.pdf", blob)]


def _shop_pdfs(db, project, order) -> list[tuple[str, bytes]] | None:
    if db is None or getattr(project, "id", None) is None:
        return None
    from sqlalchemy import select

    from app import storage
    from app.models import Asset
    from app.workers import book_render

    language = (project.language or "pt-BR").strip()
    rows = db.scalars(select(Asset).where(Asset.project_id == project.id)).all()

    def latest(role: str, page: int | None = None):
        found = []
        for asset in rows:
            meta = asset.meta or {}
            if meta.get("workflow") != 1 or meta.get("language") != language or meta.get("role") != role:
                continue
            if page is not None and meta.get("page") != page:
                continue
            found.append(asset)
        return found[-1] if found else None

    cover = latest("01_CAPA")
    back = latest("04_CONTRACAPA")
    if cover is None:
        return None
    pages: list[bytes] = []
    for number in range(1, 17):
        asset = latest("com_texto", number)
        if asset is None:
            return None
        pages.append(storage.get_bytes(asset.storage_key))
    front_bytes = storage.get_bytes(cover.storage_key)
    back_bytes = (
        storage.get_bytes(back.storage_key)
        if back is not None
        else book_render.back_cover(front_bytes)
    )
    size_cm = 15 if (order.book_size or project.book_size) == "P" else 20
    covers, interior = book_render.shop_pdfs(
        front_bytes,
        back_bytes,
        pages,
        dedication=project.dedication,
        size_cm=size_cm,
        title=_book_title(project),
    )
    code = order.code
    return [
        (f"{code}_01_Capa_e_Contracapa_Separadas_Sangria_5mm.pdf", covers),
        (f"{code}_02_Miolo_Impares_Espelhadas_Dedicatoria_Sangria_5mm.pdf", interior),
    ]


def notify_print_shop(_db, project, order) -> bool:
    """E-mail interno com a ficha da gráfica e os dois PDFs de impressão em anexo."""
    attachments = _shop_attachments(_db, project, order)
    account = project.user
    postal = "".join(ch for ch in (order.postal_code or "") if ch.isdigit())
    if len(postal) == 8:
        postal = f"{postal[:5]}-{postal[5:]}"
    address = ", ".join(
        part
        for part in (
            (order.street or "").strip(),
            (order.number or "").strip(),
            (order.complement or "").strip(),
            (order.district or "").strip(),
            " / ".join(
                part
                for part in ((order.city or "").strip(), (order.state or "").strip())
                if part
            ),
            postal,
        )
        if part
    )
    rows = [
        ("Pedido", order.code),
        ("Título", _book_title(project)),
        ("Protagonista", (project.child_name or "").strip() or "—"),
        ("Idade", str(project.child_age) if project.child_age else "—"),
        ("Tamanho", _size_label(order.book_size or project.book_size)),
        ("Capa", _cover_label(order.cover_type or project.cover_type)),
        ("Quantidade", str(order.quantity or 1)),
        ("Idioma", (project.language or "pt-BR").strip()),
        ("Dedicatória", (project.dedication or "").strip() or "—"),
        ("Destinatário", (order.recipient_name or "").strip() or "—"),
        ("Entrega", address or "—"),
        ("Cliente", (account.full_name or "").strip() or "—"),
        ("E-mail do cliente", (account.email or "").strip() or "—"),
        ("Telefone", (account.phone or "").strip() or "—"),
    ]
    subject = f"Gráfica — {order.code} — {(project.child_name or 'livro').strip()}"
    paired = len(attachments) == 2
    intro = (
        "Livro aprovado para impressão. Encaminhe este e-mail para a gráfica. "
        "O primeiro anexo traz a contracapa e a capa em páginas separadas, com sangria de 5 mm. "
        "O segundo é o miolo: páginas ímpares espelhadas, dedicatória e a mesma sangria."
        if paired
        else (
            "Livro aprovado para impressão. Encaminhe este e-mail para a gráfica. "
            "O anexo é o PDF aprovado pela família."
            if attachments
            else "Livro aprovado para impressão. Os PDFs não estavam disponíveis para anexar."
        )
    )
    text = "\n".join([intro, "", *[f"{label}: {value}" for label, value in rows], "", "www.storyrus.ai"])
    html = _new_order_html(
        rows=rows,
        summary=intro,
        order_url=f"{public_web_origin()}/pedidos",
        heading="Livro aprovado para a gráfica",
        lead="Encaminhe esta ficha e os PDFs em anexo.",
    )
    return send_email_many(
        to_emails=new_order_notify_recipients(),
        subject=subject,
        text=text,
        html=html,
        attachments=attachments or None,
    )
