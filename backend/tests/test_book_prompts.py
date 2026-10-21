"""Testes do modulo de prompts do livro (avatar + expressao + cena)."""

from app.ai_clients.book_prompts import (
    ALPHABET_SCENE_EXTRAS,
    AVATAR_PROMPT,
    AVATAR_STYLE,
    BODY_CHARACTER_PROMPT,
    BODY_PLATE_EXTRAS,
    COLOR_SCENE_EXTRAS,
    NUMBER_SCENE_EXTRAS,
    OPPOSITES_SCENE_EXTRAS,
    REFINE_IDENTITY_AVATAR_PROMPT,
    REFINE_IDENTITY_PROMPT,
    REFINE_SCENE_PROMPT,
    SCENE_GEN_PREFIX,
    build_scene_prompt,
    costume_extras_for_template,
    costume_extras_for_theme,
    expression_directive,
    infer_expression,
    name_scene_extras_for_template,
    normalize_expression,
    scene_extras_for_body_plate,
    scene_extras_for_template,
)


def test_normalize_expression_aliases():
    assert normalize_expression("feliz") == "alegria"
    assert normalize_expression("medo") == "medo_gentil"
    assert normalize_expression("Tristeza") == "tristeza_leve"
    assert normalize_expression("empolgado") == "animacao"
    assert normalize_expression("timido") == "vergonha"
    assert normalize_expression("xyz") == "alegria"


def test_infer_expression_from_text():
    assert infer_expression("Matteo fica muito triste") == "tristeza_leve"
    assert infer_expression("olhar atento e surpreso") == "surpresa"
    assert infer_expression("decidem construir uma ponte") == "determinacao"
    assert infer_expression("ficou com vergonha e corado") == "vergonha"
    assert infer_expression("pulando de empolgacao") == "animacao"


def test_build_scene_prompt_includes_expression_and_identity_hooks():
    prompt = build_scene_prompt(
        page=3,
        text="Matteo abraca o porquinho.",
        scene="Matteo sorridente com o porquinho.",
        expression="alegria",
        child_name="Matteo",
    )
    assert "Pagina 3" in prompt
    assert "Matteo" in prompt
    assert "alegria" in prompt
    assert "EXPRESSAO FACIAL OBRIGATORIA" in prompt
    assert "LEGIVEL" in prompt
    assert "NAO escrever na imagem" in prompt
    assert "NAO mude identidade" in prompt


def test_build_scene_prompt_infers_different_expressions():
    sad = build_scene_prompt(page=1, text="A menina ficou triste e sozinha.")
    happy = build_scene_prompt(page=2, text="Ela brinca feliz na festa.")
    surprise = build_scene_prompt(page=3, text="De repente, uau, que surpresa!")
    assert "tristeza_leve" in sad
    assert "alegria" in happy
    assert "surpresa" in surprise
    assert sad != happy


def test_avatar_prompt_face_fidelity_and_head():
    assert "character_ref" in AVATAR_PROMPT
    assert "mais proximo possivel" in AVATAR_PROMPT or "100% reconhecivel" in AVATAR_PROMPT
    assert "ROSTO REALISTA" in AVATAR_PROMPT
    assert "parecer uma foto" in AVATAR_PROMPT
    assert "qualidade de camera" in AVATAR_PROMPT
    assert "CGI 3D" in AVATAR_PROMPT
    assert "filme infantil" in AVATAR_PROMPT
    assert "CORPO" in AVATAR_PROMPT
    assert "ESTILO TMT" not in AVATAR_PROMPT
    assert "PROPORCAO DA CABECA" in AVATAR_PROMPT or "proporcao NATURAL" in AVATAR_PROMPT
    assert "sem aumentar" in AVATAR_PROMPT.lower() or "identica a da foto" in AVATAR_PROMPT.lower()
    assert "chibi" in AVATAR_PROMPT.lower() or "PROIBIDO" in AVATAR_PROMPT
    assert "NEUTRA-ALEGRE" in AVATAR_PROMPT or "neutra" in AVATAR_PROMPT.lower()
    assert "NAO copie a foto original" in AVATAR_PROMPT or "NAO cole" in AVATAR_PROMPT
    assert "PROIBIDO inventar franja" in AVATAR_PROMPT or "NAO invente" in AVATAR_PROMPT
    assert "tracos atipicos" in AVATAR_PROMPT
    assert "marca d'agua" in AVATAR_PROMPT.lower() or "marca d'agua" in AVATAR_PROMPT
    assert "ANTI-ROSTO-GENERICO" in AVATAR_PROMPT
    assert "IDENTITY LOCK" in AVATAR_PROMPT
    assert "Ignore adultos" in AVATAR_PROMPT
    assert "sorriso largo de banco de imagens" in AVATAR_PROMPT
    assert "fracao do rosto" in AVATAR_PROMPT
    assert "ACIMA do estilo" in AVATAR_PROMPT or "ACIMA DO ESTILO" in AVATAR_PROMPT
    assert "DIMINUA" in AVATAR_PROMPT or "NUNCA aumente" in AVATAR_PROMPT
    assert "FORMATO DO ROSTO" in AVATAR_PROMPT
    assert "engordando" in AVATAR_PROMPT
    assert "mais gorda" in AVATAR_PROMPT or "mais gordo" in AVATAR_PROMPT
    assert "REDUZA o volume das bochechas" in AVATAR_PROMPT
    assert "parecer uma foto" in AVATAR_STYLE
    assert "CGI" in AVATAR_STYLE


def test_refine_identity_avatar_keeps_cgi():
    assert "CORPO CGI 3D" in REFINE_IDENTITY_AVATAR_PROMPT
    assert "parecer uma foto" in REFINE_IDENTITY_AVATAR_PROMPT
    assert "qualidade de camera" in REFINE_IDENTITY_AVATAR_PROMPT
    assert "ROSTO REALISTA" in REFINE_IDENTITY_AVATAR_PROMPT
    assert "SO A CABECA" in REFINE_IDENTITY_AVATAR_PROMPT
    assert "RECORTE" in REFINE_IDENTITY_AVATAR_PROMPT
    assert "nao cole o close" in REFINE_IDENTITY_AVATAR_PROMPT.lower()
    assert "REDUZA o volume das bochechas" in REFINE_IDENTITY_AVATAR_PROMPT
    assert "NAO fotorealize" not in REFINE_IDENTITY_AVATAR_PROMPT


def test_refine_identity_orders_photo_first():
    assert "FOTO" in REFINE_IDENTITY_PROMPT
    assert "fonte de verdade" in REFINE_IDENTITY_PROMPT.lower()
    assert "ROSTO REALISTA" in REFINE_IDENTITY_PROMPT
    assert "parecer uma foto" in REFINE_IDENTITY_PROMPT
    assert "qualidade de camera" in REFINE_IDENTITY_PROMPT
    assert "tracos leves" in REFINE_IDENTITY_PROMPT
    assert "SO A CABECA" in REFINE_IDENTITY_PROMPT
    assert "roupa DESENHADOS" in REFINE_IDENTITY_PROMPT
    assert "ESTILO CGI 3D DE FILME INFANTIL OBRIGATORIO" not in REFINE_IDENTITY_PROMPT
    assert "pele CGI" not in REFINE_IDENTITY_PROMPT
    assert "filme infantil" not in REFINE_IDENTITY_PROMPT
    assert "MESMO idioma ilustrado" not in REFINE_IDENTITY_PROMPT
    assert "NAO invente franja" in REFINE_IDENTITY_PROMPT
    assert "tracos atipicos" in REFINE_IDENTITY_PROMPT
    assert "ANTI-ROSTO-GENERICO" in REFINE_IDENTITY_PROMPT
    assert "Ignore adultos" in REFINE_IDENTITY_PROMPT
    assert "SUBSTITUA pela qualidade fotografica" not in REFINE_IDENTITY_PROMPT
    assert "2D nitida" not in REFINE_IDENTITY_PROMPT
    assert "fracao do rosto" in REFINE_IDENTITY_PROMPT
    assert "REDUZA" in REFINE_IDENTITY_PROMPT
    assert "TAREFA CIRURGICA" in REFINE_IDENTITY_PROMPT
    assert (
        "fonte de verdade" in REFINE_IDENTITY_PROMPT.lower()
        or "UNICA fonte" in REFINE_IDENTITY_PROMPT
    )
    assert "RECORTE" in REFINE_IDENTITY_PROMPT
    assert "mais gordo" in REFINE_IDENTITY_PROMPT
    assert "REDUZA o volume das bochechas" in REFINE_IDENTITY_PROMPT
    assert (
        "nao cole o close" in REFINE_IDENTITY_PROMPT.lower()
        or "nao copie o close" in REFINE_IDENTITY_PROMPT.lower()
    )


def test_scene_and_style_are_hybrid_illustration():
    assert "ROSTO REALISTA" in SCENE_GEN_PREFIX
    assert "ESTILO TMT" in SCENE_GEN_PREFIX
    assert "mais DESENHO" in SCENE_GEN_PREFIX
    assert "parecer uma foto" in SCENE_GEN_PREFIX
    assert "qualidade de camera" in SCENE_GEN_PREFIX
    assert "airbrush" in SCENE_GEN_PREFIX
    assert "tracos leves" in SCENE_GEN_PREFIX
    assert "MESMA ROUPA da referencia" not in SCENE_GEN_PREFIX
    assert "MESMA ROUPA da referencia" not in REFINE_SCENE_PROMPT
    assert "figurino" in SCENE_GEN_PREFIX.lower()
    assert "MESMO idioma ilustrado" not in SCENE_GEN_PREFIX
    assert "ESTILO CGI 3D DE FILME INFANTIL OBRIGATORIO" not in SCENE_GEN_PREFIX
    assert "ESTILO CGI 3D DE FILME INFANTIL OBRIGATORIO" not in REFINE_SCENE_PROMPT
    assert "pele CGI" not in SCENE_GEN_PREFIX
    assert "filme infantil" not in SCENE_GEN_PREFIX
    assert "filme infantil" not in REFINE_SCENE_PROMPT
    assert "CGI 3D" not in SCENE_GEN_PREFIX
    assert "PINTURA REALISTA" not in SCENE_GEN_PREFIX
    assert "2D nitida" not in SCENE_GEN_PREFIX
    assert "PROIBIDO Pixar" not in SCENE_GEN_PREFIX
    assert "fracao do rosto" in SCENE_GEN_PREFIX
    assert "ACIMA DO ESTILO" in SCENE_GEN_PREFIX or "ACIMA do estilo" in SCENE_GEN_PREFIX
    assert "MENOR que o tronco" in SCENE_GEN_PREFIX
    assert "DIMINUA a cabeca" in SCENE_GEN_PREFIX
    assert "REDUCE" in REFINE_SCENE_PROMPT
    assert "head-to-body" in REFINE_SCENE_PROMPT
    assert "If the Scene head is larger" in REFINE_SCENE_PROMPT
    assert "1:1 facial identity" in REFINE_SCENE_PROMPT
    assert "painted concept art" in REFINE_SCENE_PROMPT
    assert "stylized drawing" in REFINE_SCENE_PROMPT
    assert "Preserve the exact costume" in REFINE_SCENE_PROMPT
    assert "Do not replace it with the Avatar's clothes" in REFINE_SCENE_PROMPT
    assert "MANDATORY identity" in REFINE_SCENE_PROMPT
    assert "Image 1 (Avatar)" in REFINE_SCENE_PROMPT
    assert "Do not use a raw photo as the face source of truth" in REFINE_SCENE_PROMPT
    assert "FONTE DO ROSTO" in SCENE_GEN_PREFIX
    assert "safari-kid" in SCENE_GEN_PREFIX or "safari" in SCENE_GEN_PREFIX
    assert "bebe/toddler" in SCENE_GEN_PREFIX
    assert "stock safari kid" in REFINE_SCENE_PROMPT
    assert "apparent age" in REFINE_SCENE_PROMPT
    assert "When a real photo is attached first" not in REFINE_SCENE_PROMPT
    scene = build_scene_prompt(page=1, text="Matteo olha a floresta.")
    assert "cena TMT de livro infantil" in scene
    assert "luz cinematografica" in scene
    assert "rosto realista" in scene
    assert "parecer uma foto" in scene
    assert "qualidade de camera" in scene
    assert "tracos leves" in scene
    assert "figurino da historia" in scene
    assert "CGI 3D de filme infantil" not in scene
    assert "cena REALISTA" not in scene
    assert "mesmo estilo de pintura digital" not in scene


def test_scene_keeps_emotion_separate_from_identity():
    assert "expressao NEUTRA" in SCENE_GEN_PREFIX or "NAO a copie" in SCENE_GEN_PREFIX
    assert "VENCE o avatar" in SCENE_GEN_PREFIX
    assert "pose dinamicos" in SCENE_GEN_PREFIX
    assert "emotional facial expression" in REFINE_SCENE_PROMPT
    assert "Do not reset to a neutral face" in REFINE_SCENE_PROMPT


def test_alphabet_extras_forbid_readable_text():
    prompt = build_scene_prompt(
        page=15,
        text="O macaco pula de galho em galho.",
        scene="Matteo vendo um macaco-prego pulando de galho em galho; letra grande abstrata M.",
        extras=ALPHABET_SCENE_EXTRAS,
        child_name="Matteo",
    )
    assert "Pagina de alfabeto" in prompt
    assert "NUNCA texto legivel" in prompt
    assert "letra grande abstrata M" in prompt
    assert "animal ou UMA fruta" in prompt


def test_number_color_opposites_extras():
    n = build_scene_prompt(page=3, text="O um e um pauzinho.", extras=NUMBER_SCENE_EXTRAS)
    assert "Pagina de numeros" in n
    assert "quantidade EXATA" in n
    c = build_scene_prompt(page=4, text="O vermelho e o morango.", extras=COLOR_SCENE_EXTRAS)
    assert "Pagina de cores" in c
    assert "alto contraste" in c
    o = build_scene_prompt(page=2, text="Grande e o elefante.", extras=OPPOSITES_SCENE_EXTRAS)
    assert "Pagina de opostos" in o
    assert "extremos" in o


def test_scene_extras_for_template():
    amazonia = scene_extras_for_template("alfabeto_amazonia")
    frutas = scene_extras_for_template("alfabeto_frutas")
    assert "animal ou UMA fruta" in amazonia
    assert "animal ou UMA fruta" in frutas
    assert "floresta amazonica umida" in amazonia
    assert "PROIBIDO neve" in amazonia
    assert "savana africana" in amazonia
    assert "eucalipto" in amazonia
    assert "floresta amazonica umida" not in frutas
    assert "PROIBIDO neve" not in frutas
    assert "explorador" in amazonia
    assert "caqui" in amazonia
    assert "PROIBIDO copiar a roupa da foto" in amazonia
    assert "aventureiro de pomar" in frutas
    assert "explorador" not in frutas
    assert "roupa ilustrada de livro infantil" in scene_extras_for_template("numeros_1_15")
    assert "Pagina de numeros" in scene_extras_for_template("numeros_1_15")
    assert "Pagina de cores" in scene_extras_for_template("cores_basicas")
    assert "Pagina de opostos" in scene_extras_for_template("grande_pequeno")
    mergulho = scene_extras_for_template("mergulho_mar")
    assert "oceano" in mergulho
    assert "mergulhador" in mergulho
    assert "NUNCA sereia" in mergulho
    reino = scene_extras_for_template("reino_animais")
    assert "reino fantastico de animais" in reino
    assert "crocodilo e jacare" in reino
    assert "distancia segura" in reino
    assert "cabelo do avatar visiveis" in reino
    assert "sem virar close" in reino
    assert "proporcao com o tronco" in reino
    assert "sem cobrir a franja" in reino
    assert "sem chibi" in reino
    assert "bebe/toddler" in reino
    assert "cabeca flutuante" in reino
    assert "brinco" in reino
    assert "explorador" in reino
    assert "letra grande abstrata" not in reino
    assert "floresta amazonica umida" not in reino
    assert "PROIBIDO neve" not in reino
    assert scene_extras_for_template("nave_vermelha") == ""
    assert scene_extras_for_template(None) == ""


def test_body_character_prompt_is_a_placeholder_face():
    assert "PLACEHOLDER" in BODY_CHARACTER_PROMPT
    assert "face-swap" in BODY_CHARACTER_PROMPT
    assert "explorador" in BODY_CHARACTER_PROMPT
    assert "NAO copie foto" in BODY_CHARACTER_PROMPT
    assert "3-5 anos" in BODY_CHARACTER_PROMPT
    assert "Chapeu na MAO" in BODY_CHARACTER_PROMPT


def test_scene_extras_for_body_plate_keeps_kingdom_and_marks_placeholder():
    extras = scene_extras_for_body_plate("reino_animais")
    assert "reino fantastico de animais" in extras
    assert "PLACEHOLDER" in extras
    assert "explorador" in extras
    assert BODY_PLATE_EXTRAS in extras
    assert scene_extras_for_body_plate(None) == BODY_PLATE_EXTRAS


def test_name_page_prompt_reserves_left_side_without_generated_letters():
    extras = name_scene_extras_for_template("alfabeto_amazonia")
    prompt = build_scene_prompt(
        page=2,
        text="Matteo se soletra assim: M · A · T · T · E · O.",
        scene="Matteo no lado direito da floresta; rio calmo a esquerda.",
        extras=extras,
        child_name="Matteo",
        shot="wide",
        text_band="left",
    )

    assert "lado esquerdo" in prompt
    assert "inteiramente no lado oposto" in prompt
    assert "PROIBIDO desenhar letras" in prompt
    assert "destaque UM animal" not in prompt
    assert "floresta amazonica umida" in prompt
    assert "explorador infantil" in prompt


def test_costume_extras_for_template_and_theme():
    assert "explorador" in costume_extras_for_template("alfabeto_amazonia")
    assert "explorador" in costume_extras_for_template("reino_animais")
    assert "aventureiro de pomar" in costume_extras_for_template("alfabeto_frutas")
    assert "mergulhador infantil" in costume_extras_for_template("mergulho_mar")
    assert "sereia" in costume_extras_for_template("mergulho_mar")
    assert costume_extras_for_template(None) == ""
    assert "explorador" in costume_extras_for_theme("adventure")
    assert "vestido" in costume_extras_for_theme("princess")
    assert "astronauta" in costume_extras_for_theme("space")
    assert "explorador" in costume_extras_for_theme(None)


def test_expression_directive():
    d = expression_directive("curiosidade")
    assert "curiosidade" in d
    assert "sobrancelhas" in d
    assert "NAO mude identidade" in d
    assert "PROIBIDO copiar a expressao neutra" in d
    assert "LEGIVEL" in d
    assert "pose" in d.lower()
    assert "NAO mude o TAMANHO dos olhos" in d
    assert "fracao do rosto" in d
    happy = expression_directive("alegria")
    assert "sorriso ABERTO" in happy
    assert "olhos vivos e brilhantes" not in happy
    assert "olhos bem abertos" not in expression_directive("animacao")
    assert "corpo em movimento" in expression_directive("animacao")


def test_build_scene_prompt_uses_shot_and_text_band():
    prompt = build_scene_prompt(
        page=2,
        text="Matteo corre.",
        scene="CENA_VISUAL_DO_BRIEF",
        expression="determinacao",
        shot="close",
        text_band="top",
        child_name="Matteo",
    )
    assert "CENA_VISUAL_DO_BRIEF" in prompt
    assert "determinacao" in prompt
    assert "ENQUADRAMENTO OBRIGATORIO" in prompt
    assert "'close'" in prompt
    assert "FAIXA DE TEXTO" in prompt
    assert "superior" in prompt


def test_normalize_shot_and_text_band():
    from app.ai_clients.book_prompts import (
        identity_shot,
        normalize_shot,
        normalize_text_band,
        shot_directive,
    )

    assert normalize_shot("closeup") == "close"
    assert normalize_shot("plano detalhe") == "detail"
    assert normalize_shot("xyz") == "medium"
    assert "quinto" in shot_directive("medium")
    assert "corpo inteiro no fundo" in shot_directive("medium")
    assert identity_shot("wide") == "medium"
    assert identity_shot("wide", layout="name") == "wide"
    assert identity_shot("close") == "close"
    assert normalize_text_band("TOP") == "top"
    assert normalize_text_band("LEFT") == "left"
    assert normalize_text_band("right") == "right"
    assert normalize_text_band("nope") == "bottom"


def test_character_bible_prompts():
    from app.ai_clients.book_prompts import (
        CHARACTER_SHEET_PROMPT,
        EXPRESSION_SHEET_PROMPT,
        costume_lock_prompt,
    )

    assert "FICHA DE PERSONAGEM" in CHARACTER_SHEET_PROMPT
    assert "TRES-QUARTOS" in CHARACTER_SHEET_PROMPT
    assert "GRADE DE EXPRESSOES" in EXPRESSION_SHEET_PROMPT
    assert "BEM DISTINTAS" in EXPRESSION_SHEET_PROMPT
    assert "LEGIVEIS" in EXPRESSION_SHEET_PROMPT
    lock = costume_lock_prompt("capa vermelha")
    assert "FIGURINO LOCK" in lock
    assert "capa vermelha" in lock
    assert "CORPO INTEIRO" in lock
