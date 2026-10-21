"""
Gera o PACOTE COMPLETO de posts para Instagram da Story R Us (storyrus.ai)
usando as imagens REAIS do site (capas e fotos oficiais) + texto e logo.

Saida:
  docs/social-assets/real/feed/       -> posts de feed (1:1)
  docs/social-assets/real/carrossel/  -> carrosseis (varios slides 1:1)
  docs/social-assets/real/stories/    -> stories (9:16)

Rodar: python Storyrus/scripts/build_instagram_posts.py
Edite os textos/capas/cores aqui e rode de novo para regerar tudo.
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
D_FEED = os.path.join(BASE, "feed")
D_CARR = os.path.join(BASE, "carrossel")
D_STORY = os.path.join(BASE, "stories")
for d in (D_FEED, D_CARR, D_STORY):
    os.makedirs(d, exist_ok=True)

# ---------------------------------------------------------------- brand
NAVY = (18, 44, 102)
NAVY_DARK = (10, 20, 45)
GOLD = (246, 180, 0)
CREAM = (251, 244, 228)
BLUE = (70, 165, 232)
RED = (196, 53, 43)
GREY = (70, 80, 110)
WHITE = (255, 255, 255)

FONTS = r"C:\Windows\Fonts"
def _f(name, size): return ImageFont.truetype(os.path.join(FONTS, name), size)
def f_black(s): return _f("seguibl.ttf", s)   # Segoe UI Black
def f_bold(s):  return _f("segoeuib.ttf", s)  # Segoe UI Semibold/Bold

SITE = "storyrus.ai"
CTA = "Crie a prévia grátis"
CTA_SITE = "Crie a prévia grátis • storyrus.ai"

# >>> DATAS (edite aqui e rode de novo para atualizar todas as artes) <<<
DATE_BF = "29/11"      # último dia da Black Friday
DATE_XMAS = "15/12"    # prazo para pedir e receber o livro impresso até o Natal

# ---------------------------------------------------------------- helpers
def load(p): return Image.open(p).convert("RGBA")

def cover_fit(img, w, h):
    iw, ih = img.size
    s = max(w / iw, h / ih)
    nw, nh = int(iw * s) + 1, int(ih * s) + 1
    img = img.resize((nw, nh), Image.LANCZOS)
    l, t = (nw - w) // 2, (nh - h) // 2
    return img.crop((l, t, l + w, t + h))

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

def grad_v(w, h, top_a, bot_a, color=(0, 0, 0)):
    g = Image.new("L", (1, h))
    for y in range(h):
        t = y / max(h - 1, 1)
        g.putpixel((0, y), int(top_a + (bot_a - top_a) * t))
    g = g.resize((w, h))
    o = Image.new("RGBA", (w, h), color + (0,)); o.putalpha(g); return o

def wrap(d, text, fnt, max_w):
    out, cur = [], ""
    for wd in text.split():
        t = (cur + " " + wd).strip()
        if d.textlength(t, font=fnt) <= max_w:
            cur = t
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
    """Post 1:1 com foto de estilo de vida em tela cheia."""
    W = H = 1080
    c = Image.new("RGBA", (W, H)); c.alpha_composite(cover_fit(load(photo), W, H))
    c.alpha_composite(grad_v(W, 430, 205, 0))
    c.alpha_composite(grad_v(W, 520, 0, 210), (0, H - 520))
    d = ImageDraw.Draw(c)
    draw_text(d, (75, 70), wrap(d, headline, f_black(74), W - 150), f_black(74),
              WHITE, center_w=W - 150, shadow=(0, 3, (0, 0, 0, 160)))
    pill(d, (210, H - 250, W - 210, H - 170), GOLD, CTA, f_bold(42), NAVY)
    center(d, SITE, f_bold(36), WHITE, W, H - 120, shadow=(0, 1, (0, 0, 0, 120)))
    save(c, D_FEED, fname)

def feed_cover_post(cover, headline, subtitle, fname, accent=BLUE,
                    badge=None, badge_color=RED, cta=CTA):
    """Post 1:1 texto a esquerda + capa a direita (fundo creme)."""
    W = H = 1080
    c = Image.new("RGBA", (W, H), CREAM + (255,)); d = ImageDraw.Draw(c)
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
    draw_text(d, (70, y + 18), wrap(d, subtitle, f_bold(30), col), f_bold(30), accent)
    place_cover(c, cover, (560, 150, 1020, 610))
    pill(d, (70, 770, 650, 850), GOLD, cta, f_bold(40), NAVY)
    d.text((72, 886), SITE, font=f_bold(34), fill=NAVY)
    save(c, D_FEED, fname)

def feed_temas():
    W = H = 1080
    c = Image.new("RGBA", (W, H), NAVY + (255,)); d = ImageDraw.Draw(c)
    center(d, "Escolha o tema da história", f_black(58), WHITE, W, 60)
    covers = ["capa-abigail.png", "capa-noe.png", "capa-miriam.png",
              "capa-rebeca.png", "capa-lucas-max.png", "capa-nossa-familia.png"]
    labels = ["Espaço", "Dinossauros", "Fundo do mar", "Super-heróis", "Pets", "Família"]
    cols, pad, top = 3, 50, 190
    cw = (W - pad * (cols + 1)) // cols
    for i, (cv, lab) in enumerate(zip(covers, labels)):
        r, col = divmod(i, cols)
        x0 = pad + col * (cw + pad); y0 = top + r * (cw + 90)
        place_cover(c, cap(cv), (x0, y0, x0 + cw, y0 + cw), rad=20)
        lw = d.textlength(lab, font=f_bold(32))
        d.text((x0 + (cw - lw) / 2, y0 + cw + 14), lab, font=f_bold(32), fill=GOLD)
    center(d, CTA_SITE, f_bold(34), WHITE, W, H - 70)
    save(c, D_FEED, "feed-03-temas.jpg")

def feed_blackfriday():
    W = H = 1080
    c = Image.new("RGBA", (W, H), NAVY_DARK + (255,)); d = ImageDraw.Draw(c)
    center(d, "BLACK FRIDAY", f_black(96), GOLD, W, 70)
    center(d, "Seu livro personalizado com condição especial", f_bold(34), WHITE, W, 185)
    place_cover(c, cap("capa-rebeca.png"), (330, 270, 750, 690))
    pill(d, (270, 760, 810, 844), GOLD, "Garanta o seu", f_bold(44), NAVY)
    center(d, SITE + "  •  só até " + DATE_BF, f_bold(34), WHITE, W, 910)
    save(c, D_FEED, "feed-05-blackfriday.jpg")

def feed_prova():
    """Post de prova social com foto de estilo de vida + frase destaque."""
    W = H = 1080
    c = Image.new("RGBA", (W, H)); c.alpha_composite(cover_fit(load(cap("foto-raquel-papai.png")), W, H))
    c.alpha_composite(grad_v(W, 560, 0, 220), (0, H - 560))
    d = ImageDraw.Draw(c)
    draw_stars(d, W / 2, H - 410, 5, r=24)
    quote = "\u201cA reação dela ao se ver no livro não tem preço.\u201d"
    draw_text(d, (80, H - 360), wrap(d, quote, f_black(50), W - 160), f_black(50),
              WHITE, center_w=W - 160, shadow=(0, 2, (0, 0, 0, 160)))
    pill(d, (210, H - 180, W - 210, H - 100), GOLD, CTA, f_bold(40), NAVY)
    save(c, D_FEED, "feed-10-prova.jpg")

# ================================================================ CARROSSEIS
def carr_slide_base(bg=CREAM):
    return Image.new("RGBA", (1080, 1080), bg + (255,))

def carousel_como_funciona():
    pre = "c1-comofunciona"
    # slide 1 - capa
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    center(d, "Como funciona", f_black(76), WHITE, 1080, 120)
    center(d, "em 3 passos simples", f_bold(40), GOLD, 1080, 230)
    place_cover(c, cap("capa-meupai-heroi.png"), (310, 340, 770, 800))
    center(d, "Arraste  →", f_bold(34), WHITE, 1080, 900)
    save(c, D_CARR, f"{pre}-1.jpg")
    steps = [
        ("1", "Envie a foto", "Fotos nítidas de quem é o herói da história — rosto, cabelo e traços.", "foto-raquel-papai.png"),
        ("2", "A gente cria", "Criamos o personagem e uma história única, com o rosto do seu filho.", "capa-abigail.png"),
        ("3", "Receba e aprove", "Você vê a prévia e aprova tudo antes de imprimir. Sem risco.", "foto-meupai-heroi.png"),
    ]
    for i, (num, title, desc, img) in enumerate(steps, start=2):
        c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
        place_cover(c, cap(img), (0, 0, 1080, 560), rad=0, shadow=False)
        c.alpha_composite(grad_v(1080, 200, 0, 120), (0, 360))
        d = ImageDraw.Draw(c)
        d.ellipse([70, 620, 210, 760], fill=NAVY + (255,))
        nw = d.textlength(num, font=f_black(84))
        d.text((140 - nw / 2, 640), num, font=f_black(84), fill=GOLD)
        d.text((250, 640), title, font=f_black(64), fill=NAVY)
        draw_text(d, (70, 800), wrap(d, desc, f_bold(40), 940), f_bold(40), GREY)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    # slide final CTA
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (90, 300), wrap(d, "Pronto para criar a história do seu filho?", f_black(66), 900),
              f_black(66), WHITE, center_w=900)
    pill(d, (190, 640, 890, 730), GOLD, CTA, f_bold(46), NAVY)
    center(d, SITE, f_bold(40), GOLD, 1080, 780)
    logo_chip(c, 540, 1010, logo_h=90)
    save(c, D_CARR, f"{pre}-5.jpg")

def carousel_temas():
    pre = "c2-temas"
    # slide 1 intro
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (80, 380), wrap(d, "Qual é a cara do seu filho?", f_black(78), 920),
              f_black(78), WHITE, center_w=920)
    center(d, "Arraste e escolha o tema  →", f_bold(38), GOLD, 1080, 640)
    save(c, D_CARR, f"{pre}-1.jpg")
    themes = [
        ("capa-abigail.png", "ESPAÇO", "Foguetes, planetas e curiosidade."),
        ("capa-noe.png", "DINOSSAUROS", "Uma expedição pré-histórica cheia de coragem."),
        ("capa-miriam.png", "FUNDO DO MAR", "Tartarugas, corais e muita descoberta."),
        ("capa-rebeca.png", "SUPER-HERÓIS", "Capa ao vento e coragem no coração."),
        ("capa-lucas-max.png", "PETS", "Seu filho e o melhor amigo na mesma história."),
    ]
    for i, (img, lab, desc) in enumerate(themes, start=2):
        c = Image.new("RGBA", (1080, 1080))
        c.alpha_composite(cover_fit(load(cap(img)), 1080, 1080))
        c.alpha_composite(grad_v(1080, 480, 0, 225), (0, 600))
        d = ImageDraw.Draw(c)
        d.text((70, 820), lab, font=f_black(70), fill=GOLD)
        draw_text(d, (70, 910), wrap(d, desc, f_bold(38), 940), f_bold(38), WHITE)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    # final CTA
    c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
    draw_text(d, (90, 330), wrap(d, "Tem um tema especial em mente?", f_black(64), 900),
              f_black(64), NAVY, center_w=900)
    center(d, "A gente cria a história sob medida.", f_bold(38), BLUE, 1080, 520)
    pill(d, (190, 640, 890, 730), GOLD, CTA, f_bold(46), NAVY)
    center(d, SITE, f_bold(40), NAVY, 1080, 780)
    logo_chip(c, 540, 1020, logo_h=90)
    save(c, D_CARR, f"{pre}-7.jpg")

def carousel_natal():
    pre = "c3-natal"
    # intro
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 1080, 24], fill=RED + (255,))
    d.rectangle([0, 1056, 1080, 1080], fill=RED + (255,))
    draw_text(d, (80, 340), wrap(d, "Presentes de Natal que emocionam", f_black(74), 920),
              f_black(74), WHITE, center_w=920)
    center(d, "um para cada pessoa que você ama  →", f_bold(36), GOLD, 1080, 640)
    save(c, D_CARR, f"{pre}-1.jpg")
    people = [
        ("capa-amordemae.png", "Para a mamãe", "O amor de mãe em cada página."),
        ("capa-amor-de-avo.png", "Para os avós", "O presente que faz o vovô se emocionar."),
        ("capa-raquel-papai.png", "Para o papai", "Aventuras de pai e filho para sempre."),
        ("capa-nicolas-maefilho.png", "Para o bebê", "O primeiro presente, para guardar a vida toda."),
    ]
    for i, (img, lab, desc) in enumerate(people, start=2):
        c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
        place_cover(c, cap(img), (175, 70, 905, 800), rad=26)  # caixa quadrada: capa inteira
        d = ImageDraw.Draw(c)
        d.text((90, 835), lab, font=f_black(60), fill=NAVY)
        draw_text(d, (90, 915), wrap(d, desc, f_bold(38), 900), f_bold(38), GREY)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    # CTA final
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    d.rectangle([0, 0, 1080, 24], fill=RED + (255,))
    d.rectangle([0, 1056, 1080, 1080], fill=RED + (255,))
    draw_text(d, (90, 300), wrap(d, "Garanta o presente antes do prazo de Natal", f_black(64), 900),
              f_black(64), WHITE, center_w=900)
    pill(d, (230, 600, 850, 680), RED, "Peça até " + DATE_XMAS, f_bold(42), WHITE)
    pill(d, (190, 720, 890, 810), GOLD, CTA, f_bold(46), NAVY)
    center(d, SITE, f_bold(38), GOLD, 1080, 860)
    save(c, D_CARR, f"{pre}-6.jpg")

def carousel_antes_depois():
    pre = "c4-antesdepois"
    # intro
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (90, 320), wrap(d, "Da foto real ao personagem do livro", f_black(74), 900),
              f_black(74), WHITE, center_w=900)
    center(d, "Veja a transformação  →", f_bold(38), GOLD, 1080, 640)
    save(c, D_CARR, f"{pre}-1.jpg")
    pairs = [
        ("foto-sofia.png", "capa-sofia-alfabeto.png", "A Sofia virou a heroína da própria história"),
        ("foto-matteo.png", "cartoon-capa-matteo.jpg", "O Matteo virou personagem do seu livro"),
        ("cartoon-foto-davi.jpg", "cartoon-capa-davi.png", "O Davi virou o herói da aventura dele"),
    ]
    panel, top = 430, 250
    lx, rx = 65, 1080 - 65 - 430
    cxm, cym = 540, top + panel / 2
    for i, (real, char, nm) in enumerate(pairs, start=2):
        c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
        center(d, "DA FOTO AO LIVRO", f_black(50), WHITE, 1080, 80)
        place_cover(c, cap(real), (lx, top, lx + panel, top + panel), rad=24)
        place_cover(c, cap(char), (rx, top, rx + panel, top + panel), rad=24)
        d = ImageDraw.Draw(c)
        draw_text(d, (lx + panel / 2, top + panel + 18), ["A FOTO"], f_bold(34), WHITE, anchor="ma")
        draw_text(d, (rx + panel / 2, top + panel + 18), ["O PERSONAGEM"], f_bold(34), GOLD, anchor="ma")
        d.ellipse([cxm - 56, cym - 56, cxm + 56, cym + 56], fill=GOLD + (255,))
        d.polygon([(cxm - 20, cym - 28), (cxm - 20, cym + 28), (cxm + 30, cym)], fill=NAVY + (255,))
        draw_text(d, (90, top + panel + 110), wrap(d, nm, f_black(50), 900),
                  f_black(50), WHITE, center_w=900)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    # CTA final
    c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
    draw_text(d, (90, 300), wrap(d, "Quer ver seu filho assim?", f_black(70), 900),
              f_black(70), NAVY, center_w=900)
    center(d, "Envie uma foto e receba a prévia grátis.", f_bold(36), BLUE, 1080, 480)
    pill(d, (190, 620, 890, 710), GOLD, CTA, f_bold(46), NAVY)
    center(d, SITE, f_bold(40), NAVY, 1080, 760)
    logo_chip(c, 540, 1020, logo_h=90)
    save(c, D_CARR, f"{pre}-5.jpg")

def carousel_faq():
    pre = "c5-faq"
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (90, 360), wrap(d, "Perguntas frequentes", f_black(84), 920),
              f_black(84), WHITE, center_w=920)
    center(d, "antes de criar o seu  →", f_bold(38), GOLD, 1080, 560)
    save(c, D_CARR, f"{pre}-1.jpg")
    faqs = [
        ("Preciso saber desenhar ou usar algum programa?",
         "Não! Você só envia uma foto. A gente cria o personagem e toda a história para você."),
        ("Posso ver antes de imprimir?",
         "Sim. Você recebe a prévia e aprova tudo antes. Sem risco e sem surpresa."),
        ("Quanto tempo leva?",
         "A prévia digital sai na hora. O eBook é imediato e o livro impresso é enviado até você."),
        ("Quais formatos existem?",
         "eBook em PDF (na hora), livro impresso, vídeo narrado e até animação."),
    ]
    for i, (q, a) in enumerate(faqs, start=2):
        c = carr_slide_base(CREAM); d = ImageDraw.Draw(c)
        d.text((70, 80), str(i - 1), font=f_black(130), fill=GOLD + (255,))
        y = draw_text(d, (70, 270), wrap(d, q, f_black(56), 940), f_black(56), NAVY, line_sp=1.05)
        draw_text(d, (70, y + 30), wrap(d, a, f_bold(42), 940), f_bold(42), GREY, line_sp=1.15)
        d.text((72, 985), SITE, font=f_bold(34), fill=NAVY)
        save(c, D_CARR, f"{pre}-{i}.jpg")
    c = carr_slide_base(NAVY); d = ImageDraw.Draw(c)
    draw_text(d, (90, 320), wrap(d, "Ainda com dúvida?", f_black(72), 900),
              f_black(72), WHITE, center_w=900)
    center(d, "Crie a prévia grátis e veja na prática.", f_bold(38), GOLD, 1080, 500)
    pill(d, (190, 640, 890, 730), GOLD, CTA, f_bold(46), NAVY)
    center(d, SITE, f_bold(40), GOLD, 1080, 780)
    logo_chip(c, 540, 1020, logo_h=90)
    save(c, D_CARR, f"{pre}-6.jpg")

# ================================================================ STORIES
def story_photo_cta():
    W, H = 1080, 1920
    c = Image.new("RGBA", (W, H)); c.alpha_composite(cover_fit(load(cap("foto-meupai-heroi.png")), W, H))
    c.alpha_composite(grad_v(W, 650, 210, 0)); c.alpha_composite(grad_v(W, 780, 0, 225), (0, H - 780))
    d = ImageDraw.Draw(c)
    draw_text(d, (75, 150), wrap(d, "Uma foto. Uma história. Uma memória eterna.", f_black(82), W - 150),
              f_black(82), WHITE, center_w=W - 150, line_sp=1.1, shadow=(0, 3, (0, 0, 0, 170)))
    pill(d, (150, H - 420, W - 150, H - 320), GOLD, CTA, f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 120, logo_h=86)
    save(c, D_STORY, "story-01-cta.jpg")

def story_prazo():
    W, H = 1080, 1920
    c = Image.new("RGBA", (W, H), NAVY_DARK + (255,)); d = ImageDraw.Draw(c)
    d.text((70, 120), "Quer receber", font=f_black(100), fill=WHITE)
    d.text((70, 240), "no Natal?", font=f_black(100), fill=GOLD)
    pill(d, (70, 420, 760, 520), RED, "Peça até " + DATE_XMAS, f_bold(54), WHITE)
    place_cover(c, cap("capa-nicolas-maefilho.png"), (260, 620, 820, 1240))
    pill(d, (150, 1370, W - 150, 1470), GOLD, CTA, f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 110, logo_h=86)
    save(c, D_STORY, "story-02-prazo.jpg")

def story_comofunciona():
    W, H = 1080, 1920
    c = Image.new("RGBA", (W, H), CREAM + (255,)); d = ImageDraw.Draw(c)
    center(d, "Como funciona", f_black(84), NAVY, W, 110)
    steps = [("1", "Envie a foto", "Fotos nítidas de quem é o herói da história."),
             ("2", "A gente cria", "O personagem e a história, com o rosto do seu filho."),
             ("3", "Receba e aprove", "Veja a prévia e aprove antes de imprimir.")]
    y = 330
    for num, title, desc in steps:
        d.ellipse([80, y, 200, y + 120], fill=NAVY + (255,))
        nw = d.textlength(num, font=f_black(70)); d.text((140 - nw / 2, y + 18), num, font=f_black(70), fill=GOLD)
        d.text((250, y + 6), title, font=f_black(56), fill=NAVY)
        draw_text(d, (250, y + 78), wrap(d, desc, f_bold(36), W - 310), f_bold(36), GREY)
        y += 330
    pill(d, (150, H - 420, W - 150, H - 320), GOLD, CTA, f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 120, logo_h=86)
    save(c, D_STORY, "story-03-comofunciona.jpg")

def story_enquete():
    W, H = 1080, 1920
    c = Image.new("RGBA", (W, H), NAVY + (255,)); d = ImageDraw.Draw(c)
    center(d, "Qual combina com", f_black(72), WHITE, W, 150)
    center(d, "o seu filho?", f_black(72), GOLD, W, 250)
    place_cover(c, cap("capa-rebeca.png"), (90, 470, 520, 900), rad=24)
    place_cover(c, cap("capa-abigail.png"), (560, 470, 990, 900), rad=24)
    center(d, "Super-herói", f_bold(40), WHITE, 305, 930)
    center(d, "Espaço", f_bold(40), WHITE, 775, 930)
    place_cover(c, cap("capa-noe.png"), (90, 1040, 520, 1470), rad=24)
    place_cover(c, cap("capa-lucas-max.png"), (560, 1040, 990, 1470), rad=24)
    center(d, "Dinossauros", f_bold(40), WHITE, 305, 1500)
    center(d, "Pets", f_bold(40), WHITE, 775, 1500)
    center(d, "Toque e responda a enquete  →", f_bold(40), GOLD, W, 1600)
    logo_chip(c, W / 2, H - 100, logo_h=80)
    save(c, D_STORY, "story-04-enquete.jpg")

def story_prova():
    W, H = 1080, 1920
    c = Image.new("RGBA", (W, H)); c.alpha_composite(cover_fit(load(cap("foto-raquel-papai.png")), W, H))
    c.alpha_composite(grad_v(W, 700, 150, 0)); c.alpha_composite(grad_v(W, 760, 0, 225), (0, H - 760))
    d = ImageDraw.Draw(c)
    draw_stars(d, W / 2, 200, 5, r=32)
    draw_text(d, (80, 300), wrap(d, "\u201cMelhor presente que já demos. Virou relíquia da família.\u201d",
              f_black(64), W - 160), f_black(64), WHITE, center_w=W - 160, shadow=(0, 2, (0, 0, 0, 170)))
    pill(d, (150, H - 430, W - 150, H - 330), GOLD, CTA, f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 120, logo_h=86)
    save(c, D_STORY, "story-05-prova.jpg")

def story_blackfriday():
    W, H = 1080, 1920
    c = Image.new("RGBA", (W, H), NAVY_DARK + (255,)); d = ImageDraw.Draw(c)
    center(d, "BLACK", f_black(140), GOLD, W, 160)
    center(d, "FRIDAY", f_black(140), GOLD, W, 320)
    center(d, "Condição especial por tempo limitado", f_bold(40), WHITE, W, 540)
    place_cover(c, cap("capa-rebeca.png"), (290, 660, 790, 1160))
    pill(d, (230, 1260, 850, 1360), RED, "Só até " + DATE_BF, f_bold(48), WHITE)
    pill(d, (150, 1420, W - 150, 1520), GOLD, "Garanta o seu", f_bold(50), NAVY)
    logo_chip(c, W / 2, H - 110, logo_h=86)
    save(c, D_STORY, "story-06-blackfriday.jpg")

# ================================================================ RUN
if __name__ == "__main__":
    print("== FEED ==")
    feed_photo_hero(cap("foto-meupai-heroi.png"), "Seu filho é o herói do próprio livro", "feed-01-hero.jpg")
    feed_cover_post(cap("capa-meupai-heroi.png"),
                    "Transforme uma foto em uma história inesquecível",
                    "onde seu filho é o protagonista.", "feed-02-produto.jpg")
    feed_temas()
    feed_cover_post(cap("capa-nicolas-maefilho.png"),
                    "O presente de Natal que a família guarda para sempre",
                    "Peça até " + DATE_XMAS + " e receba a tempo.", "feed-04-natal.jpg",
                    accent=RED, badge="NATAL", badge_color=RED)
    feed_blackfriday()
    feed_cover_post(cap("capa-ester.png"),
                    "O aniversário dele vira uma história só dele",
                    "Um presente que ninguém esquece.", "feed-06-aniversario.jpg",
                    badge="ANIVERSÁRIO", badge_color=BLUE)
    feed_cover_post(cap("capa-amor-de-avo.png"),
                    "O presente que emociona os avós",
                    "Netos e avós na mesma história.", "feed-07-avos.jpg",
                    badge="PARA OS AVÓS", badge_color=NAVY)
    feed_cover_post(cap("capa-lucas-max.png"),
                    "Seu filho e o melhor amigo na mesma história",
                    "O pet da família também vira personagem.", "feed-08-pets.jpg",
                    badge="PETS", badge_color=NAVY)
    feed_cover_post(cap("capa-nicolas-maefilho.png"),
                    "O primeiro presente que ele guarda para sempre",
                    "Perfeito para recém-nascidos.", "feed-09-bebe.jpg",
                    badge="RECÉM-NASCIDO", badge_color=BLUE)
    feed_prova()
    print("== CARROSSEIS ==")
    carousel_como_funciona()
    carousel_temas()
    carousel_natal()
    carousel_antes_depois()
    carousel_faq()
    print("== STORIES ==")
    story_photo_cta()
    story_prazo()
    story_comofunciona()
    story_enquete()
    story_prova()
    story_blackfriday()
    print("\nTudo salvo em:", BASE)
