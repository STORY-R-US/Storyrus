"""
Publica os posts da Story R Us no Instagram via Instagram Graph API (Meta).

PRE-REQUISITOS (ver guia no final deste arquivo):
  1. Conta @storyrus.br como PROFISSIONAL (Comercial/Criador) ligada a uma Pagina do Facebook.
  2. Um app na Meta (developers.facebook.com) com o produto "Instagram Graph API".
  3. Um ACCESS TOKEN de longa duracao com permissoes:
       instagram_basic, instagram_content_publish, pages_show_list,
       pages_read_engagement, business_management
  4. O IG_USER_ID (id numerico da conta do Instagram).
  5. As imagens hospedadas em URL PUBLICA HTTPS (a API baixa a imagem pela URL).
     Ex.: suba a pasta docs/social-assets/real/ para o seu site e aponte IMAGE_BASE_URL.

CONFIG (variaveis de ambiente OU edite os defaults abaixo):
  IG_ACCESS_TOKEN   -> token de longa duracao
  IG_USER_ID        -> id da conta Instagram
  IMAGE_BASE_URL    -> base publica das imagens, ex.: https://storyrus.ai/social
                       (de modo que {BASE}/br/feed/feed-01-hero.jpg exista)
  IG_APP_ID / IG_APP_SECRET -> so para --exchange-token

USO:
  python publish_instagram.py --list                      # lista os posts
  python publish_instagram.py --lang br --post feed-01    # publica 1 post AGORA
  python publish_instagram.py --lang br --all             # publica tudo (com pausa)
  python publish_instagram.py --lang br --post c1 --dry-run
  python publish_instagram.py --exchange-token SEU_TOKEN_CURTO   # vira token 60 dias

OBS: a API publica IMEDIATAMENTE (nao existe horario agendado nativo na API).
     Para "agendar", use este script com o Agendador de Tarefas do Windows / cron,
     ou agende manualmente pelo Meta Business Suite.
"""
from __future__ import annotations
import argparse
import os
import sys
import time

try:
    import requests
except ImportError:
    sys.exit("Instale a dependencia:  pip install requests")

try:  # console do Windows costuma ser cp1252; emojis nas legendas quebram o print
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

GRAPH = "https://graph.facebook.com/v21.0"

ACCESS_TOKEN = os.environ.get("IG_ACCESS_TOKEN", "")
IG_USER_ID = os.environ.get("IG_USER_ID", "")
IMAGE_BASE_URL = os.environ.get("IMAGE_BASE_URL", "").rstrip("/")
APP_ID = os.environ.get("IG_APP_ID", "")
APP_SECRET = os.environ.get("IG_APP_SECRET", "")

# ------------------------------------------------------------ manifesto (BR)
# type: "single" (1 imagem), "carousel" (varias), "story" (1 imagem, sem legenda)
CAP = {
    "feed-01": "E se o seu filho fosse o heroi de um livro de verdade? 📖✨\n"
               "Voce envia uma foto e a gente cria um personagem com o rostinho dele.\n"
               "Crie a previa gratis (link na bio). 💛\n"
               "#livroinfantil #presentepersonalizado #storyrus",
    "feed-02": "Uma foto hoje vira uma memoria para a vida toda. 📸➡️📚\n"
               "Sem desenhar nem usar programa: voce manda a foto, a gente faz o resto.\n"
               "👉 storyrus.ai\n#livropersonalizado #maternidade #presentecriativo",
    "feed-03": "Espaco, dinossauros, fundo do mar, super-herois, pets… qual e a cara do seu filho? 🚀🦕\n"
               "Arrasta pra escolher — ou peca um tema sob medida. 💫\n"
               "#historiainfantil #presenteparacrianca #storyrus",
    "feed-04": "O presente de Natal que a familia guarda para sempre. 🎄\n"
               "Peca ate 15/12 e receba a tempo. 🎁\n#natal #presentedenatal #livroinfantil",
    "feed-05": "BLACK FRIDAY chegou! 🖤 Seu livro personalizado com condicao especial, so ate 29/11.\n"
               "Garanta o seu 👉 storyrus.ai\n#blackfriday #presentepersonalizado",
    "feed-06": "O aniversario dele vira uma historia so dele. 🎂📖 Um presente que ninguem esquece.\n"
               "#aniversario #presentecriativo",
    "feed-07": "O presente que emociona os avos. 💛 Netos e avos na mesma historia.\n"
               "#diadosavos #presenteparaavo #familia",
    "feed-08": "Seu filho e o melhor amigo na mesma aventura. 🐶 O pet da familia tambem vira personagem!\n"
               "#pets #petlovers #livroinfantil",
    "feed-09": "O primeiro presente que ele guarda para sempre. 🍼 Perfeito para recem-nascidos.\n"
               "#chadebebe #recemnascido #presentebebe",
    "feed-10": "\"A reacao dela ao se ver no livro nao tem preco.\" ⭐⭐⭐⭐⭐\n"
               "Crie a previa gratis e viva isso tambem. 👉 storyrus.ai\n"
               "#depoimento #presentepersonalizado",
    "c1": "Como funciona, em 3 passos simples 👇\n1) Envie a foto  2) A gente cria  3) Receba e aprove.\n"
          "Crie a previa gratis 👉 storyrus.ai\n#livroinfantil #comofunciona #storyrus",
    "c2": "Qual e a cara do seu filho? 🚀🦕🌊🦸🐶 Arrasta e escolha o tema — ou peca sob medida.\n"
          "#historiainfantil #presenteparacrianca #storyrus",
    "c3": "Presentes de Natal que emocionam 🎄 um para cada pessoa que voce ama.\n"
          "Peca ate 15/12. 🎁\n#natal #presentedenatal #livroinfantil",
    "c4": "Da foto real ao personagem do livro ✨ Veja a transformacao!\n"
          "Envie uma foto e receba a previa gratis 👉 storyrus.ai\n#antesedepois #livropersonalizado",
    "c5": "Ficou com duvida? Respondemos as perguntas mais comuns 👇\n"
          "Crie a previa gratis e veja na pratica. 👉 storyrus.ai\n#faq #livroinfantil #storyrus",
}

POSTS = [
    {"key": "feed-01", "type": "single", "path": "feed/feed-01-hero.jpg"},
    {"key": "feed-02", "type": "single", "path": "feed/feed-02-produto.jpg"},
    {"key": "feed-03", "type": "single", "path": "feed/feed-03-temas.jpg"},
    {"key": "feed-04", "type": "single", "path": "feed/feed-04-natal.jpg"},
    {"key": "feed-05", "type": "single", "path": "feed/feed-05-blackfriday.jpg"},
    {"key": "feed-06", "type": "single", "path": "feed/feed-06-aniversario.jpg"},
    {"key": "feed-07", "type": "single", "path": "feed/feed-07-avos.jpg"},
    {"key": "feed-08", "type": "single", "path": "feed/feed-08-pets.jpg"},
    {"key": "feed-09", "type": "single", "path": "feed/feed-09-bebe.jpg"},
    {"key": "feed-10", "type": "single", "path": "feed/feed-10-prova.jpg"},
    {"key": "c1", "type": "carousel", "prefix": "carrossel/c1-comofunciona", "n": 5},
    {"key": "c2", "type": "carousel", "prefix": "carrossel/c2-temas", "n": 7},
    {"key": "c3", "type": "carousel", "prefix": "carrossel/c3-natal", "n": 6},
    {"key": "c4", "type": "carousel", "prefix": "carrossel/c4-antesdepois", "n": 5},
    {"key": "c5", "type": "carousel", "prefix": "carrossel/c5-faq", "n": 6},
    {"key": "story-01", "type": "story", "path": "stories/story-01-cta.jpg"},
    {"key": "story-02", "type": "story", "path": "stories/story-02-prazo.jpg"},
    {"key": "story-03", "type": "story", "path": "stories/story-03-comofunciona.jpg"},
    {"key": "story-04", "type": "story", "path": "stories/story-04-enquete.jpg"},
    {"key": "story-05", "type": "story", "path": "stories/story-05-prova.jpg"},
    {"key": "story-06", "type": "story", "path": "stories/story-06-blackfriday.jpg"},
]

# ------------------------------------------------------------ API helpers
def _url(lang, rel):
    if not IMAGE_BASE_URL:
        sys.exit("Defina IMAGE_BASE_URL (base publica das imagens).")
    return f"{IMAGE_BASE_URL}/{lang}/{rel}"

def _check():
    if not ACCESS_TOKEN or not IG_USER_ID:
        sys.exit("Defina IG_ACCESS_TOKEN e IG_USER_ID (variaveis de ambiente).")

def _post(path, **params):
    params["access_token"] = ACCESS_TOKEN
    r = requests.post(f"{GRAPH}/{path}", data=params, timeout=60)
    data = r.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", data))
    return data

def _wait_ready(creation_id, tries=20, delay=3):
    """Espera o container ficar FINISHED antes de publicar (importante p/ carrossel)."""
    for _ in range(tries):
        r = requests.get(f"{GRAPH}/{creation_id}",
                         params={"fields": "status_code", "access_token": ACCESS_TOKEN}, timeout=30)
        st = r.json().get("status_code")
        if st == "FINISHED":
            return True
        if st == "ERROR":
            raise RuntimeError(f"Container {creation_id} deu ERROR no processamento.")
        time.sleep(delay)
    return False

def publish_single(lang, rel, caption):
    cont = _post(f"{IG_USER_ID}/media", image_url=_url(lang, rel), caption=caption or "")
    _wait_ready(cont["id"])
    res = _post(f"{IG_USER_ID}/media_publish", creation_id=cont["id"])
    return res.get("id")

def publish_story(lang, rel):
    cont = _post(f"{IG_USER_ID}/media", image_url=_url(lang, rel), media_type="STORIES")
    _wait_ready(cont["id"])
    res = _post(f"{IG_USER_ID}/media_publish", creation_id=cont["id"])
    return res.get("id")

def publish_carousel(lang, prefix, n, caption):
    children = []
    for i in range(1, n + 1):
        c = _post(f"{IG_USER_ID}/media", image_url=_url(lang, f"{prefix}-{i}.jpg"),
                  is_carousel_item="true")
        _wait_ready(c["id"])
        children.append(c["id"])
    cont = _post(f"{IG_USER_ID}/media", media_type="CAROUSEL",
                 children=",".join(children), caption=caption or "")
    _wait_ready(cont["id"])
    res = _post(f"{IG_USER_ID}/media_publish", creation_id=cont["id"])
    return res.get("id")

def publish_post(lang, post, dry=False):
    key = post["key"]
    cap = CAP.get(key, "")
    if dry:
        if post["type"] == "carousel":
            print(f"[dry] {key} CARROSSEL {post['n']} slides -> {_url(lang, post['prefix'] + '-1.jpg')} ...")
        else:
            print(f"[dry] {key} {post['type'].upper()} -> {_url(lang, post['path'])}")
        if cap:
            print("      legenda:", cap.split(chr(10))[0], "...")
        return None
    print(f"-> publicando {key} ({post['type']}) ...")
    if post["type"] == "single":
        mid = publish_single(lang, post["path"], cap)
    elif post["type"] == "story":
        mid = publish_story(lang, post["path"])
    elif post["type"] == "carousel":
        mid = publish_carousel(lang, post["prefix"], post["n"], cap)
    else:
        raise ValueError(post["type"])
    print(f"   OK media_id={mid}")
    return mid

# ------------------------------------------------------------ token helper
def exchange_token(short):
    if not APP_ID or not APP_SECRET:
        sys.exit("Defina IG_APP_ID e IG_APP_SECRET para trocar o token.")
    r = requests.get(f"{GRAPH}/oauth/access_token", params={
        "grant_type": "fb_exchange_token", "client_id": APP_ID,
        "client_secret": APP_SECRET, "fb_exchange_token": short}, timeout=30)
    data = r.json()
    if "error" in data:
        sys.exit("Erro: " + data["error"].get("message", str(data)))
    print("\nTOKEN DE LONGA DURACAO (valido ~60 dias):\n")
    print(data.get("access_token"))
    print("\nExpira em (s):", data.get("expires_in"))

# ------------------------------------------------------------ CLI
def main():
    ap = argparse.ArgumentParser(description="Publica posts no Instagram (Story R Us)")
    ap.add_argument("--lang", default="br", choices=["br", "en", "es"])
    ap.add_argument("--post", help="chave do post (ex.: feed-01, c3, story-02)")
    ap.add_argument("--all", action="store_true", help="publica todos em sequencia")
    ap.add_argument("--list", action="store_true", help="lista os posts disponiveis")
    ap.add_argument("--dry-run", action="store_true", help="simula sem publicar")
    ap.add_argument("--gap", type=int, default=90, help="pausa (s) entre posts no --all")
    ap.add_argument("--exchange-token", dest="exchange", help="troca token curto por 60 dias")
    a = ap.parse_args()

    if a.exchange:
        exchange_token(a.exchange)
        return
    if a.list:
        for p in POSTS:
            extra = f"{p['n']} slides" if p["type"] == "carousel" else p.get("path", "")
            print(f"  {p['key']:<10} {p['type']:<9} {extra}")
        return

    if not a.dry_run:
        _check()

    if a.all:
        for i, p in enumerate(POSTS):
            publish_post(a.lang, p, dry=a.dry_run)
            if not a.dry_run and i < len(POSTS) - 1:
                print(f"   ...aguardando {a.gap}s")
                time.sleep(a.gap)
        return

    if a.post:
        p = next((x for x in POSTS if x["key"] == a.post), None)
        if not p:
            sys.exit(f"Post '{a.post}' nao encontrado. Use --list.")
        publish_post(a.lang, p, dry=a.dry_run)
        return

    ap.print_help()

if __name__ == "__main__":
    main()
