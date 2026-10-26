"""Links e envio de e-mail transacional (confirmação / senha)."""

from app.config import settings
from app.services.transactional_email import (
    build_password_reset_url,
    build_preview_ready_url,
    build_verify_email_url,
    email_configured,
    new_order_notify_recipients,
    resolved_from_email,
    send_email,
    send_email_many,
    send_new_order_email,
    send_password_reset_email,
    send_preview_ready_email,
    send_verify_email,
)


def test_verify_url_encodes_email_and_keeps_short_token():
    url = build_verify_email_url("abc-def_ghi", email="Ana@X.com")
    origin = settings.public_web_origin.rstrip("/")
    assert url.startswith(f"{origin}/verificar-email?")
    assert "token=abc-def_ghi" in url
    assert "email=Ana%40X.com" in url


def test_password_reset_url_encodes_token_and_email():
    url = build_password_reset_url("reset/token+plus", email="a@b.com")
    origin = settings.public_web_origin.rstrip("/")
    assert url.startswith(f"{origin}/redefinir-senha?")
    assert "token=" in url
    assert "email=a%40b.com" in url
    assert "reset/token+plus" not in url


def test_email_configured_and_from_fallback(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "")
    assert email_configured() is False
    monkeypatch.setattr(settings, "resend_api_key", " re_abc ")
    assert email_configured() is True
    monkeypatch.setattr(settings, "transactional_from_email", "  ")
    assert resolved_from_email() == "Story R Us <noreply@storyrus.ai>"
    monkeypatch.setattr(settings, "transactional_from_email", "Me <me@storyrus.ai>")
    assert resolved_from_email() == "Me <me@storyrus.ai>"


def test_send_email_posts_to_resend(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "transactional_from_email", "Story R Us <noreply@storyrus.ai>")
    calls: list[dict] = []

    class _Resp:
        status_code = 200
        text = '{"id":"ok"}'

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return _Resp()

    monkeypatch.setattr(
        "app.services.transactional_email.httpx.post",
        fake_post,
    )
    assert send_email(to_email="u@x.com", subject="Hi", text="t", html="<p>t</p>") is True
    assert calls[0]["url"] == "https://api.resend.com/emails"
    assert calls[0]["headers"]["Authorization"] == "Bearer re_test"
    assert calls[0]["json"]["to"] == ["u@x.com"]
    assert calls[0]["json"]["from"] == "Story R Us <noreply@storyrus.ai>"


def test_send_password_reset_skips_without_key(monkeypatch, caplog):
    monkeypatch.setattr(settings, "resend_api_key", "")
    monkeypatch.setattr(settings, "app_env", "prod")
    with caplog.at_level("WARNING"):
        assert send_password_reset_email(to_email="u@x.com", token="tok123") is False
    assert any("no_resend_api_key" in r.message for r in caplog.records)


def test_verify_email_html_is_branded_title_case(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "public_web_origin", "https://storyrus.ai")
    calls: list[dict] = []

    class _Resp:
        status_code = 200
        text = '{"id":"ok"}'

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        return _Resp()

    monkeypatch.setattr("app.services.transactional_email.httpx.post", fake_post)
    assert send_verify_email(to_email="u@x.com", token="tok-verify") is True
    payload = calls[0]
    assert payload["subject"] == "Confirme Seu E-mail — Story R Us"
    assert "Confirme Seu E-mail" in payload["html"]
    assert "Confirmar Meu E-mail →" in payload["html"]
    assert "confirm-hero.jpg" in payload["html"]
    assert "email-footer.jpg" in payload["html"]
    assert "token=tok-verify" in payload["html"]
    assert "Falta só um passo" in payload["html"]
    assert "Confirme Seu E-mail" in payload["text"]


def test_password_reset_html_is_branded_title_case(monkeypatch):
    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "public_web_origin", "https://storyrus.ai")
    calls: list[dict] = []

    class _Resp:
        status_code = 200
        text = '{"id":"ok"}'

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        return _Resp()

    monkeypatch.setattr("app.services.transactional_email.httpx.post", fake_post)
    assert send_password_reset_email(to_email="u@x.com", token="tok-reset") is True
    payload = calls[0]
    assert payload["subject"] == "Esqueceu Sua Senha? — Story R Us"
    assert "Esqueceu Sua Senha?" in payload["html"]
    assert "Redefinir Minha Senha →" in payload["html"]
    assert "reset-hero.jpg" in payload["html"]
    assert "token=tok-reset" in payload["html"]
    assert "Sem problemas!" in payload["html"]


def _capture_resend(monkeypatch, calls: list[dict]) -> None:
    monkeypatch.setattr(settings, "resend_api_key", "re_test")

    class _Resp:
        status_code = 200
        text = '{"id":"ok"}'

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        return _Resp()

    monkeypatch.setattr("app.services.transactional_email.httpx.post", fake_post)


def test_send_email_many_posts_to_all_recipients(monkeypatch):
    calls: list[dict] = []
    _capture_resend(monkeypatch, calls)
    sent = send_email_many(
        to_emails=["a@x.com", "b@y.com"], subject="Hi", text="t", html="<p>t</p>"
    )
    assert sent is True
    assert calls[0]["to"] == ["a@x.com", "b@y.com"]


def test_print_shop_email_attaches_the_approved_pdf(monkeypatch):
    import base64

    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "new_order_notify_emails", "sales@storyrus.ai")
    calls: list[dict] = []

    class _Resp:
        status_code = 200
        text = "ok"

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        return _Resp()

    monkeypatch.setattr("app.services.transactional_email.httpx.post", fake_post)
    pdf = b"%PDF-1.4 livro-aprovado"
    monkeypatch.setattr("app.storage.get_bytes", lambda key: pdf)

    class Bag:
        pass

    account = Bag()
    account.full_name = "Ana"
    account.email = "ana@example.com"
    account.phone = ""
    project = Bag()
    project.ebook_url = "book.pdf"
    project.book_profile = {"title": "Lia e o mar"}
    project.story_text = ""
    project.child_name = "Lia"
    project.child_age = 4
    project.language = "pt-BR"
    project.dedication = "Para Lia."
    project.book_size = "M"
    project.cover_type = "hard"
    project.user = account
    order = Bag()
    order.code = "SR-TESTE01"
    order.book_size = "M"
    order.cover_type = "hard"
    order.quantity = 1
    order.postal_code = "01310100"
    order.street = "Av. Paulista"
    order.number = "1000"
    order.complement = ""
    order.district = "Bela Vista"
    order.city = "São Paulo"
    order.state = "SP"
    order.recipient_name = "Ana"

    from app.services.transactional_email import notify_print_shop

    assert notify_print_shop(None, project, order) is True
    body = calls[0]
    assert body["to"] == ["sales@storyrus.ai"]
    assert body["subject"] == "Gráfica — SR-TESTE01 — Lia"
    assert "Lia e o mar" in body["text"]
    assert "20 × 20 cm" in body["text"]
    assert "Capa dura" in body["text"]
    assert body["attachments"][0]["filename"] == "SR-TESTE01.pdf"
    assert base64.b64decode(body["attachments"][0]["content"]) == pdf


def test_print_shop_email_attaches_cover_and_interior(monkeypatch):
    import base64

    monkeypatch.setattr(settings, "resend_api_key", "re_test")
    monkeypatch.setattr(settings, "new_order_notify_emails", "sales@storyrus.ai")
    calls: list[dict] = []

    class _Resp:
        status_code = 200
        text = "ok"

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append(json)
        return _Resp()

    monkeypatch.setattr("app.services.transactional_email.httpx.post", fake_post)
    monkeypatch.setattr(
        "app.services.transactional_email._shop_pdfs",
        lambda db, project, order: [
            (f"{order.code}_01_Capa_e_Contracapa_Separadas_Sangria_5mm.pdf", b"%PDF-capa"),
            (f"{order.code}_02_Miolo_Impares_Espelhadas_Dedicatoria_Sangria_5mm.pdf", b"%PDF-miolo"),
        ],
    )

    class Bag:
        pass

    account = Bag()
    account.full_name = "Ana"
    account.email = "ana@example.com"
    account.phone = ""
    project = Bag()
    project.child_name = "Lia"
    project.child_age = 4
    project.language = "pt-BR"
    project.dedication = "Para Lia."
    project.book_size = "M"
    project.cover_type = "hard"
    project.book_profile = {"title": "Lia e o mar"}
    project.story_text = ""
    project.user = account
    order = Bag()
    order.code = "SR-TESTE01"
    order.book_size = "M"
    order.cover_type = "hard"
    order.quantity = 1
    order.postal_code = "01310100"
    order.street = "Av. Paulista"
    order.number = "1000"
    order.complement = ""
    order.district = "Bela Vista"
    order.city = "São Paulo"
    order.state = "SP"
    order.recipient_name = "Ana"

    from app.services.transactional_email import notify_print_shop

    assert notify_print_shop(None, project, order) is True
    names = [item["filename"] for item in calls[0]["attachments"]]
    assert names == [
        "SR-TESTE01_01_Capa_e_Contracapa_Separadas_Sangria_5mm.pdf",
        "SR-TESTE01_02_Miolo_Impares_Espelhadas_Dedicatoria_Sangria_5mm.pdf",
    ]
    assert base64.b64decode(calls[0]["attachments"][1]["content"]) == b"%PDF-miolo"
    assert "páginas ímpares espelhadas" in calls[0]["text"]


def test_send_email_many_without_recipients_is_noop(monkeypatch):
    calls: list[dict] = []
    _capture_resend(monkeypatch, calls)
    assert send_email_many(to_emails=[], subject="Hi", text="t", html="<p>t</p>") is False
    assert calls == []


def test_new_order_email_targets_sales_and_eng(monkeypatch):
    monkeypatch.setattr(
        settings, "new_order_notify_emails", "sales@storyrus.ai,eng.andrevitor89@gmail.com"
    )
    monkeypatch.setattr(settings, "public_web_origin", "https://storyrus.ai")
    calls: list[dict] = []
    _capture_resend(monkeypatch, calls)

    sent = send_new_order_email(
        child_name="Lia",
        summary="NOVO LIVRO STORY R US CARTOON\nNome: Lia",
        client_name="Ana Souza",
        client_email="ana@email.com",
    )
    assert sent is True
    payload = calls[0]
    assert payload["to"] == ["sales@storyrus.ai", "eng.andrevitor89@gmail.com"]
    assert payload["subject"] == "Novo pedido — Lia"
    assert "Ana Souza" in payload["text"]
    assert "NOVO LIVRO" in payload["text"]
    assert "https://storyrus.ai/pedidos" in payload["html"]


def test_new_order_email_escapes_html(monkeypatch):
    monkeypatch.setattr(settings, "new_order_notify_emails", "sales@storyrus.ai")
    calls: list[dict] = []
    _capture_resend(monkeypatch, calls)

    send_new_order_email(child_name="<b>Lia</b>", summary="a & b")
    payload = calls[0]
    assert "&lt;b&gt;Lia&lt;/b&gt;" in payload["html"]
    assert "a &amp; b" in payload["html"]
    assert "<b>Lia</b>" not in payload["html"]


def test_new_order_email_without_recipients_is_noop(monkeypatch):
    monkeypatch.setattr(settings, "new_order_notify_emails", "   ")
    assert new_order_notify_recipients() == []
    assert send_new_order_email(child_name="Lia", summary="x") is False


def test_preview_ready_email_targets_the_client(monkeypatch):
    monkeypatch.setattr(settings, "public_web_origin", "https://storyrus.ai")
    calls: list[dict] = []
    _capture_resend(monkeypatch, calls)

    sent = send_preview_ready_email(to_email="ana@email.com", child_name="Lia")
    assert sent is True
    payload = calls[0]
    assert payload["to"] == ["ana@email.com"]
    assert payload["subject"] == "A prévia do livro de Lia ficou pronta — Story R Us"
    assert "A prévia ficou pronta!" in payload["text"]
    assert "Lia" in payload["text"]
    assert "Meus Pedidos" in payload["text"]
    assert "https://storyrus.ai/pedidos" in payload["html"]
    assert "Ver meu pedido →" in payload["html"]


def test_preview_ready_email_without_name_uses_generic_copy(monkeypatch):
    monkeypatch.setattr(settings, "public_web_origin", "https://storyrus.ai")
    calls: list[dict] = []
    _capture_resend(monkeypatch, calls)

    assert send_preview_ready_email(to_email="ana@email.com") is True
    payload = calls[0]
    assert payload["subject"] == "Sua prévia ficou pronta — Story R Us"
    assert "do seu livro" in payload["text"]


def test_preview_ready_email_without_email_is_noop(monkeypatch, caplog):
    calls: list[dict] = []
    _capture_resend(monkeypatch, calls)
    assert send_preview_ready_email(to_email="   ", child_name="Lia") is False
    assert calls == []


def test_preview_ready_url_points_to_my_orders(monkeypatch):
    monkeypatch.setattr(settings, "public_web_origin", "https://storyrus.ai/")
    assert build_preview_ready_url() == "https://storyrus.ai/pedidos"


def test_preview_ready_email_escapes_html(monkeypatch):
    calls: list[dict] = []
    _capture_resend(monkeypatch, calls)
    send_preview_ready_email(to_email="ana@email.com", child_name="<b>Lia</b>")
    html = calls[0]["html"]
    assert "&lt;b&gt;Lia&lt;/b&gt;" in html
    assert "<b>Lia</b>" not in html
