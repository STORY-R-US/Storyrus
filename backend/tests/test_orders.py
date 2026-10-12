"""Pedido criado quando a foto do livro chega, e lido só no painel do dono."""

from app.config import settings
from app.orders import build_book_order_summary

CARTOON = (
    "NOVO LIVRO STORY R US CARTOON\n"
    "Nome: Lia\n"
    "Idioma: Português\n"
    "Tema: Papai herói\n"
    "Personagens: Lia, Vovó, Totó\n"
    "Fotos anexadas: 1 (arquivo recebido)"
)

REALISTA = (
    "NOVO LIVRO STORY R US REALISTA\n"
    "Nome: Lila\n"
    "Idioma: Inglês\n"
    "Tema: Aventura no espaço\n"
    "Personagens: Lila\n"
    "Fotos anexadas: 2 (arquivos recebidos)"
)

CLIENT = "Cliente: Ana Souza\nE-mail: ana@email.com\nTelefone: 11999999999\nEndereço: Rua A, 10"


def test_summary_cartoon_lists_child_and_extras():
    text = build_book_order_summary(
        style="cartoon",
        child_name="Lia",
        language="pt-BR",
        theme="Papai herói",
        extra_names=["Vovó", "Lia", "Totó"],
        photo_count=1,
    )
    assert text == CARTOON


def test_summary_records_pet_gender_and_companion():
    text = build_book_order_summary(
        style="realistic",
        child_name="Maya",
        language="pt-BR",
        theme="Maya, Minha Cachorra Carinhosa",
        extra_names=["Ana"],
        photo_count=1,
        gender="f",
        subject="pet",
        also_name="Max",
        also_gender="m",
        also_subject="pet",
    )
    assert "Nome: Maya\n" in text
    assert "Protagonista: Pet\n" in text
    assert "Gênero: Feminino\n" in text
    assert "Nome do pet: Max\n" in text
    assert "Gênero do pet: Masculino\n" in text
    assert "Personagens: Maya, Max, Ana\n" in text
    assert "Quantidade:" not in text


def test_summary_records_copy_count_for_party_favors():
    text = build_book_order_summary(
        style="realistic",
        child_name="Lila",
        language="pt-BR",
        theme="Aniversário",
        extra_names=[],
        photo_count=1,
        quantity=20,
    )
    assert text.endswith("Quantidade: 20\nFotos anexadas: 1 (arquivo recebido)")


def test_summary_anything_but_cartoon_is_realista():
    text = build_book_order_summary(
        style="realistic",
        child_name="Lila",
        language="en",
        theme="Aventura no espaço",
        extra_names=[],
        photo_count=2,
    )
    assert text == REALISTA
    for style in ("cgi_3d", "anime", "realista", None, ""):
        again = build_book_order_summary(
            style=style,
            child_name="Lila",
            language="es",
            theme="Un mundo de colores",
            extra_names=["mamá"],
            photo_count=1,
        )
        assert again.startswith("NOVO LIVRO STORY R US REALISTA\n")
        assert "Idioma: Espanhol\n" in again
        assert "Personagens: Lila, mamá\n" in again
        assert again.endswith("Fotos anexadas: 1 (arquivo recebido)")


def test_summary_keeps_client_registration_and_drops_blank_notes():
    text = build_book_order_summary(
        style="cartoon",
        child_name="Lia",
        language="pt-BR",
        theme="Papai herói",
        extra_names=["Vovó", "Totó"],
        photo_count=1,
        client_name="Ana Souza",
        client_email="ana@email.com",
        client_phone="11999999999",
        client_address="Rua A,\n10",
        client_notes="  ",
    )
    assert text == CARTOON + "\n" + CLIENT
    noted = build_book_order_summary(
        style="cartoon",
        child_name="Lia",
        language="pt-BR",
        theme="Papai herói",
        extra_names=["Vovó", "Totó"],
        photo_count=1,
        client_name="Ana Souza",
        client_email="ana@email.com",
        client_phone="11999999999",
        client_address="Rua A, 10",
        client_notes="entregar\nà tarde",
    )
    assert noted.endswith("Observação: entregar à tarde")


def _create(auth_client, **extra):
    body = {
        "style": "cartoon",
        "child_name": "Lia",
        "child_age": 4,
        "theme": "fathers",
        "book_size": "P",
        "cover_type": "soft",
        "language": "pt-BR",
    }
    body.update(extra)
    r = auth_client.post("/v1/projects", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _jpeg() -> bytes:
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (8, 8), (20, 40, 60)).save(buf, format="JPEG")
    return buf.getvalue()


def _photo(auth_client, pid, **fields):
    data = {
        "language": "pt-BR",
        "theme_label": "Papai herói",
        "extra_names": "Vovó, Totó",
        "client_name": "Ana Souza",
        "client_email": "ana@email.com",
        "client_phone": "11999999999",
        "client_address": "Rua A, 10",
    }
    data.update(fields)
    return auth_client.post(
        f"/v1/projects/{pid}/photo",
        files={"file": ("foto.jpg", _jpeg(), "image/jpeg")},
        data=data,
    )


def test_photo_upload_opens_one_order_for_the_owner(auth_client, monkeypatch):
    monkeypatch.setattr("app.storage.put_bytes", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.storage.presign_get", lambda key: f"https://fotos.test/{key}")
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    pid = _create(auth_client)

    denied = auth_client.get("/v1/usage")
    assert denied.status_code == 401
    assert "NOVO LIVRO" not in denied.text

    up = _photo(auth_client, pid)
    assert up.status_code == 201, up.text
    assert b"\xff\xd8" not in up.content

    owner_once = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert owner_once.status_code == 200, owner_once.text
    assert len(owner_once.json()["orders"]) == 1
    assert owner_once.json()["orders"][0]["summary"] == CARTOON + "\n" + CLIENT

    again = _photo(auth_client, pid, extra_names="outra pessoa")
    assert again.status_code == 201, again.text

    owner = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert owner.status_code == 200, owner.text
    orders = owner.json()["orders"]
    assert len(orders) == 1
    assert orders[0]["project_id"] == pid
    # Segunda foto atualiza o resumo (contagem + extras do último envio).
    assert "Fotos anexadas: 2" in orders[0]["summary"]
    assert "outra pessoa" in orders[0]["summary"]
    assert "Cliente: Ana Souza" in orders[0]["summary"]
    assert "foto.jpg" not in orders[0]["summary"]
    assert orders[0]["photo_urls"]
    assert orders[0]["photo_urls"][0].startswith("https://fotos.test/")
    assert orders[0]["print_code"].startswith("SR-")
    assert orders[0]["print_order_id"]
    assert orders[0]["payment_status"] == "unpaid"
    assert orders[0]["book_files"] == []


def test_realista_order_uses_typed_theme_and_site_language(auth_client, monkeypatch):
    monkeypatch.setattr("app.storage.put_bytes", lambda *args, **kwargs: None)
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    pid = _create(
        auth_client,
        style="realistic",
        child_name="Lila",
        theme="aventura",
        book_size="M",
        cover_type="hard",
    )
    up = _photo(
        auth_client,
        pid,
        language="en",
        theme_label="Aventura no espaço",
        extra_names="",
    )
    assert up.status_code == 201, up.text

    owner = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    summary = owner.json()["orders"][0]["summary"]
    assert summary == (
        "NOVO LIVRO STORY R US REALISTA\n"
        "Nome: Lila\n"
        "Idioma: Inglês\n"
        "Tema: Aventura no espaço\n"
        "Personagens: Lila\n"
        "Fotos anexadas: 1 (arquivo recebido)\n" + CLIENT
    )


def test_logged_in_account_opens_the_order_without_the_form(client, monkeypatch):
    monkeypatch.setattr("app.storage.put_bytes", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.storage.presign_get", lambda key: f"https://fotos.test/{key}")
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    from tests.conftest import signup_and_verify

    token = signup_and_verify(
        client,
        "ana@email.com",
        password="senha-forte",
        password_confirm="senha-forte",
        full_name="Ana Souza",
        phone="11988887777",
    )
    client.headers.update({"Authorization": f"Bearer {token}"})
    pid = _create(client)
    up = client.post(
        f"/v1/projects/{pid}/photo",
        files={"file": ("foto.jpg", _jpeg(), "image/jpeg")},
        data={"language": "pt-BR", "theme_label": "Papai herói"},
    )
    assert up.status_code == 201, up.text
    owner = client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    summary = owner.json()["orders"][0]["summary"]
    # Conta logada ainda pode enviar buyer vazio no upload; Studio passará o perfil.
    assert "ana@email.com" in summary


def test_guest_cannot_create_project_or_order(guest_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    r = guest_client.post("/v1/projects", json={})
    assert r.status_code == 403
    assert "Cadastro" in r.json()["detail"]
    owner = guest_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert owner.json()["orders"] == []


def test_several_photos_count_together_on_one_order(auth_client, monkeypatch):
    monkeypatch.setattr("app.storage.put_bytes", lambda *args, **kwargs: None)
    monkeypatch.setattr("app.storage.presign_get", lambda key: f"https://fotos.test/{key}")
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    pid = _create(auth_client)
    first = _photo(auth_client, pid, finalize="0")
    assert first.status_code == 201, first.text
    waiting = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    # Pedido abre na primeira foto; a segunda só atualiza a contagem.
    assert len(waiting.json()["orders"]) == 1
    assert "Fotos anexadas: 1" in waiting.json()["orders"][0]["summary"]
    second = auth_client.post(
        f"/v1/projects/{pid}/photo",
        files={"file": ("lado.jpg", _jpeg(), "image/jpeg")},
        data={
            "language": "pt-BR",
            "theme_label": "Papai herói",
            "client_name": "Ana Souza",
            "client_email": "ana@email.com",
            "client_phone": "11999999999",
            "client_address": "Rua A, 10",
        },
    )
    assert second.status_code == 201, second.text
    owner = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    orders = owner.json()["orders"]
    assert len(orders) == 1
    assert "Fotos anexadas: 2 (arquivos recebidos)" in orders[0]["summary"]
    assert len(orders[0]["photo_urls"]) == 2


def test_unreadable_photo_is_rejected(auth_client, monkeypatch):
    def _forbid_put(*_args, **_kwargs):
        raise AssertionError("nao grava")

    monkeypatch.setattr("app.storage.put_bytes", _forbid_put)
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    pid = _create(auth_client)
    up = auth_client.post(
        f"/v1/projects/{pid}/photo",
        files={"file": ("foto.heic", b"not-a-photo", "image/heic")},
        data={
            "client_name": "Ana Souza",
            "client_email": "ana@email.com",
            "client_phone": "11999999999",
            "client_address": "Rua A, 10",
        },
    )
    assert up.status_code == 400
    assert "HEIC" in up.json()["detail"]
    owner = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert owner.json()["orders"] == []


def test_empty_photo_does_not_open_an_order(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "usage_dashboard_password", "segredo")
    monkeypatch.setattr(settings, "usage_dashboard_password_previous", None)
    pid = _create(auth_client, style="cgi_3d", child_name="Lila")
    up = auth_client.post(
        f"/v1/projects/{pid}/photo",
        files={"file": ("foto.jpg", b"", "image/jpeg")},
    )
    assert up.status_code == 400
    owner = auth_client.get("/v1/usage", headers={"X-Usage-Password": "segredo"})
    assert owner.json()["orders"] == []
