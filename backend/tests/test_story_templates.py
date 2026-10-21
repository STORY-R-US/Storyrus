"""Testes do catálogo de histórias prontas (templates traduzidos)."""

from app.story_templates import (
    STORY_TEMPLATES,
    build_name_rhyme,
    illustration_notes,
    list_templates,
    render_template,
)

_CATALOG_JSON_IDS = {
    "alfabeto_amazonia",
    "alfabeto_frutas",
    "numeros_1_15",
    "cores_basicas",
    "grande_pequeno",
    "mergulho_mar",
}


def test_catalog_includes_amazonia():
    assert "alfabeto_amazonia" in STORY_TEMPLATES
    assert _CATALOG_JSON_IDS <= set(STORY_TEMPLATES)
    assert len(STORY_TEMPLATES) == 12
    meta = list_templates()
    assert {m["id"] for m in meta} == set(STORY_TEMPLATES)
    amazonia = next(m for m in meta if m["id"] == "alfabeto_amazonia")
    assert amazonia["paginas"] == 29
    frutas = next(m for m in meta if m["id"] == "alfabeto_frutas")
    assert frutas["paginas"] == 29
    assert next(m for m in meta if m["id"] == "numeros_1_15")["paginas"] == 18
    assert next(m for m in meta if m["id"] == "cores_basicas")["paginas"] == 15
    assert next(m for m in meta if m["id"] == "grande_pequeno")["paginas"] == 15
    assert next(m for m in meta if m["id"] == "mergulho_mar")["paginas"] == 17
    for m in meta:
        assert m["titulo"] and m["tematica"] and m["paginas"] >= 13


def test_render_replaces_name_everywhere():
    text = render_template("nave_vermelha", "Matteo")
    assert text.startswith("Título: Matteo e sua nave vermelha")
    assert "{NOME}" not in text
    # formato compatível com _parse_pages/_parse_title
    assert "Página 1:" in text and "Página 15:" in text


def test_amazonia_dedication_and_name_rhyme():
    text = render_template("alfabeto_amazonia", "Matteo", gender="boy")
    assert "{NOME}" not in text
    assert "Título: Matteo na Amazônia" in text
    assert "Para você, Matteo, pequeno aventureiro" in text
    assert "a floresta o leve" in text
    assert "Preservar a Amazônia" in text
    assert "aventureiros" not in text.lower()
    assert "M · A · T · T · E · O" in text
    assert "menino valente" in text
    assert "O é ousado" in text
    assert "Macaco" not in text.split("Página 15:")[0]
    assert "Arara" not in text.split("Página 3:")[0]
    # conteúdo animal continua nas páginas A–Z
    assert "O macaco usa" in text
    assert "A arara voa" in text
    assert "O kinkajú vive" in text
    assert "O uakari tem" in text
    assert "O iapu é um pássaro" in text
    assert "O zogue-zogue é um macaco" in text
    assert "Da arara até o zogue-zogue, Matteo" in text
    for banned in ("koala", "wombat", "iaque", "zebra", "paisagem fria"):
        assert banned not in text.lower()
    # dedicatória longa não pode fragmentar o parse das demais páginas
    from app.workers.handlers import _parse_pages

    pages = _parse_pages(text)
    assert len(pages) == 29
    assert len(pages[0]) > 260
    assert pages[2].startswith("A arara voa")


def test_amazonia_dedication_girl():
    text = render_template("alfabeto_amazonia", "Ana", gender="girl")
    assert "Para você, Ana, pequena aventureira" in text
    assert "a floresta a leve" in text
    assert "pequeno aventureiro" not in text
    assert "menina valente" in text


def test_name_rhyme_never_uses_animals():
    rhyme = build_name_rhyme("Matteo", "boy")
    for banned in ("Macaco", "Arara", "Onça", "Tucano", "Boto"):
        assert banned.lower() not in rhyme.lower()
    assert "menino valente" in rhyme
    assert "T é terno" in rhyme
    assert "T é talentoso" in rhyme  # letra repetida não repete a palavra
    assert "O é ousado" in rhyme


def test_amazonia_notes_keep_child_and_letter():
    notes = illustration_notes("alfabeto_amazonia", "Matteo")
    assert len(notes) == 29
    assert notes[0] == ""
    assert "Matteo" in notes[1]
    assert "lado direito" in notes[1]
    assert "lado esquerdo" in notes[1]
    assert "Nenhuma letra" in notes[1]
    assert "{NOME}" not in "".join(notes)
    assert "letra grande abstrata M" in notes[14]
    assert "pulando de galho em galho" in notes[14]
    assert "letra grande abstrata K" in notes[12]
    assert "kinkaju" in notes[12].lower()
    assert "um animal so" in notes[12]
    assert "letra grande abstrata W" in notes[24]
    assert "uakari" in notes[24].lower()
    assert "um animal so" in notes[24]
    assert "letra grande abstrata Y" in notes[26]
    assert "iapu" in notes[26].lower()
    assert "um animal so" in notes[26]
    assert "letra grande abstrata Z" in notes[27]
    assert "zogue-zogue" in notes[27]
    assert "um animal so" in notes[27]
    joined = " ".join(notes).lower()
    for banned in ("koala", "wombat", "iaque", "zebra", "paisagem fria"):
        assert banned not in joined


def test_list_endpoint(auth_client):
    r = auth_client.get("/v1/projects/story-templates")
    assert r.status_code == 200, r.text
    assert len(r.json()) == 12
    ids = {t["id"] for t in r.json()}
    assert "alfabeto_amazonia" in ids
    assert _CATALOG_JSON_IDS <= ids


def test_apply_template_sets_story(auth_client):
    r = auth_client.post("/v1/projects", json={"style": "cartoon", "child_name": "Matteo"})
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    r = auth_client.post(f"/v1/projects/{pid}/story/template", json={"template_id": "mapa_secreto"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "STORY_READY"
    assert body["story_text"].startswith("Título: Matteo e seu mapa secreto")
    # sem créditos gastos: job STORY registrado como DONE com custo 0
    jobs = auth_client.get(f"/v1/projects/{pid}/jobs").json()
    story_jobs = [j for j in jobs if j["type"] == "STORY"]
    assert story_jobs and story_jobs[0]["status"] == "DONE"
    assert story_jobs[0]["cost_credits"] == 0


def test_apply_amazonia_template(auth_client):
    r = auth_client.post("/v1/projects", json={"style": "cartoon", "child_name": "Matteo"})
    pid = r.json()["id"]
    r = auth_client.post(
        f"/v1/projects/{pid}/story/template",
        json={"template_id": "alfabeto_amazonia", "gender": "boy"},
    )
    assert r.status_code == 200, r.text
    story = r.json()["story_text"]
    assert "Para você, Matteo, pequeno aventureiro" in story
    assert "Preservar a Amazônia" in story
    assert "menino valente" in story
    assert "aventureiros" not in story.lower()


def test_frutas_dedication_and_name_rhyme():
    text = render_template("alfabeto_frutas", "Matteo", gender="boy")
    assert "{NOME}" not in text
    assert "Título: Matteo no Pomar" in text
    assert "Para você, Matteo pequeno aventureiro" in text
    assert "o pomar o leve" in text
    assert "M · A · T · T · E · O" in text
    assert "menino valente" in text
    from app.workers.handlers import _parse_pages

    pages = _parse_pages(text)
    assert len(pages) == 29
    assert pages[2].startswith("O abacaxi usa")
    assert "Do abacaxi até o zimbro, Matteo" in pages[-1]


def test_frutas_dedication_girl():
    text = render_template("alfabeto_frutas", "Ana", gender="girl")
    assert "Para você, Ana pequena aventureira" in text
    assert "o pomar a leve" in text
    assert "pequeno aventureiro" not in text
    assert "menina valente" in text


def test_frutas_notes_keep_child_and_letter():
    notes = illustration_notes("alfabeto_frutas", "Matteo")
    assert len(notes) == 29
    assert notes[0] == ""
    assert "Matteo" in notes[1]
    assert "{NOME}" not in "".join(notes)
    assert "letra grande abstrata A" in notes[2]
    assert "abacaxi" in notes[2].lower()
    assert "uma fruta so" in notes[2]


def test_numeros_render_and_parse():
    text = render_template("numeros_1_15", "Matteo", gender="boy")
    assert "{NOME}" not in text
    assert "Título: Matteo e os Números" in text
    assert "pequeno aventureiro" in text
    assert "O um é um pauzinho" in text
    assert "O quinze é um e cinco" in text
    from app.workers.handlers import _parse_pages

    pages = _parse_pages(text)
    assert len(pages) == 18
    notes = illustration_notes("numeros_1_15", "Matteo")
    assert "EXATAMENTE TRES peixinhos" in notes[4]
    assert "nao amontoar onze" in notes[12]


def test_numeros_dedication_girl():
    text = render_template("numeros_1_15", "Ana", gender="girl")
    assert "pequena aventureira" in text
    assert "contar a leve" in text


def test_cores_render_and_parse():
    text = render_template("cores_basicas", "Matteo", gender="boy")
    assert "{NOME}" not in text
    assert "O preto é a noite" in text
    assert "Vermelho com amarelo" in text
    assert "Azul com vermelho" in text
    from app.workers.handlers import _parse_pages

    pages = _parse_pages(text)
    assert len(pages) == 15
    notes = illustration_notes("cores_basicas", "Matteo")
    assert "cor dominante VERMELHO" in notes[3]
    assert "pigmento vermelho e amarelo" in notes[12]


def test_mergulho_render_and_parse():
    text = render_template("mergulho_mar", "Nicolas")
    assert "{NOME}" not in text
    assert text.startswith("Título: Nicolas em um mergulho no fundo do mar")
    assert "Para você, Nicolas, com carinho e muita imaginação" in text
    assert "Nicolas mergulhou nas águas azuis" in text
    assert "GOLFINHO alegre" in text
    assert "Nicolas voltou feliz" in text
    assert "cada animal deixou uma lembrança" in text
    from app.workers.handlers import _parse_pages

    pages = _parse_pages(text)
    assert len(pages) == 17
    assert pages[1].startswith("Nicolas mergulhou")
    assert pages[-1].startswith("Nicolas voltou feliz")
    notes = illustration_notes("mergulho_mar", "Nicolas")
    assert len(notes) == 17
    assert notes[0] == ""
    assert "{NOME}" not in "".join(notes)
    assert "Nicolas" in notes[1]
    assert "golfinho" in notes[1].lower()
    assert "distancia segura" in notes[8]
    assert "distancia segura" in notes[10]
    assert "distancia segura" in notes[15]
    assert "varios animais" in notes[16]


def test_grande_pequeno_render_and_parse():
    text = render_template("grande_pequeno", "Matteo", gender="boy")
    assert "{NOME}" not in text
    assert "Grande é o elefante" in text
    assert "Pequeno é o botão" in text
    assert "Claro é o dia" in text
    from app.workers.handlers import _parse_pages

    pages = _parse_pages(text)
    assert len(pages) == 15
    notes = illustration_notes("grande_pequeno", "Matteo")
    assert "elefante" in notes[1].lower()
    assert "Cena dividida" in notes[13]


def test_apply_frutas_template(auth_client):
    r = auth_client.post("/v1/projects", json={"style": "cartoon", "child_name": "Matteo"})
    pid = r.json()["id"]
    r = auth_client.post(
        f"/v1/projects/{pid}/story/template",
        json={"template_id": "alfabeto_frutas", "gender": "boy"},
    )
    assert r.status_code == 200, r.text
    story = r.json()["story_text"]
    assert "Matteo no Pomar" in story
    assert "O abacaxi usa" in story
    assert "menino valente" in story


def test_apply_template_requires_child_name(auth_client):
    r = auth_client.post("/v1/projects", json={"style": "cartoon"})
    pid = r.json()["id"]
    r = auth_client.post(f"/v1/projects/{pid}/story/template", json={"template_id": "atacante"})
    assert r.status_code == 400


def test_apply_unknown_template_404(auth_client):
    r = auth_client.post("/v1/projects", json={"style": "cartoon", "child_name": "Ana"})
    pid = r.json()["id"]
    r = auth_client.post(f"/v1/projects/{pid}/story/template", json={"template_id": "nao_existe"})
    assert r.status_code == 404
