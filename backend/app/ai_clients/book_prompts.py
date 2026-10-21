"""Prompts do pipeline foto -> avatar -> paginas do livro.

Regras de ouro:
- 1 avatar-base gerado da foto; reusado como character_ref em TODAS as paginas
- Estilo TMT aprovado: rosto pintura fotorrealista 1:1; corpo ilustrado; luz cinematografica; cenario pintado
- Figurino da HISTORIA nas paginas (explorador, medica, marinheiro...); avatar nao trava a roupa da foto
- Identidade da foto e imutavel e esta ACIMA do estilo: nao inventar franja, olhos, idade, etnia
- Proporcoes naturais da foto (cabeca anatomica, sem aumento); sem chibi/funko
- Expressao facial MUDA por pagina e deve coincidir com a historia
"""

from __future__ import annotations

import re
import unicodedata

# --------------------------------------------------------------------------- #
# Expressoes faciais permitidas
# --------------------------------------------------------------------------- #
EXPRESSIONS: dict[str, str] = {
    "alegria": (
        "sorriso ABERTO visivel, bochechas bem erguidas, ombros soltos — "
        "PROIBIDO sorriso fechado de retrato"
    ),
    "curiosidade": (
        "sobrancelhas bem erguidas, boca entreaberta, corpo inclinado para a "
        "descoberta, olhar preso no objeto"
    ),
    "medo_gentil": (
        "boca fechada tensa, ombros recolhidos, corpo um pouco para tras, "
        "palpebras abertas no MESMO tamanho de olho — sem terror, sem chibi"
    ),
    "determinacao": (
        "queixo firme, boca fechada decidida, corpo inclinado para a acao, olhar direto no objetivo"
    ),
    "surpresa": (
        "boca em O bem marcada, sobrancelhas BEM erguidas, palpebras abertas "
        "no MESMO tamanho de olho, corpo recuado um instante"
    ),
    "calma": (
        "sorriso fechado aconchegante, ombros baixos e soltos, olhar sereno — "
        "ainda assim uma emocao, nao cara vazia"
    ),
    "tristeza_leve": ("cantos da boca caidos, ombros caidos, olhar baixo — sem choro de teatro"),
    "concentracao": (
        "sobrancelhas franzidas, boca fechada, corpo quieto e inclinado no trabalho, olhar cravado"
    ),
    "carinho": (
        "sorriso terno amplo, cabeca inclinada, corpo perto do outro, bracos "
        "em gesto de abraco ou cuidado"
    ),
    "orgulho": ("peito estufado, sorriso confiante aberto, queixo um pouco alto, postura ereta"),
    "vergonha": (
        "olhar baixo, sorriso timido de lado, ombros para dentro, mao perto do rosto ou da barriga"
    ),
    "animacao": (
        "sorriso LARGO, corpo em movimento (pulo ou bracos abertos), energia "
        "no tronco — sem inchar o olho"
    ),
}

_DEFAULT_EXPRESSION = "alegria"

_INFER_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("medo_gentil", re.compile(r"medo|assust|escuro|trem|perigo|susto|receio", re.IGNORECASE)),
    (
        "tristeza_leve",
        re.compile(r"trist|chor|doente|separad|desanim|sozinh|saudade", re.IGNORECASE),
    ),
    ("vergonha", re.compile(r"vergonh|timid|constrang|envergonh|corado", re.IGNORECASE)),
    (
        "surpresa",
        re.compile(r"surpre|de repente|olha!|inesperad|uau|nossa|assombro", re.IGNORECASE),
    ),
    (
        "curiosidade",
        re.compile(r"curios|pergunt|descob|imagin|pensa|olha as|observ|investig", re.IGNORECASE),
    ),
    (
        "determinacao",
        re.compile(
            r"decid|determin|coragem|tentar|construir|ajuda|limpo|miss|enfrentar", re.IGNORECASE
        ),
    ),
    ("concentracao", re.compile(r"concent|cuidado|conta|junta|coloca|aprende|foco", re.IGNORECASE)),
    ("carinho", re.compile(r"abrac|carinh|amor|anin|colo|corac|beijo", re.IGNORECASE)),
    ("orgulho", re.compile(r"orgulh|conquist|consegui|pronto|cheinho|vitor", re.IGNORECASE)),
    (
        "animacao",
        re.compile(r"empolg|animad|eufor|pulando|correndo de alegria|animacao", re.IGNORECASE),
    ),
    ("calma", re.compile(r"calm|quiet|paz|dorm|tranquil|seren|descans", re.IGNORECASE)),
    ("alegria", re.compile(r"feliz|alegr|sorr|brinc|festa|brilha|divert|risad", re.IGNORECASE)),
]


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))


def normalize_expression(value: str | None) -> str:
    if not value:
        return _DEFAULT_EXPRESSION
    key = _strip_accents(value.strip().lower()).replace(" ", "_").replace("-", "_")
    aliases = {
        "medo": "medo_gentil",
        "tristeza": "tristeza_leve",
        "triste": "tristeza_leve",
        "feliz": "alegria",
        "happy": "alegria",
        "curious": "curiosidade",
        "surprised": "surpresa",
        "calm": "calma",
        "determined": "determinacao",
        "proud": "orgulho",
        "tender": "carinho",
        "focused": "concentracao",
        "shy": "vergonha",
        "excited": "animacao",
        "empolgado": "animacao",
        "timido": "vergonha",
    }
    key = aliases.get(key, key)
    return key if key in EXPRESSIONS else _DEFAULT_EXPRESSION


def infer_expression(*texts: str) -> str:
    blob = _strip_accents(" ".join(t for t in texts if t))
    for name, pattern in _INFER_RULES:
        if pattern.search(blob):
            return name
    return _DEFAULT_EXPRESSION


def expression_directive(expression: str | None) -> str:
    key = normalize_expression(expression)
    detail = EXPRESSIONS[key]
    return (
        f"EXPRESSAO FACIAL OBRIGATORIA desta pagina: '{key}' ({detail}). "
        "A emocao tem de ser LEGIVEL num thumbnail: rosto E pose. "
        "MUDE sobrancelhas, cantos da boca, tensao dos labios, olhar e postura "
        "do corpo ate a emocao ficar obvia. "
        "PROIBIDO retrato parado com a cara neutra do avatar. "
        "NAO mude o TAMANHO dos olhos: emocao NAO autoriza olhos maiores; a "
        "fracao do rosto permanece a da foto/avatar. "
        "NAO mude identidade: mesmo formato de rosto/bochechas, mesmos olhos "
        "(cor, tamanho NATURAL, espacamento), mesmo nariz, mesma estrutura da "
        "boca, mesmo cabelo, mesmo tom de pele e mesma idade do avatar-base. "
        "PROIBIDO copiar a expressao neutra do avatar; a emocao desta pagina "
        "vence. Nunca altere a estrutura do rosto so para forcar a expressao."
    )


# --------------------------------------------------------------------------- #
# Enquadramento e faixa de texto (roteiro visual da pagina)
# --------------------------------------------------------------------------- #
SHOTS: dict[str, str] = {
    "close": "close do rosto ou da acao — aproxime a camera; o objeto/rosto ocupa boa parte do quadro",
    "medium": (
        "plano medio — peito, ombros e cabeca; o rosto ocupa pelo menos um "
        "quinto da altura do quadro, perto da camera. PROIBIDO corpo inteiro "
        "no fundo ou figura minuscula ao lado de um animal"
    ),
    "wide": "plano geral — corpo inteiro e cenario amplo",
    "detail": "plano detalhe — objeto, mao ou acao em close; o rosto pode sair do quadro",
}
_DEFAULT_SHOT = "medium"
_SHOT_ALIASES = {
    "closeup": "close",
    "close_up": "close",
    "plano_detalhe": "detail",
    "detalhe": "detail",
    "wide_shot": "wide",
    "geral": "wide",
    "plano_geral": "wide",
    "plano_medio": "medium",
    "medio": "medium",
}

TEXT_BANDS = ("top", "bottom", "left", "right")
_DEFAULT_TEXT_BAND = "bottom"

# Expressoes empacotadas na grade 2x2 da ficha (expression_sheet).
EXPRESSION_SHEET_KEYS: tuple[str, ...] = ("alegria", "surpresa", "determinacao", "calma")


def normalize_shot(value: str | None) -> str:
    if not value:
        return _DEFAULT_SHOT
    key = _strip_accents(value.strip().lower()).replace(" ", "_").replace("-", "_")
    key = _SHOT_ALIASES.get(key, key)
    return key if key in SHOTS else _DEFAULT_SHOT


def identity_shot(value: str | None, *, layout: str = "story") -> str:
    """Wide some a cara. Nome/alfabeto pode ser geral; historia fica medio."""
    if layout == "name":
        return "wide"
    if layout == "dedication":
        return normalize_shot(value)
    key = normalize_shot(value)
    return "medium" if key == "wide" else key


def normalize_text_band(value: str | None) -> str:
    if not value:
        return _DEFAULT_TEXT_BAND
    key = _strip_accents(value.strip().lower())
    return key if key in TEXT_BANDS else _DEFAULT_TEXT_BAND


def shot_directive(shot: str | None) -> str:
    key = normalize_shot(shot)
    return f"ENQUADRAMENTO OBRIGATORIO: '{key}' ({SHOTS[key]})."


def text_band_directive(band: str | None) -> str:
    key = normalize_text_band(band)
    if key in {"left", "right"}:
        lado = "esquerdo" if key == "left" else "direito"
        return (
            f"FAIXA DE TEXTO: reserve cerca de 45% do lado {lado} do quadro ({key}) "
            "como uma area calma e limpa (nevoa suave, agua ou folhagem desfocada), "
            "sem personagens nem objetos importantes. Mantenha o protagonista "
            "inteiramente no lado oposto: rosto, cabelo, corpo e maos nao podem "
            "entrar nessa area."
        )
    lado = "superior" if key == "top" else "inferior"
    return (
        f"FAIXA DE TEXTO: deixe a faixa {lado} do quadro ({key}) mais calma/limpa "
        "(ceu, agua ou folhagem suave) para a estrofe impressa. Nao coloque o "
        "rosto do protagonista nessa faixa."
    )


# --------------------------------------------------------------------------- #
# Avatar (foto -> personagem-base)
# --------------------------------------------------------------------------- #
_HEAD_PROPORTION = (
    "PROPORCAO DA CABECA: identica a da foto — tamanho NATURAL, anatomico, "
    "sem aumentar. PROIBIDO cabeca grande, bobblehead, chibi, funko, anime "
    "ou olhos grandes de cartoon."
)

_SUBJECT_LOCK = (
    "SUJEITO: a crianca da foto de referencia e a UNICA pessoa a desenhar. "
    "Ignore adultos, colo, maos de quem segura, outras pessoas, casa, caminho "
    "e cenario. NAO inclua ninguem alem da crianca."
)

_GENERIC_FACE_LOCK = (
    "ANTI-ROSTO-GENERICO (prioridade maxima): NAO invente um bebe de animacao "
    "fofo, rosto de banco de imagens ou crianca 'bonitinha' padronizada. A "
    "identidade e a da foto anexa. Colocada ao lado da foto, um familiar deve "
    "reconhecer na hora que e a MESMA crianca. Se o modelo hesitar, copie os "
    "tracos atipicos da foto em vez de suavizar. "
    "NAO deixe a crianca 'mais fofa' aumentando os olhos. Identidade da foto "
    "esta ACIMA do estilo de livro."
)

_HAIR_LOCK = (
    "CABELO (imutavel): copie da foto o penteado EXATO — cor, textura, "
    "comprimento, risca, volume, densidade e se existe ou NAO existe franja. "
    "Se o cabelo da foto for fino, ralo ou esvoacante, MANTENHA assim — "
    "PROIBIDO engrossar, escurecer ou 'penteado de salao'. "
    "Se a testa estiver visivel na foto, a testa DEVE ficar visivel no avatar. "
    "PROIBIDO inventar franja, cortina, baby bangs, fios na testa ou mudar o "
    "penteado. Nao 'melhore' o cabelo."
)

_FACE_FIDELITY = (
    "ROSTO REALISTA: deve parecer uma foto desta crianca, qualidade de camera — "
    "pintura digital fotorrealista (pele, cilios, iris, labios, cabelo fio a fio), "
    "identidade 1:1. "
    "Acabamento levemente pictorico, com tracos leves de desenho — mais REAL "
    "que desenho. Nao foto crua colada; nao cartoon. IDENTIDADE (rosto, olhos, "
    "nariz, boca, idade) esta ACIMA do estilo. NAO cole o rosto fotografico "
    "como recorte. "
    "OLHOS: ocupam a MESMA fracao do rosto que na foto — mesma largura, "
    "altura, espacamento e quantidade de branco visivel. Se hesitar, DIMINUA; "
    "NUNCA aumente. PROIBIDO iris gigante, olho de boneca, brilho de lente "
    "cobrindo o olho, fofura via olhos maiores, olhos anime/chibi/cartoon. "
    "IDENTIDADE: copie da foto formato, espacamento e cor EXATA dos olhos, "
    "palpebras, estrutura ossea, bochechas, sobrancelhas, nariz, labios, "
    "tom de pele e idade aparente. "
    "IDADE: a da foto (bebe continua bebe; nao 'envelheca' para um modelo fofo). "
    "FORMATO DO ROSTO: largura, bochechas, queixo e pescoco identicos a foto "
    "(mesma fracao da largura da cabeca). PROIBIDO embelezar engordando "
    "bochechas, arredondando o maxilar ou alargando a cara — nao faca uma "
    "versao mais gorda/fofa do mesmo menino. Se o rosto estiver "
    "mais cheio que a foto, REDUZA o volume das bochechas ate bater. "
    "PELE: microtextura NATURAL da foto, acabamento pictorico leve (nao "
    "porcelana, nao airbrush pesado, nao filtro de beleza, nao pele plastica lisa). "
    "Sem poros grotescos de close extremo. "
    "BOCA: copie a BOCA e o TIPO de sorriso da foto (se for sorriso pequeno/"
    "candido, mantenha pequeno). PROIBIDO sorriso largo de banco de imagens "
    "e sorriso fechado de desenho. "
    "ACESSORIOS DE IDENTIDADE: preserve brinco, oculos ou outro acessorio do "
    "ROSTO visivel na foto; NAO invente o que nao estiver la. "
    "NAO embeleze, NAO 'corrija' tracos atipicos, assimetria ou estrutura "
    "ossea unica. NAO invente sardas, pintas, covinhas ou dentes que nao "
    "estejam claramente na foto."
)

_CGI_AVATAR_STYLE = (
    "ESTILO HIBRIDO OBRIGATORIO: ROSTO fotorrealista + CORPO CGI 3D. "
    "ROSTO: pintura digital fotorrealista, qualidade de camera, identidade 1:1 "
    "da foto — mais REAL que desenho. Junta continua no pescoco. "
    "CORPO: CGI 3D de filme infantil (pescoco, ombros, tronco, roupa); "
    "volume, luz suave, tecido ilustrado. Corpo mais DESENHO/CGI que o rosto. "
    "LUZ: suave, quente, frontal/lateral, sem sombra dura. "
    "FUNDO: bokeh creme/dourado, sem cenario narrativo. "
    "PROIBIDO: colagem, recorte fotografico, chibi, cabeca gigante, olhos anime, "
    "crianca generica, texto, marca d'agua. "
    "NAO copie figurino de referencia de estilo (macacao listrado etc.) — "
    "roupa ilustrada simples."
)

_HYBRID_STYLE = (
    "ESTILO TMT OBRIGATORIO (Tell My Tale). "
    "ROSTO: pintura digital fotorrealista desta crianca, identidade 1:1 da foto "
    "(olhos, nariz, boca, orelhas, cabelo fio a fio, idade). Acabamento "
    "levemente pictorico, tracos leves de desenho — mais REAL que desenho. "
    "Nao foto crua colada; nao cartoon; nao chibi. "
    "CORPO: ilustracao 3D de livro infantil (pescoco, ombros, bracos, maos "
    "desenhados; junta continua no pescoco); corpo mais DESENHO que o rosto. "
    "LUZ: cinematografica, quente, glow suave, contraluz/rim light, atmosfera magica. "
    "CENARIO: concept art pintado, rico, saturado, com profundidade — nao foto, "
    "nao 2D chapado, nao linha preta. "
    "IDENTIDADE ACIMA DO ESTILO: o realismo do rosto NAO altera proporcoes "
    "do rosto ou dos olhos. "
    "PROIBIDO: colagem, recorte fotografico, pele de porcelana/plastica, "
    "olhos de boneca enormes, chibi, olhos anime, cel-shading, cartoon chapado, "
    "Pixar/CGI, marca d'agua, texto."
)

_WATERMARK_LOCK = (
    "MARCA D'AGUA E TEXTO: ignore e REMOVA qualquer marca d'agua de banco de "
    "imagens (Vecteezy, Dreamstime, Shutterstock, Getty, etc.), letras na frente "
    "do rosto, logos e captions. Nunca copie texto da foto para a ilustracao."
)

AVATAR_PROMPT = (
    "TAREFA: gere UM retrato-base (avatar) da pessoa da foto, para ser a UNICA "
    "referencia de IDENTIDADE (rosto, cabelo, corpo) em todas as paginas de um "
    "livro infantil personalizado. A roupa deste retrato NAO e o figurino do livro.\n\n"
    "IDENTITY LOCK: desenhe ESTA crianca especifica da foto anexa. NAO invente "
    "uma crianca generica. Se colocada ao lado da foto, um pai/mae deve "
    "reconhecer na hora.\n\n"
    "IDENTIDADE (prioridade maxima, ACIMA do estilo): a pessoa deve ser "
    "reconhecivel — mesmos tracos da foto (formato do rosto e bochechas; olhos "
    "na MESMA fracao do rosto; sobrancelhas; nariz; boca; cabelo; tom de pele; "
    "idade). O rosto deve parecer uma foto desta crianca, qualidade de camera, "
    "com tracos leves de desenho; corpo CGI 3D. NAO cole a "
    "foto como recorte. "
    "NAO embelezar, NAO inventar caracteristicas, NAO mudar etnia, idade ou "
    "proporcoes. Colocada ao lado da foto, a pessoa deve ser 100% reconhecivel.\n\n"
    f"{_SUBJECT_LOCK}\n\n"
    f"{_GENERIC_FACE_LOCK}\n\n"
    f"{_FACE_FIDELITY}\n\n"
    f"{_HEAD_PROPORTION}\n\n"
    f"{_HAIR_LOCK}\n\n"
    f"{_CGI_AVATAR_STYLE}\n\n"
    f"{_WATERMARK_LOCK}\n\n"
    "COMPOSICAO: UMA so crianca, meio corpo (peito + ombros visiveis e largos o bastante), de frente, "
    "camera na altura dos olhos (NAO plongee / NAO close de rosto). A cabeca deve "
    "ocupar no maximo ~1/3 da altura do quadro; ombros e tronco visiveis abaixo. "
    "Proporcao cabeca-corpo NATURAL da foto — NUNCA cabeca gigante nem bobblehead. "
    "Expressao NEUTRA-ALEGRE leve: parta do sorriso REAL da foto (pequeno se a "
    "foto for pequena) — so o rosto-padrao de referencia; nas cenas do livro a "
    "expressao facial MUDARA conforme a historia. Fundo creme suave ou bokeh "
    "luminoso — SEM casa, SEM caminho, SEM cenario narrativo, SEM objetos, SEM "
    "texto, SEM moldura, SEM marca d'agua. "
    "ROUPA: peca ilustrada simples (nao copiar o macacao/trator nem a roupa da "
    "foto peca por peca). Este retrato e so identidade; o figurino do livro "
    "entra nas paginas.\n\n"
    "SAIDA: uma unica imagem limpa (rosto pintura fotorrealista, qualidade de "
    "camera; corpo CGI 3D de filme infantil). "
    "Este arquivo sera o character_ref imutavel de identidade de todas as paginas."
)

AVATAR_STYLE = (
    "estilo hibrido: rosto deve parecer uma foto, qualidade de camera; "
    "corpo CGI 3D de filme infantil, bokeh creme, peito e ombros; sem foto colada"
)

STYLE = (
    "estilo TMT: rosto pintura fotorrealista, qualidade de camera, tracos leves "
    "de desenho (mais real que desenho); "
    "corpo mais DESENHO que o rosto; luz cinematografica quente com glow e "
    "contraluz; crianca identica a referencia (rosto e olhos na mesma fracao da foto); "
    "cabeca em proporcao NATURAL; identidade acima do estilo; figurino da historia "
    "nas paginas; sem texto"
)

# Perfil mestre do Studio (docs/chatgpt/perfil-mestre.txt): identidade e produto.
_STUDIO_IDENTITY_LOCK = (
    "PERFIL MESTRE STORY R US: a fotografia original do cliente e a fonte "
    "definitiva de identidade. Ordem: (1) foto original, (2) ficha/avatar da "
    "foto, (3) capa aprovada, (4) imagens anteriores so para continuidade. "
    "Nunca substitua a foto por uma geracao anterior em caso de conflito. "
    "Trave formato do rosto, olhos e cor, sobrancelhas, nariz, boca, sorriso, "
    "bochechas, cabelo (cor, textura, comprimento, linha), idade, tom de pele e "
    "proporcoes. Sem crianca generica, sem embelezar, sem mudar etnia ou idade. "
    "Identidade vem antes da estetica: se o rosto estiver errado, a imagem falhou. "
)

_STUDIO_TYPOGRAPHY_LOCK = (
    "TIPOGRAFIA TRAVADA: rounded sans-serif editorial infantil (Nunito / Avenir "
    "Next Rounded / Sofia Pro Soft), Medium ou SemiBold, titulos em Bold, cor "
    "dark navy #172A3A. Proibido cursiva, manuscrita, serifada, Comic Sans ou "
    "fonte decorativa. A mesma familia em capa, miolo e cena com o livro."
)

_STUDIO_ANIMAL_LOCK = (
    "Se houver animal na foto: preserve raca, porte, cor, pelagem, manchas, "
    "focinho, olhos, orelhas e anatomia. Se for inventado, fixe a aparencia uma "
    "vez e nao mude no livro."
)

_PAGE_LOCK = (
    "FORMATO DO LIVRO (grafica): pagina quadrada 1:1 (20x20 cm no M, 15x15 cm no P), "
    "sangria total, arte ate a borda, sem deformar. Rosto, maos e texto a 5 mm da "
    "borda e da dobra (area de seguranca). A estrofe fica so numa faixa calma no "
    "topo ou na base, longe da dobra, nunca numa coluna ao lado da cena e nunca "
    "sobre o rosto. Sem marca d'agua e sem texto solto na cena. "
    + _STUDIO_TYPOGRAPHY_LOCK
)

_REALISTA = (
    "MODO REALISTA PREMIUM: fotografia editorial infantil, realismo delicado, "
    "pele e cabelo naturais, iluminacao suave, cenario elegante, profundidade "
    "fotografica, qualidade comercial, sem aparencia artificial exagerada. "
    "Iris nitida na mesma fracao do rosto da foto, cabelo fio a fio. "
    "Sem cartoon, anime, caricatura, chibi, 3D plastico, olho de boneca, ombros largos, "
    "bracos volumosos ou corpo esticado. "
    + _STUDIO_IDENTITY_LOCK
    + _STUDIO_ANIMAL_LOCK
    + _PAGE_LOCK
)

_CARTOON = (
    "MODO CARTOON PREMIUM: ilustracao claramente DESENHADA (nao foto com filtro), "
    "linhas suaves, volumes arredondados, expressoes infantis, cores alegres e "
    "sofisticadas, cartoon moderno editorial de alto nivel. Olhos levemente maiores, "
    "ainda assim o rosto deriva da foto. Sem anime, manga, chibi extremo, caricatura "
    "extrema, 3D plastico ou personagem generico. "
    + _STUDIO_IDENTITY_LOCK
    + _STUDIO_ANIMAL_LOCK
    + _PAGE_LOCK
)


def book_art_direction(style: str | None) -> str:
    """Direcao de arte da serie: realista ou cartoon, com o formato quadrado do livro."""
    if (style or "").strip().lower() == "cartoon":
        return _CARTOON
    return _REALISTA


CHARACTER_GEN_PREFIX = (
    "Crie um personagem TMT a partir das fotos de "
    "referencia: o rosto deve parecer uma foto, qualidade de camera, com tracos leves "
    "de desenho; corpo claramente desenhado. A foto vale para rosto, cabelo e corpo — "
    "NAO copie a roupa da foto. "
    "TRAVE A IDENTIDADE (acima do estilo): mesmo formato de rosto, mesmos olhos "
    "(cor e MESMA fracao do rosto; se hesitar, diminua), mesmo nariz, boca e sobrancelhas, mesmo cabelo e penteado da "
    "foto (franja so se a foto tiver franja; testa visivel se a foto mostrar "
    "testa), mesmo tom de pele e mesma idade. "
    "Nao invente tracos, nao embeleze, nao 'corrija' tracos atipicos, nao mude "
    f"etnia nem idade. Sem texto, sem moldura, sem marca d'agua. {_SUBJECT_LOCK} "
    f"{_GENERIC_FACE_LOCK} {_FACE_FIDELITY} "
    f"{_HEAD_PROPORTION} {_HAIR_LOCK} {_HYBRID_STYLE} {_WATERMARK_LOCK} "
)

# --------------------------------------------------------------------------- #
# Cena (avatar + historia -> pagina)
# --------------------------------------------------------------------------- #
SCENE_GEN_PREFIX = (
    "REGRA CRITICA DE IDENTIDADE (prioridade maxima, acima de qualquer outra "
    "instrucao): a imagem anexada e a UNICA fonte de verdade para o ROSTO, "
    "cabelo, idade e proporcoes do protagonista. Voce NAO esta criando um "
    "personagem novo - voce esta REDESENHANDO EXATAMENTE A MESMA CRIANCA da "
    "imagem de referencia (avatar-base) em uma nova cena. Copie da referencia, "
    "traco a traco: formato do rosto e das "
    "bochechas; olhos (cor, formato, MESMA fracao do rosto, espacamento); sobrancelhas; "
    "nariz; boca (estrutura base); cabelo (cor exata, textura, comprimento, franja, "
    "risca, penteado); tom de pele; idade aparente; proporcoes do corpo. "
    "NAO copie a ROUPA do avatar nem a roupa da foto — o figurino e o da HISTORIA "
    "(explorador, medica, marinheiro, etc.), o mesmo em todas as paginas. "
    "Colocada lado a lado com a referencia, a crianca desta cena deve parecer "
    "dois quadros do mesmo filme - mesma pessoa; mudam pose, EXPRESSAO FACIAL, "
    "cenario e figurino tematico. "
    f"{_FACE_FIDELITY} "
    f"{_HEAD_PROPORTION} {_HAIR_LOCK} "
    "ESCALA DA CABECA NA CENA: a cabeca tem de ser MENOR que o tronco — "
    "ombros e peito dominam o corpo. Se hesitar, DIMINUA a cabeca; NUNCA "
    "aumente. PROIBIDO bobblehead, cabeca de chibi ou close de rosto que "
    "faca a cabeca ocupar o quadro. Os olhos ficam na mesma fracao do "
    "ROSTO do avatar — nao infle o olho para compensar a cabeca menor. "
    "EXPRESSAO: o avatar-base tem expressao NEUTRA — NAO a copie. A emocao "
    "desta pagina VENCE o avatar: rosto e pose dinamicos alinhados ao "
    "sentimento (alegria, surpresa, determinacao, etc.). Mude sobrancelhas, "
    "boca, olhar e postura. NAO o tamanho dos olhos; a estrutura do rosto "
    "permanece a do avatar. "
    f"{_HYBRID_STYLE} "
    "FONTE DO ROSTO: o AVATAR anexado — nao uma crianca loira de explorador, "
    "nem um menino safari de banco de imagens. "
    "IDADE: a MESMA idade aparente do avatar (bebe/toddler). PROIBIDO "
    "envelhecer para 5-6 anos ou 'menino de filme'. "
    "PROIBIDO safari-kid stock, Pixar/Disney generico, olho maior que o do "
    "avatar, cabelo de salao; se o cabelo do avatar for fino e a testa "
    "visivel, MANTENHA. "
    "PROIBIDO: inventar outra crianca parecida; mudar cabelo, idade, "
    "etnia ou tom de pele; 'embelezar' ou estilizar o rosto de forma diferente "
    "da referencia; copiar a roupa da foto ou do avatar; copiar a "
    "POSE ESTATICA (sentado/parado de frente para a camera) da imagem de "
    "referencia quando a cena pedir outra coisa - a referencia e so um retrato "
    "parado e NAO deve travar a pose desta cena. "
    "ENQUADRAMENTO E COMPOSICAO: siga EXATAMENTE o que a descricao da cena pedir "
    "- se pedir um CLOSE ou PLANO DETALHE (ex.: closeup de uma mao, de um objeto), "
    "faca um close de verdade, aproximando a camera de verdade do objeto/acao "
    "pedido: o objeto (moeda, mao, etc.) deve ocupar boa parte do quadro, e o "
    "rosto do personagem pode ficar PARCIALMENTE fora do enquadramento, desfocado "
    "ou nem aparecer - nao force mostrar o rosto inteiro nem afaste a camera so "
    "para caber o personagem completo; se "
    "pedir uma cena com 2 personagens, pose e as duas; se pedir uma cena DIVIDIDA "
    "em paineis, divida a imagem em paineis. NAO force um enquadramento de corpo "
    "inteiro em cenas que pedem outra coisa. Fora isso, a pose e a acao do "
    "personagem devem ser dinamicas e condizentes com a cena (nao paradas feito "
    "retrato), respeitando sempre o enquadramento pedido. So a IDENTIDADE (rosto, "
    "cabelo, tom de pele, idade) fica fixa; pose, expressao, acao, figurino, "
    "enquadramento e cenario seguem a cena descrita. "
)

REFINE_SCENE_PROMPT = (
    "[TASK] Modify the character's head in Image 2 (Scene) to achieve a "
    "1:1 facial identity match with Image 1 (Avatar). "
    "Image order: (1) Avatar — MANDATORY identity reference for face, "
    "hair, age and proportions; (2) Scene — last. "
    "Do not use a raw photo as the face source of truth. "
    "The ONLY exception is clothes: copy the Scene costume, never the "
    "Avatar outfit. "
    "[FACIAL IDENTITY & STRUCTURE - MANDATORY] "
    "Redraw the face using exact anatomy, geometry, and features from the "
    "Avatar: face shape, cheeks, exact natural eye size and spacing "
    "(REDUCE if oversized), brow thickness, nose width, lips, skin tone, "
    "and apparent age. "
    "Hair (Immutable): Copy exact hair color, texture, length, parting, "
    "density, and volume. If forehead is visible or hair is thin in "
    "reference, maintain it. Do not add bangs or alter the haircut. "
    "Head Proportion: Match the Avatar head-to-body scale. If the Scene "
    "head is larger than the Avatar's relative to the torso, REDUCE it. "
    "Shoulders and chest must dominate. Do not reset pose or expression. "
    "[STYLE: TMT (Tell My Tale)] "
    "Face: Photorealistic digital painting, sharp camera-quality clarity "
    "with subtle artistic brushstrokes. More real than drawing. No raw "
    "photo collages, no porcelain/plastic skin. "
    "Body: 3D children's book illustration style (neck, shoulders, limbs). "
    "Smooth, continuous blend at the neckline. Body looks more like a "
    "stylized drawing than the face. "
    "Costume & Outfit: Preserve the exact costume, outfit, hat, boots, or "
    "historical/story accessories already present in the Scene. Do not "
    "replace it with the Avatar's clothes. "
    "Background & Lighting: Rich, saturated painted concept art with "
    "depth. Cinematic warm lighting, soft glow, rim light, magical "
    "atmosphere. "
    "[PRESERVATION & RESTRICTIONS] "
    "Preserve: Keep the exact scene composition, framing, camera angle, "
    "character pose, action, and emotional facial expression from the "
    "Scene. Do not reset to a neutral face. "
    "Age: keep the Avatar's apparent age (baby/toddler). Do not age the "
    "child up to 5-6 years. "
    "Prohibited: No cartoon, no anime, no chibi, no massive doll eyes, "
    "no bobbleheads, no Pixar/CGI look, no stock safari kid, no generic "
    "Disney/Pixar explorer boy, no salon hair if the Avatar hair is thin, "
    "no flat cel-shading, no text, no watermarks."
)

REFINE_IDENTITY_PROMPT = (
    "TAREFA CIRURGICA: voce recebe DUAS imagens em ordem. "
    "(1) o RECORTE do rosto da FOTO — unica fonte de verdade dos olhos, nariz, "
    "bochechas, queixo e do REALISMO do rosto (nao cole o close como colagem). "
    "(2) o PERSONAGEM a corrigir. "
    "Ajuste SO A CABECA: copie a GEOMETRIA e a qualidade de camera do recorte "
    "para o rosto (deve parecer uma foto, com tracos leves de desenho). Preserve corpo e "
    "roupa DESENHADOS, pose, enquadramento (meio corpo) e fundo. "
    f"{_SUBJECT_LOCK} {_GENERIC_FACE_LOCK} {_FACE_FIDELITY} {_HAIR_LOCK} {_WATERMARK_LOCK} "
    "Os olhos costumam estar maiores que na foto; REDUZA ate a "
    "mesma fracao do rosto. Se hesitar, diminua. NUNCA aumente. "
    "Se o rosto estiver mais gordo/cheio que a foto, REDUZA o volume das "
    "bochechas e a largura da cara ate a geometria do recorte. "
    "PROIBIDO colar o rosto fotografico como recorte. "
    "NAO invente franja. NAO 'corrija' tracos atipicos. "
    f"{_HEAD_PROPORTION} "
    "Devolva apenas o personagem corrigido."
)

REFINE_IDENTITY_AVATAR_PROMPT = (
    "TAREFA CIRURGICA: voce recebe DUAS imagens em ordem. "
    "(1) o RECORTE do rosto da FOTO — unica fonte de verdade dos olhos, nariz, "
    "bochechas, queixo e do REALISMO do rosto (nao cole o close como colagem). "
    "(2) o PERSONAGEM a corrigir. "
    "Ajuste SO A CABECA: copie a GEOMETRIA e a qualidade de camera do recorte "
    "para o rosto (deve parecer uma foto, com tracos leves de desenho). "
    "Preserve CORPO CGI 3D de filme infantil, roupa ilustrada, pose, "
    "enquadramento (meio corpo) e fundo. "
    f"{_SUBJECT_LOCK} {_GENERIC_FACE_LOCK} {_FACE_FIDELITY} {_HAIR_LOCK} {_WATERMARK_LOCK} "
    "Os olhos costumam estar maiores que na foto; REDUZA ate a "
    "mesma fracao do rosto. Se hesitar, diminua. NUNCA aumente. "
    "Se o rosto estiver mais gordo/cheio que a foto, REDUZA o volume das "
    "bochechas e a largura da cara ate a geometria do recorte. "
    "PROIBIDO colar o rosto fotografico como recorte. "
    "NAO invente franja. NAO 'corrija' tracos atipicos. "
    f"{_HEAD_PROPORTION} {_CGI_AVATAR_STYLE} "
    "Devolva apenas o personagem corrigido."
)


def build_scene_prompt(
    *,
    page: int,
    text: str,
    scene: str = "",
    expression: str | None = None,
    extras: str = "",
    child_name: str = "",
    shot: str = "",
    text_band: str = "",
) -> str:
    """Monta o prompt de cena para uma pagina do livro."""
    note = (scene or "").strip()
    caption = (text or "").strip()
    expr = normalize_expression(expression) if expression else infer_expression(caption, note)
    name_bit = f" O protagonista se chama {child_name}." if child_name else ""
    extras_bit = f" {extras.strip()}" if extras and extras.strip() else ""

    parts = [
        f"Pagina {page} da historia.{name_bit}",
        expression_directive(expr),
    ]
    if shot:
        parts.append(shot_directive(shot))
    if note:
        parts.append(
            "CENA (siga o enquadramento pedido com exatidao - close, plano detalhe, "
            f"cena dividida em paineis, ou outro, conforme descrito): {note}"
        )
    if caption:
        parts.append(
            "Texto da pagina (so para entender acao/sentimento, NAO escrever na "
            f'imagem): "{caption}".'
        )
    if extras_bit:
        parts.append(extras_bit.strip())
    parts.append(
        "Composicao QUADRADA (1:1), cena TMT de livro infantil: a crianca e "
        "identica a referencia (rosto realista deve parecer uma foto, qualidade de camera, "
        "com tracos leves de desenho; "
        "corpo desenhado; figurino da historia); cenario pintado rico com "
        "luz cinematografica, glow suave e contraluz; "
        "deixe uma area mais calma/limpa (ceu, agua, folhagem suave) para receber "
        "o texto impresso."
    )
    if text_band:
        parts.append(text_band_directive(text_band))
    parts.append(_PAGE_LOCK)
    parts.append(_STUDIO_IDENTITY_LOCK)
    return " ".join(parts)


ALPHABET_SCENE_EXTRAS = (
    "Pagina de alfabeto: destaque UM animal ou UMA fruta com a acao pedida na cena; "
    "inclua uma letra grande abstrata (madeira, espuma ou topiaria na forma da "
    "letra da pagina). A letra e so silhueta — NUNCA texto legivel, palavras, "
    "legendas, captions ou o nome do animal ou da fruta escrito na arte."
)

NAME_PAGE_SCENE_EXTRAS = (
    "Pagina de apresentacao do nome: a crianca e o unico foco principal. "
    "PROIBIDO incluir animal ou fruta em destaque. PROIBIDO desenhar letras, "
    "iniciais, palavras, placas, legendas, captions ou o nome da crianca na arte, "
    "mesmo como madeira, topiaria ou silhueta. A tipografia sera acrescentada "
    "depois, fora do gerador de imagem."
)

AMAZON_SCENE_EXTRAS = (
    "Cenario: floresta amazonica umida (rio, arvores, luz filtrada). "
    "PROIBIDO neve, gelo, savana africana, eucalipto australiano."
)

NUMBER_SCENE_EXTRAS = (
    "Pagina de numeros: inclua um numeral grande abstrato (madeira, espuma ou "
    "topiaria na forma do numero da pagina). O numeral e so silhueta — NUNCA "
    "texto legivel, palavras, legendas ou captions na arte. Se a nota pedir "
    "objetos contaveis, mostre a quantidade EXATA, bem separada e facil de contar; "
    "se pedir foco no tracado, NAO amontoe dezenas de objetos."
)

COLOR_SCENE_EXTRAS = (
    "Pagina de cores: uma cor dominante, alto contraste, agrupamento de objetos "
    "reais dessa cor. Nas paginas de mistura, mostre os dois pigmentos e o "
    "resultado no meio. NUNCA texto legivel, palavras, legendas, captions ou o "
    "nome da cor escrito na arte."
)

OPPOSITES_SCENE_EXTRAS = (
    "Pagina de opostos: os dois extremos (ou o extremo pedido) visiveis e obvios "
    "na cena — escala, direcao ou estado claros. NUNCA texto legivel, palavras, "
    "legendas ou captions na arte."
)

UNDERWATER_SCENE_EXTRAS = (
    "Cenario: oceano, recife de coral, areia, bolhas, luz filtrada pela superficie. "
    "UM animal marinho em destaque por pagina (exceto a pagina final, que junta varios). "
    "Animais amigaveis, sem sangue nem predacao. Tubarao, orca e agua-viva a distancia segura. "
    "A crianca e um mergulhador humano, NUNCA sereia. "
    "NUNCA texto legivel, palavras, legendas ou captions na arte."
)

KINGDOM_SCENE_EXTRAS = (
    "Cenario: reino fantastico de animais (floresta, rio, savana ou clareira "
    "conforme a pagina). "
    "UM animal em destaque por pagina (exceto a pagina do crocodilo e jacare, "
    "com os dois, e a pagina final, que junta varios). "
    "Animais amigaveis, sem sangue nem predacao. "
    "Leao, tigre, lobo, onca, crocodilo, jacare, hipopotamo e dinossauro "
    "a distancia segura. "
    "Rosto e cabelo do avatar visiveis, sem virar close de cabeca: a "
    "cabeca em proporcao com o tronco (menor que ombros e peito). "
    "Se houver chapeu, deixe-o na mao ou atras da cabeca, sem cobrir a franja. "
    "Olhos na mesma fracao do avatar, sem chibi. "
    "UM unico protagonista, mesma idade do avatar (bebe/toddler). "
    "PROIBIDO segundo rosto, cabeca flutuante, colagem do avatar na cena, "
    "brinco ou joia. "
    "NUNCA texto legivel, palavras, legendas ou captions na arte."
)


COSTUME_EXPLORER = (
    "FIGURINO TMT OBRIGATORIO (uma fantasia por livro, igual em todas as paginas): "
    "explorador infantil — camisa ou colete caqui, shorts ou calca safari, botas. "
    "Chapeu de explorador e binoculos ok. "
    "PROIBIDO copiar a roupa da foto (macacao, trator, jeans da foto) e a roupa do avatar-base."
)

# Placa de corpo: cenas prontas sem o rosto do cliente. O upload depois so cola a cara.
BODY_CHARACTER_PROMPT = (
    "TAREFA: gere UM retrato-base de CORPO (placa de figurino) para um livro "
    "infantil. NAO e uma crianca real. NAO copie foto. NAO invente celebridade.\n\n"
    "SUJEITO: uma unica crianca GENERICA de 3-5 anos, meio corpo (peito e ombros "
    "largos), de FRENTE, camera na altura dos olhos. Figurino de explorador "
    "infantil — camisa ou colete caqui, shorts ou calca safari, botas. "
    "Chapeu na MAO ou atras da cabeca — NUNCA cobrindo testa ou rosto.\n\n"
    "ROSTO PLACEHOLDER: simples, frontal, bem iluminado, simetrico, sem oculos, "
    "sem sombra dura. Sem tracos marcantes de pessoa famosa nem de banco de "
    "imagens. Esta cara SERA TROCADA depois por face-swap com a foto do cliente "
    "— precisa ser uma zona clara para colar o rosto.\n\n"
    "CORPO: ilustracao 3D de livro infantil TMT; cabeca MENOR que o tronco; "
    "proporcao natural; sem chibi, sem bobblehead. "
    "FUNDO: creme limpo, sem cenario narrativo, sem objetos a mais.\n\n"
    "PROIBIDO: texto, marca d'agua, segunda pessoa, close so de rosto, "
    "copiar roupa de foto, identidade de cliente."
)

BODY_PLATE_EXTRAS = (
    "PLACA DE CORPO (sem identidade de cliente): o protagonista e uma unica "
    "crianca GENERICA de 3-5 anos no figurino da historia. "
    "O rosto e um PLACEHOLDER frontal, claro, simetrico, sem tracos de "
    "celebridade — depois um face-swap cola o rosto do cliente nesta cara. "
    "Chapeu na mao ou atras da cabeca, sem cobrir testa. "
    "Cabeca menor que o tronco. UM so protagonista. "
    "PROIBIDO copiar foto, segundo rosto, cabeca flutuante, texto, marca d'agua."
)

COSTUME_ORCHARD = (
    "FIGURINO TMT OBRIGATORIO (uma fantasia por livro, igual em todas as paginas): "
    "aventureiro de pomar — roupa leve ilustrada de brincadeira. "
    "PROIBIDO copiar a roupa da foto ou do avatar-base."
)

COSTUME_STORYBOOK = (
    "FIGURINO TMT OBRIGATORIO (uma fantasia por livro, igual em todas as paginas): "
    "roupa ilustrada de livro infantil condizente com a cena. "
    "PROIBIDO copiar a roupa da foto ou do avatar-base."
)

COSTUME_DIVER = (
    "FIGURINO TMT OBRIGATORIO (uma fantasia por livro, igual em todas as paginas): "
    "mergulhador infantil — macaquinho ou roupa de mergulho ilustrada, mascara e "
    "nadadeiras leves, o mesmo em todas as paginas. "
    "PROIBIDO copiar a roupa da foto ou do avatar-base. "
    "PROIBIDO transformar a crianca em sereia."
)

_THEME_COSTUMES: dict[str, str] = {
    "adventure": COSTUME_EXPLORER,
    "princess": (
        "FIGURINO TMT OBRIGATORIO: vestido ou traje de conto de fadas ilustrado, "
        "o mesmo em todas as paginas. PROIBIDO copiar a roupa da foto ou do avatar-base."
    ),
    "superhero": (
        "FIGURINO TMT OBRIGATORIO: traje de heroi infantil ilustrado (capa leve), "
        "o mesmo em todas as paginas. PROIBIDO copiar a roupa da foto ou do avatar-base."
    ),
    "space": (
        "FIGURINO TMT OBRIGATORIO: astronauta infantil leve ilustrado, "
        "o mesmo em todas as paginas. PROIBIDO copiar a roupa da foto ou do avatar-base."
    ),
    "underwater": (
        "FIGURINO TMT OBRIGATORIO: marinheiro ou mergulhador infantil ilustrado, "
        "o mesmo em todas as paginas. PROIBIDO copiar a roupa da foto ou do avatar-base."
    ),
    "dinosaurs": COSTUME_EXPLORER,
    "fantasy": (
        "FIGURINO TMT OBRIGATORIO: traje de conto de fadas ilustrado, "
        "o mesmo em todas as paginas. PROIBIDO copiar a roupa da foto ou do avatar-base."
    ),
    "birthday": (
        "FIGURINO TMT OBRIGATORIO: roupa de festa ilustrada, "
        "a mesma em todas as paginas. PROIBIDO copiar a roupa da foto ou do avatar-base."
    ),
    "christmas": (
        "FIGURINO TMT OBRIGATORIO: roupa natalina ilustrada, "
        "a mesma em todas as paginas. PROIBIDO copiar a roupa da foto ou do avatar-base."
    ),
    "easter": (
        "FIGURINO TMT OBRIGATORIO: roupa primaveril ilustrada, "
        "a mesma em todas as paginas. PROIBIDO copiar a roupa da foto ou do avatar-base."
    ),
    "childrens_day": COSTUME_STORYBOOK,
    "mothers_day": COSTUME_STORYBOOK,
    "fathers_day": COSTUME_STORYBOOK,
    "new_year": COSTUME_STORYBOOK,
}


def costume_extras_for_template(template_id: str | None) -> str:
    """Figurino TMT do livro de catalogo. Vazio se o template nao tiver fantasia propria."""
    if template_id in {"alfabeto_amazonia", "reino_animais"}:
        return COSTUME_EXPLORER
    if template_id == "alfabeto_frutas":
        return COSTUME_ORCHARD
    if template_id == "mergulho_mar":
        return COSTUME_DIVER
    if template_id in {"numeros_1_15", "cores_basicas", "grande_pequeno"}:
        return COSTUME_STORYBOOK
    return ""


def costume_extras_for_theme(theme: str | None) -> str:
    """Figurino TMT para historia inventada, a partir do tema do projeto."""
    if not theme:
        return COSTUME_EXPLORER
    return _THEME_COSTUMES.get(theme.strip().lower(), COSTUME_STORYBOOK)


# --------------------------------------------------------------------------- #
# Ficha do personagem (3 imagens no inicio do ebook)
# --------------------------------------------------------------------------- #
CHARACTER_SHEET_PROMPT = (
    "FICHA DE PERSONAGEM (turnaround). TAREFA: uma unica imagem com a MESMA "
    "crianca em 2 ou 3 poses lado a lado — FRENTE, TRES-QUARTOS e (se couber) "
    "PERFIL. Roupa ilustrada SIMPLES, a do avatar (NAO o figurino da historia). "
    "Fundo creme limpo, sem cenario narrativo, sem texto, sem moldura. "
    "Identidade 1:1 da foto/avatar em TODAS as poses: mesmo rosto, cabelo, "
    "proporcoes, idade. Corpo desenhado, rosto pintura fotorrealista TMT. "
    f"{_SUBJECT_LOCK} {_GENERIC_FACE_LOCK} {_FACE_FIDELITY} {_HEAD_PROPORTION} "
    f"{_HAIR_LOCK} {_HYBRID_STYLE} {_WATERMARK_LOCK} "
    "SAIDA: uma ficha limpa de identidade, nao uma cena."
)

EXPRESSION_SHEET_PROMPT = (
    "GRADE DE EXPRESSOES 2x2. TAREFA: uma unica imagem com QUATRO retratos da "
    "MESMA crianca, mesma identidade, mesma roupa simples do avatar, fundo creme. "
    "Ordem: canto superior esquerdo ALEGRIA; superior direito SURPRESA; "
    "inferior esquerdo DETERMINACAO; inferior direito CALMA. "
    "As QUATRO caras tem de ser BEM DISTINTAS e LEGIVEIS (sorriso aberto / "
    "boca em O / queixo firme / calma aconchegante). Mude sobrancelhas, boca, "
    "olhar e um pouco a pose da cabeca. NAO o tamanho dos olhos nem o "
    "penteado. Sem texto, sem legendas, sem moldura. "
    f"{_SUBJECT_LOCK} {_GENERIC_FACE_LOCK} {_FACE_FIDELITY} {_HEAD_PROPORTION} "
    f"{_HAIR_LOCK} {_HYBRID_STYLE} {_WATERMARK_LOCK} "
    "SAIDA: grade 2x2 de expressoes, nao uma cena narrativa."
)


def costume_lock_prompt(costume: str) -> str:
    """Prompt do retrato de figurino (corpo inteiro, fundo creme)."""
    figurino = (costume or "").strip() or COSTUME_STORYBOOK
    return (
        "FIGURINO LOCK. TAREFA: um retrato de CORPO INTEIRO desta crianca com o "
        "figurino da HISTORIA, pose neutra-alegre, de frente, fundo creme. "
        "Este arquivo e a referencia de ROUPA de todas as paginas — copie o "
        "figurino da descricao, NAO a roupa da foto nem a do avatar. "
        f"FIGURINO: {figurino} "
        "Identidade 1:1 da foto/avatar (rosto, cabelo, idade, proporcoes). "
        "Sem cenario narrativo, sem texto, sem moldura. "
        f"{_SUBJECT_LOCK} {_GENERIC_FACE_LOCK} {_FACE_FIDELITY} {_HEAD_PROPORTION} "
        f"{_HAIR_LOCK} {_HYBRID_STYLE} {_WATERMARK_LOCK} "
        "SAIDA: um personagem de corpo inteiro no figurino da historia."
    )


def scene_extras_for_template(template_id: str | None) -> str:
    """Extras de cena do ebook conforme o livro de catálogo (inclui figurino TMT)."""
    if not template_id:
        return ""
    from app.story_templates import (
        ALPHABET_TEMPLATE_IDS,
        COLOR_TEMPLATE_IDS,
        NUMBER_TEMPLATE_IDS,
        OPPOSITES_TEMPLATE_IDS,
    )

    extras = ""
    if template_id in ALPHABET_TEMPLATE_IDS:
        extras = ALPHABET_SCENE_EXTRAS
        if template_id == "alfabeto_amazonia":
            extras = f"{extras} {AMAZON_SCENE_EXTRAS}"
    elif template_id in NUMBER_TEMPLATE_IDS:
        extras = NUMBER_SCENE_EXTRAS
    elif template_id in COLOR_TEMPLATE_IDS:
        extras = COLOR_SCENE_EXTRAS
    elif template_id in OPPOSITES_TEMPLATE_IDS:
        extras = OPPOSITES_SCENE_EXTRAS
    elif template_id == "mergulho_mar":
        extras = UNDERWATER_SCENE_EXTRAS
    elif template_id == "reino_animais":
        extras = KINGDOM_SCENE_EXTRAS
    costume = costume_extras_for_template(template_id)
    if extras and costume:
        return f"{extras} {costume}"
    return extras or costume


def name_scene_extras_for_template(template_id: str | None) -> str:
    """Extras da pagina de nome, sem instrucoes de animal/letra do alfabeto."""
    extras = [NAME_PAGE_SCENE_EXTRAS]
    if template_id == "alfabeto_amazonia":
        extras.append(AMAZON_SCENE_EXTRAS)
    costume = costume_extras_for_template(template_id)
    if costume:
        extras.append(costume)
    return " ".join(extras)


def scene_extras_for_body_plate(template_id: str | None) -> str:
    """Extras de cena para chapa sem o rosto do cliente (corpo + placeholder)."""
    extras = scene_extras_for_template(template_id)
    if extras:
        return f"{extras} {BODY_PLATE_EXTRAS}"
    return BODY_PLATE_EXTRAS


def preview_cover_prompt(
    *,
    title: str,
    child_name: str | None,
    theme: str | None,
    language: str = "pt-BR",
) -> str:
    """Prompt OpenAI para a capa da prévia (perfil mestre + landing)."""
    name = (child_name or "").strip()
    theme_bit = (theme or "").strip()
    is_en = (language or "").lower().startswith("en")
    is_es = (language or "").lower().startswith("es")
    locks = f" {_STUDIO_IDENTITY_LOCK} {_STUDIO_TYPOGRAPHY_LOCK} {_STUDIO_ANIMAL_LOCK}"
    if is_en:
        who = f" featuring {name}" if name else ""
        theme_line = f" Theme mood: {theme_bit}." if theme_bit else ""
        return (
            f"Premium children's book COVER{who}. Exact title text: '{title}'.{theme_line} "
            "Front-facing square cover 20x20 cm look, soft rounded book corners, hero large and "
            "centered, warm cinematic light, rich illustrated background, commercial catalog "
            "quality. Print the exact title in locked rounded sans-serif navy #172A3A, fully "
            "legible, inside the safe margin. No barcode, no photo frame, no watermark, no "
            "extra text. Same face as the photo/avatar reference." + locks
        )
    if is_es:
        who = f" con {name}" if name else ""
        theme_line = f" Ambiente del tema: {theme_bit}." if theme_bit else ""
        return (
            f"Portada premium de libro infantil{who}. Título exacto: '{title}'.{theme_line} "
            "Portada cuadrada frontal 20x20 cm, esquinas suaves del libro físico, héroe grande "
            "y centrado, luz cinematográfica cálida, fondo ilustrado rico, calidad de catálogo. "
            "Escribe el título exacto en tipografía rounded sans-serif navy #172A3A, legible, "
            "dentro del margen de seguridad. Sin código de barras, marco, marca de agua ni texto "
            "extra. Misma cara que la foto/avatar." + locks
        )
    who = f" com {name}" if name else ""
    theme_line = f" Clima do tema: {theme_bit}." if theme_bit else ""
    return (
        f"Capa premium de livro infantil{who}. Titulo exato: '{title}'.{theme_line} "
        "Capa de frente, quadrada 20x20 cm, cantos suaves do livro fisico, heroi grande e "
        "central, luz cinematografica quente, cenario ilustrado rico, qualidade de catalogo. "
        "Escreva o titulo exato na tipografia rounded sans-serif navy #172A3A, totalmente "
        "legivel, dentro da margem de seguranca. Sem codigo de barras, moldura, marca d'agua "
        "nem texto extra. Mesmo rosto da foto/avatar de referencia." + locks
    )


def preview_open_book_prompt(
    *,
    title: str,
    page_text: str,
    language: str = "pt-BR",
) -> str:
    """Prompt do livro aberto da prévia (duas páginas 20×20 lado a lado)."""
    stanza = " ".join((page_text or "").strip().split())[:320]
    is_en = (language or "").lower().startswith("en")
    is_es = (language or "").lower().startswith("es")
    locks = f" {_STUDIO_IDENTITY_LOCK} {_STUDIO_TYPOGRAPHY_LOCK}"
    if is_en:
        return (
            f"Photoreal product shot of an OPEN square hardcover children's book. Title '{title}'. "
            "Two square 20x20 cm pages side by side (~2:1), same size, natural center gutter, "
            "no stretching. Left page: short warm stanza (2-5 lines) far from the gutter with "
            f"matching illustration. Right page: natural continuation and illustration. Stanza "
            f"to use: «{stanza}». Same locked rounded sans-serif navy typography as the cover. "
            "Same child identity as the avatar/photo. Book fills most of the frame, studio light, "
            "no collage, no watermark." + locks
        )
    if is_es:
        return (
            f"Foto de producto de un libro infantil de tapa dura ABIERTO. Título '{title}'. "
            "Dos páginas cuadradas 20x20 cm lado a lado (~2:1), mismo tamaño, lomo central "
            "natural, sin estirar. Página izquierda: estrofa corta (2-5 líneas) lejos del "
            f"pliegue con ilustración. Página derecha: continuación e ilustración. Estrofa: "
            f"«{stanza}». Misma tipografía rounded sans-serif navy de la portada. Misma "
            "identidad del niño. El libro ocupa casi todo el cuadro. Sin collage ni marca de agua."
            + locks
        )
    return (
        f"Foto de produto de um livro infantil de capa dura ABERTO. Titulo '{title}'. "
        "Duas paginas quadradas 20x20 cm lado a lado (~2:1), mesmo tamanho, dobra central "
        "natural, sem esticar. Pagina esquerda: estrofe curta (2 a 5 linhas) longe da dobra "
        f"com ilustracao. Pagina direita: continuacao e ilustracao. Estrofe: «{stanza}». "
        "Mesma tipografia rounded sans-serif navy da capa. Mesma identidade da crianca. "
        "O livro ocupa quase todo o quadro. Sem collage, sem marca d'agua." + locks
    )


def preview_in_hand_prompt(*, language: str = "pt-BR") -> str:
    """Prompt da cena com a criança da foto original segurando o livro."""
    is_en = (language or "").lower().startswith("en")
    is_es = (language or "").lower().startswith("es")
    locks = f" {_STUDIO_IDENTITY_LOCK}"
    if is_en:
        return (
            "Photoreal lifestyle photo: the SAME child from the ORIGINAL PHOTO reference "
            "holding or reading their hardcover square children's book. Warm home light, "
            "shallow depth of field, pride and joy. The FIRST reference image is the BOOK "
            "COVER — print that exact cover art on the physical book; do not reinvent the "
            "cover. Extra references include the child's photo — use that face, not a generic "
            "kid. Natural skin and hands, no illustration style on the person. Square crop, "
            "marketing quality." + locks
        )
    if is_es:
        return (
            "Foto lifestyle fotorrealista: el MISMO niño de la FOTO ORIGINAL sostiene o lee "
            "su libro infantil cuadrado de tapa dura. Luz hogareña, orgullo y alegría. La "
            "PRIMERA imagen de referencia es la PORTADA — imprímela exactamente en el libro "
            "físico; no reinventes la portada. Las referencias extra incluyen la foto del "
            "niño — usa esa cara, no un niño genérico. Piel y manos reales. Recorte cuadrado."
            + locks
        )
    return (
        "Foto lifestyle fotorrealista: a MESMA crianca da FOTO ORIGINAL segura ou le o "
        "proprio livro infantil quadrado de capa dura. Luz de casa, carinho e orgulho. A "
        "PRIMEIRA imagem de referencia e a CAPA — imprima exatamente essa arte no livro "
        "fisico; nao reinvente a capa. As referencias extras incluem a foto da crianca — "
        "use esse rosto, nao uma crianca generica. Pele e maos reais, sem estilo ilustrado "
        "na pessoa. Enquadramento quadrado, qualidade de catalogo." + locks
    )
