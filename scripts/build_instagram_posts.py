"""
Gera o PACOTE COMPLETO de posts para Instagram da Story R Us (storyrus.ai)
em 3 IDIOMAS / 3 PERFIS, usando as imagens REAIS do site + a identidade da marca.

Perfis:
  @storyrus.br  -> Português (Brasil)  -> docs/social-assets/real/br/
  @storyr.us    -> English (US)        -> docs/social-assets/real/en/
  @storyrus.es  -> Español             -> docs/social-assets/real/es/

Cada pasta: feed/ (1:1), carrossel/ (1:1) e stories/ (9:16).

Rodar: python Storyrus/scripts/build_instagram_posts.py
Edite os textos (dicionário T), capas/cores e rode de novo para regerar tudo.
"""
from __future__ import annotations
import os
import math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ---------------------------------------------------------------- paths
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EX = os.path.join(ROOT, "apps", "web", "public", "exemplos")
LOGO = os.path.join(ROOT, "apps", "web", "src", "assets", "logo.png")
BASE = os.path.join(ROOT, "docs", "social-assets", "real")

LANGS = ["br", "en", "es"]
LANG = "br"
D_FEED = D_CARR = D_STORY = None

def set_lang(lang):
    global LANG, D_FEED, D_CARR, D_STORY
    LANG = lang
    D_FEED = os.path.join(BASE, lang, "feed")
    D_CARR = os.path.join(BASE, lang, "carrossel")
    D_STORY = os.path.join(BASE, lang, "stories")
    for d in (D_FEED, D_CARR, D_STORY):
        os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------- brand (storyrus.ai)
# Paleta oficial do site (landing.css :root)
INK       = (31, 53, 104)    # --ink    #1f3568
INK_DARK  = (16, 23, 46)     # superfície escura (base dos gradientes)
YELLOW    = (244, 183, 64)   # --yellow #f4b740
CREAMC    = (255, 247, 236)  # --cream  #fff7ec
SKY       = (127, 178, 227)  # --blue   #7fb2e3
PURPLE    = (58, 95, 174)    # --purple #3a5fae
CORALC    = (239, 143, 75)   # --coral  #ef8f4b  (cor promocional da marca)
MINT      = (63, 143, 125)   # --mint   #3f8f7d
GREY      = (74, 81, 112)    # texto secundário  #4a5170
WHITE     = (255, 255, 255)
SOFTW     = (233, 238, 251)  # texto sobre superfície escura  #e9eefb

# aliases: mantém os nomes usados no código, agora com a identidade do site
NAVY      = INK
NAVY_DARK = INK_DARK
GOLD      = YELLOW
CREAM     = CREAMC
BLUE      = PURPLE     # acento de texto legível sobre creme
RED       = CORALC     # urgência/promoção = coral da marca

# Fontes da marca: Baloo 2 (títulos/botões) + Quicksand (corpo) — mesmas do site
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")
BALOO = os.path.join(FONT_DIR, "Baloo2.ttf")
QUICK = os.path.join(FONT_DIR, "Quicksand.ttf")

def _vf(path, size, weight):
    f = ImageFont.truetype(path, size)
    try:
        f.set_variation_by_axes([weight])
    except Exception:
        pass
    return f

def f_black(s): return _vf(BALOO, s, 800)   # Baloo 2 ExtraBold (títulos)
def f_bold(s):  return _vf(BALOO, s, 700)   # Baloo 2 Bold (botões/labels)
def f_body(s):  return _vf(QUICK, s, 600)   # Quicksand (texto descritivo)

SITE = "storyrus.ai"

# >>> DATAS por idioma (edite e rode de novo) <<<
DATES = {
    "br": {"bf": "29/11", "xmas": "15/12"},
    "en": {"bf": "Nov 29", "xmas": "Dec 15"},
    "es": {"bf": "29/11", "xmas": "15/12"},
}
def D(kind): return DATES[LANG][kind]

# ================================================================ i18n
_LI = {"br": 0, "en": 1, "es": 2}
def t(k): return T[k][_LI[LANG]]

T = {
    # --- CTAs e botões ---
    "cta":        ("Crie a prévia grátis", "Create your free preview", "Crea tu vista previa gratis"),
    "get":        ("Garanta o seu", "Get yours", "Consigue el tuyo"),
    # --- FEED ---
    "hero":       ("Seu filho é o herói do próprio livro",
                   "Your child is the hero of their own book",
                   "Tu hijo es el héroe de su propio libro"),
    "prod_h":     ("Transforme uma foto em uma história inesquecível",
                   "Turn a photo into an unforgettable story",
                   "Convierte una foto en una historia inolvidable"),
    "prod_s":     ("onde seu filho é o protagonista.",
                   "where your child is the star.",
                   "donde tu hijo es el protagonista."),
    "natal_h":    ("O presente de Natal que a família guarda para sempre",
                   "The Christmas gift your family keeps forever",
                   "El regalo de Navidad que la familia guarda para siempre"),
    "natal_sub":  ("Peça até {d} e receba a tempo.",
                   "Order by {d} to get it in time.",
                   "Pide antes del {d} y recíbelo a tiempo."),
    "b_natal":    ("NATAL", "CHRISTMAS", "NAVIDAD"),
    "agg_h":      ("O aniversário dele vira uma história só dele",
                   "Their birthday becomes a story all their own",
                   "Su cumpleaños se convierte en una historia solo suya"),
    "agg_s":      ("Um presente que ninguém esquece.",
                   "A gift no one forgets.",
                   "Un regalo que nadie olvida."),
    "b_agg":      ("ANIVERSÁRIO", "BIRTHDAY", "CUMPLEAÑOS"),
    "avos_h":     ("O presente que emociona os avós",
                   "The gift that moves grandparents",
                   "El regalo que emociona a los abuelos"),
    "avos_s":     ("Netos e avós na mesma história.",
                   "Grandkids and grandparents in one story.",
                   "Nietos y abuelos en la misma historia."),
    "b_avos":     ("PARA OS AVÓS", "FOR GRANDPARENTS", "PARA LOS ABUELOS"),
    "pets_h":     ("Seu filho e o melhor amigo na mesma história",
                   "Your child and their best friend in one story",
                   "Tu hijo y su mejor amigo en la misma historia"),
    "pets_s":     ("O pet da família também vira personagem.",
                   "The family pet becomes a character too.",
                   "La mascota de la familia también es personaje."),
    "b_pets":     ("PETS", "PETS", "MASCOTAS"),
    "bebe_h":     ("O primeiro presente que ele guarda para sempre",
                   "The first gift they keep forever",
                   "El primer regalo que guarda para siempre"),
    "bebe_s":     ("Perfeito para recém-nascidos.",
                   "Perfect for newborns.",
                   "Perfecto para recién nacidos."),
    "b_bebe":     ("RECÉM-NASCIDO", "NEWBORN", "RECIÉN NACIDO"),
    "bf_sub":     ("Seu livro personalizado com condição especial",
                   "Your personalized book with a special deal",
                   "Tu libro personalizado con una oferta especial"),
    "only_until": ("só até {d}", "only until {d}", "solo hasta {d}"),
    "prova_q":    ("\u201cA reação dela ao se ver no livro não tem preço.\u201d",
                   "\u201cHer reaction to seeing herself in the book is priceless.\u201d",
                   "\u201cSu reacción al verse en el libro no tiene precio.\u201d"),
    "temas_title": ("Escolha o tema da história", "Choose the story theme", "Elige el tema de la historia"),
    # --- CARROSSEL 1 (como funciona) ---
    "cf_sub":     ("em 3 passos simples", "in 3 simple steps", "en 3 pasos simples"),
    "swipe":      ("Arraste  →", "Swipe  →", "Desliza  →"),
    "cf_final":   ("Pronto para criar a história do seu filho?",
                   "Ready to create your child's story?",
                   "¿Listo para crear la historia de tu hijo?"),
    "cf_title":   ("Como funciona", "How it works", "Cómo funciona"),
    # --- CARROSSEL 2 (temas) ---
    "temas_intro": ("Qual é a cara do seu filho?", "What's your child into?", "¿Cómo es tu hijo?"),
    "temas_swipe": ("Arraste e escolha o tema  →", "Swipe and pick the theme  →", "Desliza y elige el tema  →"),
    "temas_final": ("Tem um tema especial em mente?", "Have a special theme in mind?", "¿Tienes un tema especial en mente?"),
    "temas_final_s": ("A gente cria a história sob medida.", "We'll create a custom story.", "Creamos la historia a medida."),
    # --- CARROSSEL 3 (natal) ---
    "natal_intro": ("Presentes de Natal que emocionam", "Christmas gifts that touch hearts", "Regalos de Navidad que emocionan"),
    "natal_arrow": ("um para cada pessoa que você ama  →", "one for each person you love  →", "uno para cada persona que amas  →"),
    "natal_cta":   ("Garanta o presente antes do prazo de Natal",
                    "Get the gift before the Christmas deadline",
                    "Asegura el regalo antes de la fecha límite de Navidad"),
    "order_by":    ("Peça até {d}", "Order by {d}", "Pide antes del {d}"),
    # --- CARROSSEL 4 (antes e depois) ---
    "ad_intro":   ("Da foto real ao personagem do livro", "From a real photo to a book character", "De la foto real al personaje del libro"),
    "ad_arrow":   ("Veja a transformação  →", "See the transformation  →", "Mira la transformación  →"),
    "ad_banner":  ("DA FOTO AO LIVRO", "FROM PHOTO TO BOOK", "DE LA FOTO AL LIBRO"),
    "ad_photo":   ("A FOTO", "THE PHOTO", "LA FOTO"),
    "ad_char":    ("O PERSONAGEM", "THE CHARACTER", "EL PERSONAJE"),
    "ad_final":   ("Quer ver seu filho assim?", "Want to see your child like this?", "¿Quieres ver a tu hijo así?"),
    "ad_final_s": ("Envie uma foto e receba a prévia grátis.", "Send a photo and get your free preview.", "Envía una foto y recibe tu vista previa gratis."),
    # --- CARROSSEL 5 (faq) ---
    "faq_title":  ("Perguntas frequentes", "Frequently asked questions", "Preguntas frecuentes"),
    "faq_sub":    ("antes de criar o seu  →", "before creating yours  →", "antes de crear el tuyo  →"),
    "faq_final":  ("Ainda com dúvida?", "Still have questions?", "¿Aún tienes dudas?"),
    "faq_final_s": ("Crie a prévia grátis e veja na prática.", "Create your free preview and see for yourself.", "Crea tu vista previa gratis y compruébalo."),
    # --- STORIES ---
    "s1":         ("Uma foto. Uma história. Uma memória eterna.",
                   "One photo. One story. A memory forever.",
                   "Una foto. Una historia. Un recuerdo eterno."),
    "s2_l1":      ("Quer receber", "Want it", "¿Lo quieres"),
    "s2_l2":      ("no Natal?", "by Christmas?", "para Navidad?"),
    "cf_title2":  ("Como funciona", "How it works", "Cómo funciona"),
    "s4_l1":      ("Qual combina com", "Which one fits", "¿Cuál va con"),
    "s4_l2":      ("o seu filho?", "your child?", "tu hijo?"),
    "poll":       ("Toque e responda a enquete  →", "Tap and answer the poll  →", "Toca y responde la encuesta  →"),
    "s5_q":       ("\u201cMelhor presente que já demos. Virou relíquia da família.\u201d",
                   "\u201cBest gift we've ever given. It became a family treasure.\u201d",
                   "\u201cEl mejor regalo que hemos dado. Se volvió una reliquia familiar.\u201d"),
    "bf_story_s": ("Condição especial por tempo limitado", "Special deal for a limited time", "Oferta especial por tiempo limitado"),
    # enquete labels
    "q_super":    ("Super-herói", "Superhero", "Superhéroe"),
    "q_space":    ("Espaço", "Space", "Espacio"),
    "q_dino":     ("Dinossauros", "Dinosaurs", "Dinosaurios"),
    "q_pets":     ("Pets", "Pets", "Mascotas"),
}

# Listas localizadas (grids/carrosséis)
FEED_THEME_LABELS = {
    "br": ["Espaço", "Dinossauros", "Fundo do mar", "Super-heróis", "Pets", "Família"],
    "en": ["Space", "Dinosaurs", "Under the sea", "Superheroes", "Pets", "Family"],
    "es": ["Espacio", "Dinosaurios", "Fondo del mar", "Superhéroes", "Mascotas", "Familia"],
}
THEMES = {  # (label, desc) x5 para o carrossel de temas
    "br": [("ESPAÇO", "Foguetes, planetas e curiosidade."),
           ("DINOSSAUROS", "Uma expedição pré-histórica cheia de coragem."),
           ("FUNDO DO MAR", "Tartarugas, corais e muita descoberta."),
           ("SUPER-HERÓIS", "Capa ao vento e coragem no coração."),
           ("PETS", "Seu filho e o melhor amigo na mesma história.")],
    "en": [("SPACE", "Rockets, planets and curiosity."),
           ("DINOSAURS", "A prehistoric expedition full of courage."),
           ("UNDER THE SEA", "Turtles, corals and lots of discovery."),
           ("SUPERHEROES", "Cape in the wind and courage at heart."),
           ("PETS", "Your child and their best friend in one story.")],
    "es": [("ESPACIO", "Cohetes, planetas y curiosidad."),
           ("DINOSAURIOS", "Una expedición prehistórica llena de valentía."),
           ("FONDO DEL MAR", "Tortugas, corales y mucho descubrimiento."),
           ("SUPERHÉROES", "Capa al viento y valentía en el corazón."),
           ("MASCOTAS", "Tu hijo y su mejor amigo en la misma historia.")],
}
NATAL_PEOPLE = {  # (label, desc) x4
    "br": [("Para a mamãe", "O amor de mãe em cada página."),
           ("Para os avós", "O presente que faz o vovô se emocionar."),
           ("Para o papai", "Aventuras de pai e filho para sempre."),
           ("Para o bebê", "O primeiro presente, para guardar a vida toda.")],
    "en": [("For mom", "A mother's love on every page."),
           ("For grandparents", "The gift that brings grandpa to tears."),
           ("For dad", "Father-and-child adventures forever."),
           ("For the baby", "The first gift, to keep for life.")],
    "es": [("Para mamá", "El amor de mamá en cada página."),
           ("Para los abuelos", "El regalo que emociona al abuelo."),
           ("Para papá", "Aventuras de padre e hijo para siempre."),
           ("Para el bebé", "El primer regalo, para guardar toda la vida.")],
}
STEPS = {  # como funciona (title, desc) x3
    "br": [("Envie a foto", "Fotos nítidas de quem é o herói da história — rosto, cabelo e traços."),
           ("A gente cria", "Criamos o personagem e uma história única, com o rosto do seu filho."),
           ("Receba e aprove", "Você vê a prévia e aprova tudo antes de imprimir. Sem risco.")],
    "en": [("Send the photo", "Clear photos of your story's hero — face, hair and features."),
           ("We create it", "We craft the character and a unique story with your child's face."),
           ("Review & approve", "You see the preview and approve everything before printing. No risk.")],
    "es": [("Envía la foto", "Fotos nítidas del héroe de la historia — rostro, cabello y rasgos."),
           ("Nosotros lo creamos", "Creamos el personaje y una historia única con el rostro de tu hijo."),
           ("Recibe y aprueba", "Ves la vista previa y apruebas todo antes de imprimir. Sin riesgo.")],
}
STEPS_SHORT = {  # story como funciona
    "br": [("Envie a foto", "Fotos nítidas de quem é o herói da história."),
           ("A gente cria", "O personagem e a história, com o rosto do seu filho."),
           ("Receba e aprove", "Veja a prévia e aprove antes de imprimir.")],
    "en": [("Send the photo", "Clear photos of your story's hero."),
           ("We create it", "The character and story, with your child's face."),
           ("Review & approve", "See the preview and approve before printing.")],
    "es": [("Envía la foto", "Fotos nítidas del héroe de la historia."),
           ("Nosotros lo creamos", "El personaje y la historia, con el rostro de tu hijo."),
           ("Recibe y aprueba", "Mira la vista previa y aprueba antes de imprimir.")],
}
FAQ = {
    "br": [("Preciso saber desenhar ou usar algum programa?",
            "Não! Você só envia uma foto. A gente cria o personagem e toda a história para você."),
           ("Posso ver antes de imprimir?",
            "Sim. Você recebe a prévia e aprova tudo antes. Sem risco e sem surpresa."),
           ("Quanto tempo leva?",
            "A prévia digital sai na hora. O eBook é imediato e o livro impresso é enviado até você."),
           ("Quais formatos existem?",
            "eBook em PDF (na hora), livro impresso, vídeo narrado e até animação.")],
    "en": [("Do I need to draw or use any software?",
            "No! You just send a photo. We create the character and the whole story for you."),
           ("Can I see it before printing?",
            "Yes. You get the preview and approve everything first. No risk, no surprises."),
           ("How long does it take?",
            "The digital preview is instant. The eBook is immediate and the printed book ships to you."),
           ("What formats are available?",
            "PDF eBook (instant), printed book, narrated video and even animation.")],
    "es": [("¿Necesito saber dibujar o usar algún programa?",
            "¡No! Solo envías una foto. Nosotros creamos el personaje y toda la historia por ti."),
           ("¿Puedo verlo antes de imprimir?",
            "Sí. Recibes la vista previa y apruebas todo antes. Sin riesgo ni sorpresas."),
           ("¿Cuánto tarda?",
            "La vista previa digital es al instante. El eBook es inmediato y el libro impreso se envía a tu casa."),
           ("¿Qué formatos existen?",
            "eBook en PDF (al instante), libro impreso, video narrado e incluso animación.")],
}
AD_NAMES = {  # antes e depois (nome por par)
    "br": ["A Sofia virou a heroína da própria história",
           "O Matteo virou personagem do seu livro",
           "O Davi virou o herói da aventura dele"],
    "en": ["Sofia became the hero of her own story",
           "Matteo became a character in his own book",
           "Davi became the hero of his adventure"],
    "es": ["Sofía se volvió la heroína de su propia historia",
           "Matteo se volvió personaje de su propio libro",
           "David se volvió el héroe de su aventura"],
}
# Fotos de estilo de vida por idioma (livro na foto no idioma certo)
PHOTOS = {
    "br": {"hero": "foto-meupai-heroi.png", "prova": "foto-raquel-papai.png"},
    "en": {"hero": "foto-amordemae-en.jpg", "prova": "foto-mako-amigofiel-en.jpg"},
    "es": {"hero": "foto-amordemae-es.jpg", "prova": "foto-mako-amigofiel-es.jpg"},
}

def hero_cover():
    """Capa 'carro-chefe' com texto no idioma certo (BR usa a capa-herói original)."""
    return "capa-meupai-heroi.png" if LANG == "br" else loc("capa-nanoaventuras.png")

def loc(name):
    """Escolhe a variante localizada da imagem (-en/-es) se existir; senão usa a base."""
    if LANG == "br":
        return name
    stem, ext = os.path.splitext(name)
    for e in (ext, ".png", ".jpg"):
        cand = f"{stem}-{LANG}{e}"
        if os.path.exists(os.path.join(EX, cand)):
            return cand
    return name

# ---------------------------------------------------------------- helpers
def load(p): return Image.open(p).convert("RGBA")

def cover_fit(img, w, h):
    iw, ih = img.size
    s = max(w / iw, h / ih)
    nw, nh = int(iw * s) + 1, int(ih * s) + 1
    img = img.resize((nw, nh), Image.LANCZOS)
    l, tt = (nw - w) // 2, (nh - h) // 2
    return img.crop((l, tt, l + w, tt + h))

def rounded(img, rad):
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, *img.size], rad, fill=255)
    o = img.copy(); o.putalpha(m); return o

def shadow_for(img, blur=25, alpha=130, grow=20):
    w, h = img.size
    base = Image.new("RGBA", (w + grow * 2, h + grow * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", img.size, (0, 0, 0, alpha))
    sh.putalpha(img.split()[-1].point(lambda a: min(a, alpha)))
    base.paste(sh, (grow, grow), img)
    return base.filter(ImageFilter.GaussianBlur(blur))

def _lerp(a, b, tt): return tuple(int(a[i] + (b[i] - a[i]) * tt) for i in range(3))

def _vgrad(w, h, top, bot):
    col = Image.new("RGB", (1, h)); px = col.load()
    for y in range(h):
        px[0, y] = _lerp(top, bot, y / max(h - 1, 1))
    return col.resize((w, h)).convert("RGBA")

def bg_light(w, h):
    g = _vgrad(w, h, (243, 248, 255), (255, 242, 219))
    glow = _vgrad(w, int(h * 0.55), (220, 236, 251), (220, 236, 251))
    gm = Image.new("L", (w, int(h * 0.55)))
    for y in range(int(h * 0.55)):
        gm.paste(int(90 * (1 - y / (h * 0.55))), (0, y, w, y + 1))
    glow.putalpha(gm)
    g.alpha_composite(glow, (0, 0))
    return g

def bg_dark(w, h):
    return _vgrad(w, h, (26, 38, 72), (16, 23, 46))

def grad_v(w, h, top_a, bot_a, color=(0, 0, 0)):
    g = Image.new("L", (1, h))
    for y in range(h):
        tt = y / max(h - 1, 1)
        g.putpixel((0, y), int(top_a + (bot_a - top_a) * tt))
    g = g.resize((w, h))
    o = Image.new("RGBA", (w, h), color + (0,)); o.putalpha(g); return o

def wrap(d, text, fnt, max_w):
    out, cur = [], ""
    for wd in text.split():
        tx = (cur + " " + wd).strip()
        if d.textlength(tx, font=fnt) <= max_w:
            cur = tx
        else:
            if cur: out.append(cur)
            cur = wd
    if cur: out.append(cur)
    return out

def draw_text(d, xy, lines, fnt, fill, line_sp=1.12, center_w=None,
              anchor="la", shadow=None):
    x, y = xy
    asc, desc = fnt.getmetrics(); lh = int((asc + desc) * line_sp)
    for ln in lines:
        tw = d.textlength(ln, font=fnt)
        if center_w is not None: px = x + (center_w - tw) / 2
        elif anchor == "ma": px = x - tw / 2
        else: px = x
        if shadow:
            sx, sy, sc = shadow
            d.text((px + sx, y + sy), ln, font=fnt, fill=sc)
        d.text((px, y), ln, font=fnt, fill=fill)
        y += lh
    return y

def center(d, text, fnt, fill, w, y, shadow=None):
    tw = d.textlength(text, font=fnt)
    if shadow:
        sx, sy, sc = shadow
        d.text(((w - tw) / 2 + sx, y + sy), text, font=fnt, fill=sc)
    d.text(((w - tw) / 2, y), text, font=fnt, fill=fill)

def pill(d, box, fill, text, fnt, text_fill):
    x0, y0, x1, y1 = box
    d.rounded_rectangle(box, (y1 - y0) // 2, fill=fill)
    tw = d.textlength(text, font=fnt); asc, desc = fnt.getmetrics()
    d.text((x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - (asc + desc)) / 2),
           text, font=fnt, fill=text_fill)

def logo_chip(c, cx, bottom_y, logo_h=86, pad=20, bg=WHITE):
    lg = load(LOGO); r = logo_h / lg.height
    lg = lg.resize((int(lg.width * r), int(lg.height * r)), Image.LANCZOS)
    cw, ch = lg.width + pad * 2, lg.height + pad * 2
    chip = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    ImageDraw.Draw(chip).rounded_rectangle([0, 0, cw, ch], 30, fill=bg + (238,))
    chip.paste(lg, (pad, pad), lg)
    x, y = int(cx - cw / 2), int(bottom_y - ch)
    c.alpha_composite(shadow_for(chip, blur=16, alpha=60), (x - 18, y - 18))
    c.alpha_composite(chip, (x, y))

def place_cover(c, cover, box, rad=26, shadow=True):
    x0, y0, x1, y1 = box
    cv = rounded(cover_fit(load(cover), x1 - x0, y1 - y0), rad)
    if shadow:
        c.alpha_composite(shadow_for(cv, blur=28, alpha=115, grow=24), (x0 - 24, y0 - 24))
    c.alpha_composite(cv, (x0, y0))

def _hbind(w, h, max_a=78):
    """Faixa de encadernação: gradiente escuro da esquerda -> transparente."""
    g = Image.new("RGBA", (w, h), (9, 15, 32, 0)); px = g.load()
    for x in range(w):
        a = int(max_a * (1 - x / max(w - 1, 1)) ** 1.4)
        for y in range(h):
            px[x, y] = (9, 15, 32, a)
    return g

def place_book(c, cover, box, shadow=True):
    """Capa como LIVRO 3D no padrão do site (.kbh-frame)."""
    x0, y0, x1, y1 = [int(v) for v in box]
    w, h = x1 - x0, y1 - y0
    rad = max(10, int(h * 0.035))
    spine = max(6, int(w * 0.02))
    img = rounded(cover_fit(load(cover), w, h), rad)
    if shadow:
        sh = shadow_for(img, blur=36, alpha=95, grow=34)
        tint = Image.new("RGBA", sh.size, (31, 53, 104, 0)); tint.putalpha(sh.split()[-1])
        c.alpha_composite(tint, (x0 - 34, y0 - 34 + int(h * 0.045)))
    sp = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(sp).rounded_rectangle([0, 0, w, h], rad, fill=(26, 39, 72, 255))
    c.alpha_composite(sp, (x0 + spine, y0))
    bw = max(8, int(w * 0.04))
    cover_img = img.copy()
    cover_img.alpha_composite(_hbind(bw, h), (0, 0))
    cover_img.putalpha(img.split()[-1])
    c.alpha_composite(cover_img, (x0, y0))

def _star_pts(cx, cy, r_out, r_in):
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(ang), cy + r * math.sin(ang)))
    return pts

def draw_stars(d, cx, cy, n=5, r=26, gap=14, fill=GOLD):
    step = 2 * r + gap
    start = cx - (n * step - gap) / 2 + r
    for i in range(n):
        d.polygon(_star_pts(start + i * step, cy, r, r * 0.45), fill=fill + (255,))

def cap(name): return os.path.join(EX, name)

def save(c, folder, name):
    c.convert("RGB").save(os.path.join(folder, name), "JPEG", quality=92)
    print("ok ->", os.path.relpath(os.path.join(folder, name), BASE))

# ================================================================ FEED
def feed_photo_hero(photo, headline, fname):
    W = H = 1080
    c = Image.new("RGBA", (W, H)); c.alpha_composite(cover_fit(load(photo), W, H))
    c.alpha_composite(grad_v(W, 430, 205, 0))
    c.alpha_composite(grad_v(W, 520, 0, 210), (0, H - 520))
    d = ImageDraw.Draw(c)
    draw_text(d, (75, 70), wrap(d, headline, f_black(74), W - 150), f_black(74),
              WHITE, center_w=W - 150, shadow=(0, 3, (0, 0, 0, 160)))
    pill(d, (210, H - 250, W - 210, H - 170), GOLD, t("cta"), f_bold(42), NAVY)
    center(d, SITE, f_bold(36), WHITE, W, H - 120, shadow=(0, 1, (0, 0, 0, 120)))
    save(c, D_FEED, fname)

def feed_cover_post(cover, headline, subtitle, fname, accent=BLUE,
                    badge=None, badge_color=RED, cta=None):
    cta = cta or t("cta")
    W = H = 1080
    c = bg_light(W, H); d = ImageDraw.Draw(c)
    for sx, sy, r in [(92, 150, 9), (120, 905, 7)]:
        d.ellipse([sx - r, sy - r, sx + r, sy + r], fill=GOLD + (255,))
    col = 440
    y = 150
    if badge:
        bw = d.textlength(badge, font=f_bold(30)) + 60
        pill(d, (70, y, 70 + bw, y + 60), badge_color, badge, f_bold(30), WHITE)
        y += 95
    y = draw_text(d, (70, y), wrap(d, headline, f_black(50), col), f_black(50),
                  NAVY, line_sp=1.04)
    draw_text(d, (70, y + 18), wrap(d, subtitle, f_body(32), col), f_body(32), accent)
    place_book(c, cover, (560, 150, 1020, 610))
    pill(d, (70, 770, 650, 850), GOLD, cta, f_bold(40), NAVY)
    d.text((72, 886), SITE, font=f_bold(34), fill=NAVY)
    save(c, D_FEED, fname)

def feed_temas():
    W = H = 1080
    c = bg_dark(W, H); d = ImageDraw.Draw(c)
    center(d, t("temas_title"), f_black(58), WHITE, W, 60)
    covers = ["capa-abigail.png", "capa-noe.png", "capa-miriam.png",
              "capa-rebeca.png", "capa-lucas-max.png", "capa-nossa-familia.png"]
    labels = FEED_THEME_LABELS[LANG]
    cols, pad, top = 3, 50, 190
    cw = (W - pad * (cols + 1)) // cols
    for i, (cv, lab) in enumerate(zip(covers, labels)):
        r, col = divmod(i, cols)
        x0 = pad + col * (cw + pad); y0 = top + r * (cw + 90)
        place_cover(c, cap(loc(cv)), (x0, y0, x0 + cw, y0 + cw), rad=20)
        lw = d.textlength(lab, font=f_bold(32))
        d.text((x0 + (cw - lw) / 2, y0 + cw + 14), lab, font=f_bold(32), fill=GOLD)
    center(d, t("cta") + " • " + SITE, f_bold(34), WHITE, W, H - 70)
    save(c, D_FEED, "feed-03-temas.jpg")

def feed_blackfriday():
    W = H = 1080
    c = bg_dark(W, H); d = ImageDraw.Draw(c)
    center(d, "BLACK FRIDAY", f_black(96), GOLD, W, 70)
    center(d, t("bf_sub"), f_bold(34), WHITE, W, 185)
    place_book(c, cap(loc("capa-rebeca.png")), (330, 270, 750, 690))
    pill(d, (270, 760, 810, 844), GOLD, t("get"), f_bold(44), NAVY)
    center(d, SITE + "  •  " + t("only_until").format(d=D("bf")), f_bold(34), WHITE, W, 910)
    save(c, D_FEED, "feed-05-blackfriday.jpg")

def feed_prova(photo):
    W = H = 1080
    c = Image.new("RGBA", (W, H)); c.alpha_composite(cover_fit(load(photo), W, H))
    c.alpha_composite(grad_v(W, 560, 0, 220), (0, H - 560))
    d = ImageDraw.Draw(c)
    draw_stars(d, W / 2, H - 410, 5, r=24)
    draw_text(d, (80, H - 360), wrap(d, t("prova_q"), f_black(50), W - 160), f_black(50),
              WHITE, center_w=W - 160, shadow=(0, 2, (0, 0, 0, 160)))
    pill(d, (210, H - 180, W - 210, H - 100), GOLD, t("cta"), f_bold(40), NAVY)
    save(c, D_FEED, "feed-10-prova.jpg")

# ================================================================ CARROSSEIS
def carr_slide_base(bg=CREAM):
    if bg == CREAM: return bg_light(1080, 1080)
    if bg in (NAVY, NAVY_DARK): return bg_dark(1080, 1080)
    return Image.new("RGBA", (1080, 1080), bg + (255,))

def carousel_como_funciona():
    pre = "c1-comofunciona"
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    center(d, t("cf_title"), f_black(76), WHITE, 1080, 120)
    center(d, t("cf_sub"), f_bold(40), GOLD, 1080, 230)
    place_book(c, cap(hero_cover()), (310, 340, 770, 800))
    center(d, t("swipe"), f_bold(34), WHITE, 1080, 900)
    save(c, D_CARR, f"{pre}-1.jpg")
    imgs = [PHOTOS[LANG]["prova"], loc("capa-abigail.png"), PHOTOS[LANG]["hero"]]
    for i, ((title, desc), img) in enumerate(zip(STEPS[LANG], imgs), start=2):
        num = str(i - 1)
        c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
        place_cover(c, cap(img), (0, 0, 1080, 560), rad=0, shadow=False)
        c.alpha_composite(grad_v(1080, 200, 0, 120), (0, 360))
        d = ImageDraw.Draw(c)
        d.ellipse([70, 620, 210, 760], fill=NAVY + (255,))
        nw = d.textlength(num, font=f_black(84))
        d.text((140 - nw / 2, 640), num, font=f_black(84), fill=GOLD)
        d.text((250, 640), title, font=f_black(64), fill=NAVY)
        draw_text(d, (70, 800), wrap(d, desc, f_body(40), 940), f_body(40), GREY)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (90, 300), wrap(d, t("cf_final"), f_black(66), 900),
              f_black(66), WHITE, center_w=900)
    pill(d, (190, 640, 890, 730), GOLD, t("cta"), f_bold(46), NAVY)
    center(d, SITE, f_bold(40), GOLD, 1080, 780)
    logo_chip(c, 540, 1010, logo_h=90)
    save(c, D_CARR, f"{pre}-5.jpg")

def carousel_temas():
    pre = "c2-temas"
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (80, 380), wrap(d, t("temas_intro"), f_black(78), 920),
              f_black(78), WHITE, center_w=920)
    center(d, t("temas_swipe"), f_bold(38), GOLD, 1080, 640)
    save(c, D_CARR, f"{pre}-1.jpg")
    covers = ["capa-abigail.png", "capa-noe.png", "capa-miriam.png",
              "capa-rebeca.png", "capa-lucas-max.png"]
    for i, (img, (lab, desc)) in enumerate(zip(covers, THEMES[LANG]), start=2):
        c = Image.new("RGBA", (1080, 1080))
        c.alpha_composite(cover_fit(load(cap(loc(img))), 1080, 1080))
        c.alpha_composite(grad_v(1080, 480, 0, 225), (0, 600))
        d = ImageDraw.Draw(c)
        d.text((70, 820), lab, font=f_black(70), fill=GOLD)
        draw_text(d, (70, 910), wrap(d, desc, f_body(38), 940), f_body(38), WHITE)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
    draw_text(d, (90, 330), wrap(d, t("temas_final"), f_black(64), 900),
              f_black(64), NAVY, center_w=900)
    center(d, t("temas_final_s"), f_bold(38), BLUE, 1080, 520)
    pill(d, (190, 640, 890, 730), GOLD, t("cta"), f_bold(46), NAVY)
    center(d, SITE, f_bold(40), NAVY, 1080, 780)
    logo_chip(c, 540, 1020, logo_h=90)
    save(c, D_CARR, f"{pre}-7.jpg")

def carousel_natal():
    pre = "c3-natal"
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 1080, 24], fill=RED + (255,))
    d.rectangle([0, 1056, 1080, 1080], fill=RED + (255,))
    draw_text(d, (80, 340), wrap(d, t("natal_intro"), f_black(74), 920),
              f_black(74), WHITE, center_w=920)
    center(d, t("natal_arrow"), f_bold(36), GOLD, 1080, 640)
    save(c, D_CARR, f"{pre}-1.jpg")
    covers = ["capa-amordemae.png", "capa-amor-de-avo.png",
              "capa-raquel-papai.png", "capa-nicolas-maefilho.png"]
    for i, (img, (lab, desc)) in enumerate(zip(covers, NATAL_PEOPLE[LANG]), start=2):
        c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
        place_book(c, cap(loc(img)), (175, 70, 905, 800))
        d = ImageDraw.Draw(c)
        d.text((90, 835), lab, font=f_black(60), fill=NAVY)
        draw_text(d, (90, 915), wrap(d, desc, f_body(38), 900), f_body(38), GREY)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 1080, 24], fill=RED + (255,))
    d.rectangle([0, 1056, 1080, 1080], fill=RED + (255,))
    draw_text(d, (90, 300), wrap(d, t("natal_cta"), f_black(64), 900),
              f_black(64), WHITE, center_w=900)
    pill(d, (230, 600, 850, 680), RED, t("order_by").format(d=D("xmas")), f_bold(42), WHITE)
    pill(d, (190, 720, 890, 810), GOLD, t("cta"), f_bold(46), NAVY)
    center(d, SITE, f_bold(38), GOLD, 1080, 860)
    save(c, D_CARR, f"{pre}-6.jpg")

def carousel_antes_depois():
    pre = "c4-antesdepois"
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (90, 320), wrap(d, t("ad_intro"), f_black(74), 900),
              f_black(74), WHITE, center_w=900)
    center(d, t("ad_arrow"), f_bold(38), GOLD, 1080, 640)
    save(c, D_CARR, f"{pre}-1.jpg")
    pairs = [("foto-sofia.png", "capa-sofia-alfabeto.png"),
             ("foto-matteo.png", "cartoon-capa-matteo.jpg"),
             ("cartoon-foto-davi.jpg", "cartoon-capa-davi.png")]
    panel, top = 430, 250
    lx, rx = 65, 1080 - 65 - 430
    cxm, cym = 540, top + panel / 2
    for i, ((real, char), nm) in enumerate(zip(pairs, AD_NAMES[LANG]), start=2):
        c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
        center(d, t("ad_banner"), f_black(50), WHITE, 1080, 80)
        place_cover(c, cap(real), (lx, top, lx + panel, top + panel), rad=24)
        place_cover(c, cap(char), (rx, top, rx + panel, top + panel), rad=24)
        d = ImageDraw.Draw(c)
        draw_text(d, (lx + panel / 2, top + panel + 18), [t("ad_photo")], f_bold(34), WHITE, anchor="ma")
        draw_text(d, (rx + panel / 2, top + panel + 18), [t("ad_char")], f_bold(34), GOLD, anchor="ma")
        d.ellipse([cxm - 56, cym - 56, cxm + 56, cym + 56], fill=GOLD + (255,))
        d.polygon([(cxm - 20, cym - 28), (cxm - 20, cym + 28), (cxm + 30, cym)], fill=NAVY + (255,))
        draw_text(d, (90, top + panel + 110), wrap(d, nm, f_black(50), 900),
                  f_black(50), WHITE, center_w=900)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
    draw_text(d, (90, 300), wrap(d, t("ad_final"), f_black(70), 900),
              f_black(70), NAVY, center_w=900)
    center(d, t("ad_final_s"), f_bold(36), BLUE, 1080, 480)
    pill(d, (190, 620, 890, 710), GOLD, t("cta"), f_bold(46), NAVY)
    center(d, SITE, f_bold(40), NAVY, 1080, 760)
    logo_chip(c, 540, 1020, logo_h=90)
    save(c, D_CARR, f"{pre}-5.jpg")

def carousel_faq():
    pre = "c5-faq"
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (90, 360), wrap(d, t("faq_title"), f_black(84), 920),
              f_black(84), WHITE, center_w=920)
    center(d, t("faq_sub"), f_bold(38), GOLD, 1080, 560)
    save(c, D_CARR, f"{pre}-1.jpg")
    for i, (q, a) in enumerate(FAQ[LANG], start=2):
        c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
        d.text((70, 80), str(i - 1), font=f_black(130), fill=GOLD + (255,))
        y = draw_text(d, (70, 270), wrap(d, q, f_black(56), 940), f_black(56), NAVY, line_sp=1.05)
        draw_text(d, (70, y + 30), wrap(d, a, f_body(42), 940), f_body(42), GREY, line_sp=1.2)
        d.text((72, 985), SITE, font=f_bold(34), fill=NAVY)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (90, 320), wrap(d, t("faq_final"), f_black(72), 900),
              f_black(72), WHITE, center_w=900)
    center(d, t("faq_final_s"), f_bold(38), GOLD, 1080, 500)
    pill(d, (190, 640, 890, 730), GOLD, t("cta"), f_bold(46), NAVY)
    center(d, SITE, f_bold(40), GOLD, 1080, 780)
    logo_chip(c, 540, 1020, logo_h=90)
    save(c, D_CARR, f"{pre}-6.jpg")

# ================================================================ STORIES
def story_photo_cta(photo):
    W, H = 1080, 1920
    c = Image.new("RGBA", (W, H)); c.alpha_composite(cover_fit(load(photo), W, H))
    c.alpha_composite(grad_v(W, 650, 210, 0)); c.alpha_composite(grad_v(W, 780, 0, 225), (0, H - 780))
    d = ImageDraw.Draw(c)
    draw_text(d, (75, 150), wrap(d, t("s1"), f_black(82), W - 150),
              f_black(82), WHITE, center_w=W - 150, line_sp=1.1, shadow=(0, 3, (0, 0, 0, 170)))
    pill(d, (150, H - 420, W - 150, H - 320), GOLD, t("cta"), f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 120, logo_h=86)
    save(c, D_STORY, "story-01-cta.jpg")

def story_prazo():
    W, H = 1080, 1920
    c = bg_dark(W, H); d = ImageDraw.Draw(c)
    d.text((70, 120), t("s2_l1"), font=f_black(100), fill=WHITE)
    d.text((70, 240), t("s2_l2"), font=f_black(100), fill=GOLD)
    pill(d, (70, 420, 760, 520), RED, t("order_by").format(d=D("xmas")), f_bold(54), WHITE)
    place_book(c, cap(loc("capa-nicolas-maefilho.png")), (260, 620, 820, 1240))
    pill(d, (150, 1370, W - 150, 1470), GOLD, t("cta"), f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 110, logo_h=86)
    save(c, D_STORY, "story-02-prazo.jpg")

def story_comofunciona():
    W, H = 1080, 1920
    c = bg_light(W, H); d = ImageDraw.Draw(c)
    center(d, t("cf_title2"), f_black(84), NAVY, W, 110)
    y = 330
    for idx, (title, desc) in enumerate(STEPS_SHORT[LANG], start=1):
        d.ellipse([80, y, 200, y + 120], fill=NAVY + (255,))
        num = str(idx)
        nw = d.textlength(num, font=f_black(70)); d.text((140 - nw / 2, y + 18), num, font=f_black(70), fill=GOLD)
        d.text((250, y + 6), title, font=f_black(56), fill=NAVY)
        draw_text(d, (250, y + 78), wrap(d, desc, f_body(36), W - 310), f_body(36), GREY)
        y += 330
    pill(d, (150, H - 420, W - 150, H - 320), GOLD, t("cta"), f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 120, logo_h=86)
    save(c, D_STORY, "story-03-comofunciona.jpg")

def story_enquete():
    W, H = 1080, 1920
    c = bg_dark(W, H); d = ImageDraw.Draw(c)
    center(d, t("s4_l1"), f_black(72), WHITE, W, 150)
    center(d, t("s4_l2"), f_black(72), GOLD, W, 250)
    place_cover(c, cap(loc("capa-rebeca.png")), (90, 470, 520, 900), rad=24)
    place_cover(c, cap(loc("capa-abigail.png")), (560, 470, 990, 900), rad=24)
    center(d, t("q_super"), f_bold(40), WHITE, 305, 930)
    center(d, t("q_space"), f_bold(40), WHITE, 775, 930)
    place_cover(c, cap(loc("capa-noe.png")), (90, 1040, 520, 1470), rad=24)
    place_cover(c, cap(loc("capa-lucas-max.png")), (560, 1040, 990, 1470), rad=24)
    center(d, t("q_dino"), f_bold(40), WHITE, 305, 1500)
    center(d, t("q_pets"), f_bold(40), WHITE, 775, 1500)
    center(d, t("poll"), f_bold(40), GOLD, W, 1600)
    logo_chip(c, W / 2, H - 100, logo_h=80)
    save(c, D_STORY, "story-04-enquete.jpg")

def story_prova(photo):
    W, H = 1080, 1920
    c = Image.new("RGBA", (W, H)); c.alpha_composite(cover_fit(load(photo), W, H))
    c.alpha_composite(grad_v(W, 700, 150, 0)); c.alpha_composite(grad_v(W, 760, 0, 225), (0, H - 760))
    d = ImageDraw.Draw(c)
    draw_stars(d, W / 2, 200, 5, r=32)
    draw_text(d, (80, 300), wrap(d, t("s5_q"), f_black(64), W - 160),
              f_black(64), WHITE, center_w=W - 160, shadow=(0, 2, (0, 0, 0, 170)))
    pill(d, (150, H - 430, W - 150, H - 330), GOLD, t("cta"), f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 120, logo_h=86)
    save(c, D_STORY, "story-05-prova.jpg")

def story_blackfriday():
    W, H = 1080, 1920
    c = bg_dark(W, H); d = ImageDraw.Draw(c)
    center(d, "BLACK", f_black(140), GOLD, W, 160)
    center(d, "FRIDAY", f_black(140), GOLD, W, 320)
    center(d, t("bf_story_s"), f_bold(40), WHITE, W, 540)
    place_book(c, cap(loc("capa-rebeca.png")), (290, 660, 790, 1160))
    pill(d, (230, 1260, 850, 1360), RED, t("only_until").format(d=D("bf")).capitalize(), f_bold(48), WHITE)
    pill(d, (150, 1420, W - 150, 1520), GOLD, t("get"), f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 110, logo_h=86)
    save(c, D_STORY, "story-06-blackfriday.jpg")

# ================================================================ RUN
def build_lang(lang):
    set_lang(lang)
    ph = PHOTOS[lang]
    print(f"\n######## {lang.upper()} ########")
    print("== FEED ==")
    feed_photo_hero(cap(ph["hero"]), t("hero"), "feed-01-hero.jpg")
    feed_cover_post(cap(hero_cover()), t("prod_h"), t("prod_s"), "feed-02-produto.jpg")
    feed_temas()
    feed_cover_post(cap(loc("capa-nicolas-maefilho.png")), t("natal_h"),
                    t("natal_sub").format(d=D("xmas")), "feed-04-natal.jpg",
                    accent=RED, badge=t("b_natal"), badge_color=RED)
    feed_blackfriday()
    feed_cover_post(cap(loc("capa-ester.png")), t("agg_h"), t("agg_s"),
                    "feed-06-aniversario.jpg", badge=t("b_agg"), badge_color=BLUE)
    feed_cover_post(cap(loc("capa-amor-de-avo.png")), t("avos_h"), t("avos_s"),
                    "feed-07-avos.jpg", badge=t("b_avos"), badge_color=NAVY)
    feed_cover_post(cap(loc("capa-lucas-max.png")), t("pets_h"), t("pets_s"),
                    "feed-08-pets.jpg", badge=t("b_pets"), badge_color=NAVY)
    feed_cover_post(cap(loc("capa-nicolas-maefilho.png")), t("bebe_h"), t("bebe_s"),
                    "feed-09-bebe.jpg", badge=t("b_bebe"), badge_color=BLUE)
    feed_prova(cap(ph["prova"]))
    print("== CARROSSEIS ==")
    carousel_como_funciona()
    carousel_temas()
    carousel_natal()
    carousel_antes_depois()
    carousel_faq()
    print("== STORIES ==")
    story_photo_cta(cap(ph["hero"]))
    story_prazo()
    story_comofunciona()
    story_enquete()
    story_prova(cap(ph["prova"]))
    story_blackfriday()

if __name__ == "__main__":
    for lang in LANGS:
        build_lang(lang)
    print("\nTudo salvo em:", BASE, "->", ", ".join(LANGS))
