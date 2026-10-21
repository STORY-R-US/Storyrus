"""Catálogo de histórias prontas (templates) da plataforma.

Traduzidas do material da cliente ("Imagina un cuento", jul/2026) e formatadas no
padrão da plataforma: uma frase por página, placeholder {NOME} substituído pelo
nome da criança no título e no texto. Aplicar um template NÃO usa IA nem créditos:
o texto vai direto para `project.story_text` no formato "Título: ...\nPágina N: ...",
que `_parse_title`/`_parse_pages` (workers/handlers.py) já sabem ler.

As notas de ilustração são guia interno de produção (retornadas na listagem para o
front/equipe), nunca entram no texto do livro.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path

PLACEHOLDER = "{NOME}"
STORIES_DIR = Path(__file__).resolve().parent / "stories"
ALPHABET_TEMPLATE_IDS = frozenset({"alfabeto_amazonia", "alfabeto_frutas"})
NUMBER_TEMPLATE_IDS = frozenset({"numeros_1_15"})
COLOR_TEMPLATE_IDS = frozenset({"cores_basicas"})
OPPOSITES_TEMPLATE_IDS = frozenset({"grande_pequeno"})

# Qualidades de conforto/impulso para a página do NOME (nunca animal).
_CHILD_QUALITIES: dict[str, list[str]] = {
    "A": ["amigo", "alegre", "amoroso"],
    "B": ["bondoso", "brilhante"],
    "C": ["corajoso", "carinhoso", "curioso"],
    "D": ["doce", "determinado"],
    "E": ["especial", "esperto"],
    "F": ["forte", "feliz"],
    "G": ["gentil", "grande"],
    "H": ["honesto"],
    "I": ["incrível"],
    "J": ["justo"],
    "K": ["querido"],
    "L": ["leal", "luz"],
    "M": ["magia"],
    "N": ["nobre"],
    "O": ["ousado", "amoroso"],
    "P": ["paciente"],
    "Q": ["querido"],
    "R": ["risonho"],
    "S": ["sonhador", "sorriso"],
    "T": ["terno", "talentoso", "tão especial"],
    "U": ["único"],
    "V": ["valente"],
    "W": ["valente"],
    "X": ["especial"],
    "Y": ["único"],
    "Z": ["zeloso"],
}
_QUALITY_FALLBACK = ["especial", "querido", "valente", "amigo", "luz"]

# id -> template. `paginas` é uma lista de (texto_da_pagina, nota_de_ilustracao).
STORY_TEMPLATES: dict[str, dict] = {
    "nave_vermelha": {
        "titulo": "{NOME} e sua nave vermelha",
        "genero": "unissex",
        "idade": "4-6",
        "tematica": "O valor do dinheiro e dos sonhos",
        "emoji": "🚀",
        "paginas": [
            (
                "A todos os pequenos sonhadores: que seus sonhos cresçam passinho a passinho.",
                "Página de dedicatória: céu estrelado com uma navezinha vermelha de brinquedo entre nuvens.",
            ),
            (
                "{NOME} sonha com uma nave vermelha, brilhante e veloz.",
                "{NOME} no quarto olhando um pôster/brinquedo de nave vermelha brilhante.",
            ),
            (
                "Toda noite olha as estrelas e se imagina viajando pelo céu.",
                "{NOME} na janela à noite, céu estrelado; balão de pensamento pilotando a nave.",
            ),
            (
                "Sua mãe lhe entrega um cofrinho especial: um porquinho com pintinhas rosas.",
                "Mãe entregando o cofre-porquinho rosa de pintinhas nas mãos de {NOME}.",
            ),
            (
                "{NOME} com seu porquinho novo está pronto para guardar moedas.",
                "{NOME} abraçado ao porquinho, sorridente, moedas na mesa.",
            ),
            (
                "{NOME} coloca sua primeira moeda dentro do porquinho. Clin, clin!, soa baixinho.",
                "Close da moedinha entrando na fenda do porquinho.",
            ),
            (
                "{NOME} aprende que os sonhos grandes precisam de tempo e paciência.",
                "{NOME} sentado com o porquinho no colo, calendário na parede ao fundo.",
            ),
            (
                "Seu pai lhe ensina que cada moeda se cuida com carinho.",
                "Pai agachado na altura de {NOME}, mostrando uma moeda com cuidado.",
            ),
            (
                "{NOME} ajuda em casa: recolhe seus brinquedos e varre as folhinhas do quintal.",
                "{NOME} guardando brinquedos numa caixa e varrendo folhas no quintal.",
            ),
            (
                "Cada pequeno esforço traz uma nova moeda.",
                "Mão dos pais entregando moedinha; {NOME} feliz com o porquinho por perto.",
            ),
            (
                "Um dia, {NOME} vê um robô brilhante na loja e quer comprá-lo.",
                "{NOME} na vitrine de uma loja, olhos grandes para um robô brilhante.",
            ),
            (
                "Mas lembra da sua nave vermelha e guarda a moeda.",
                "{NOME} de costas para a vitrine, apertando a moedinha; balão de pensamento com a nave.",
            ),
            (
                "O porquinho vai enchendo pouco a pouco, com paciência e amor.",
                "Sequência do porquinho cada vez mais cheio; moedas empilhadas ao lado.",
            ),
            (
                "Enfim o porquinho está cheinho, cheinho. {NOME} abre e conta suas moedas para "
                "comprar sua tão sonhada nave vermelha.",
                "{NOME} contando moedas no chão, porquinho aberto, expressão de alegria.",
            ),
            (
                "No final, {NOME} aprende que os sonhos decolam quando são cuidados e construídos "
                "passinho a passinho.",
                "{NOME} brincando com a nave vermelha nova; pais ao fundo sorrindo.",
            ),
        ],
    },
    "mapa_secreto": {
        "titulo": "{NOME} e seu mapa secreto",
        "genero": "unissex",
        "idade": "3-6",
        "tematica": "Mapa das emoções",
        "emoji": "🗺️",
        "paginas": [
            (
                "A todos os pequenos exploradores: que cada emoção os ajude a crescer.",
                "Página de dedicatória: mapa de pergaminho com corações e bússola.",
            ),
            (
                "{NOME} tem um mapa muito especial.",
                "{NOME} segurando um grande mapa colorido, olhar curioso.",
            ),
            (
                "Não é um mapa de ruas nem de tesouros. É o mapa do seu coração.",
                "Mapa aberto com um coração grande no centro, caminhos coloridos.",
            ),
            (
                "No mapa há emoções que mudam a cada dia.",
                "Mapa com quatro regiões: nuvem cinza, vulcão vermelho, chuva azul e campo amarelo.",
            ),
            (
                "Numa manhã, {NOME} vê uma nuvem cinza no seu mapa. A nuvem cinza é o medo.",
                "Nuvem cinza fofinha (não assustadora) pairando sobre o mapa.",
            ),
            (
                "{NOME} pensa em algo bonito e a nuvem vai embora devagarinho.",
                "{NOME} de olhos fechados pensando; nuvem saindo pelo canto.",
            ),
            (
                "À tarde aparece um vulcão vermelho no mapa. O vulcão vermelho é a raiva.",
                "Vulcão vermelho pequeno soltando fumacinha no mapa.",
            ),
            (
                "{NOME} põe uma mão no peito e outra na barriguinha.",
                "Close de {NOME} com uma mão no peito e outra na barriga.",
            ),
            (
                "Respira devagarinho e o vulcão se acalma suavemente.",
                "Vulcão apagando, virando montanha tranquila com florzinhas.",
            ),
            (
                "De repente aparece uma chuva azul. A chuva azul é a tristeza.",
                "Chuvinha azul suave caindo sobre uma parte do mapa.",
            ),
            (
                "{NOME} chora um pouquinho e sabe que a chuva também passa devagarinho.",
                "{NOME} com uma lagriminha, abraçando um bichinho de pelúcia; arco-íris surgindo.",
            ),
            (
                "Dali a pouco, aparece um campo amarelo de sol e flores. O campo amarelo é a alegria.",
                "Campo amarelo ensolarado com flores e borboletas no mapa.",
            ),
            (
                "{NOME} sorri suavemente e o coração fica tranquilinho.",
                "{NOME} sorrindo deitado no campo amarelo do mapa, coração brilhando.",
            ),
            (
                "No final, {NOME} olha seu mapa e aprende que todas as emoções podem ser exploradas "
                "e superadas dia a dia.",
                "{NOME} com o mapa completo aberto, as quatro emoções em harmonia.",
            ),
        ],
    },
    "atacante": {
        "titulo": "O atacante {NOME}",
        "genero": "menino",
        "idade": "4-6",
        "tematica": "O sonho do futebol: esforço e disciplina",
        "emoji": "⚽",
        "paginas": [
            (
                "A todos os pequenos sonhadores: que nunca deixem de correr atrás dos seus sonhos.",
                "Página de dedicatória: bola de futebol no gramado sob luzes de estádio.",
            ),
            (
                "{NOME} sonhava em ser jogador de futebol profissional.",
                "{NOME} de chuteira e camisa, bola debaixo do braço.",
            ),
            (
                "Nos fins de semana via os jogos com seu pai.",
                "{NOME} e o pai no sofá vibrando com um jogo na TV.",
            ),
            (
                "Um dia seu pai o levou ao estádio do seu clube favorito.",
                "{NOME} e o pai de mãos dadas chegando ao estádio.",
            ),
            (
                "Havia luzes gigantes, bandeiras coloridas e um gramado enorme.",
                "Vista ampla do estádio pelos olhos de {NOME}.",
            ),
            (
                "Desde esse dia, {NOME} saía para treinar com sua bola.",
                "{NOME} driblando a bola no quintal, cones improvisados.",
            ),
            (
                "Enquanto outras crianças brincavam de outras coisas, ele seguia com sua bola.",
                "Crianças ao fundo em outras brincadeiras; {NOME} treinando embaixadinhas.",
            ),
            (
                "Treinou tanto que um dia foi convidado para jogar num clube.",
                "Treinador entregando uma camisa de time para {NOME}.",
            ),
            (
                "Na sua primeira partida, ficou no banco o tempo todo.",
                "{NOME} sentado no banco de reservas, olhar ansioso para o campo.",
            ),
            (
                "O coração de {NOME} ficou triste. Mas ele não desistiu.",
                "{NOME} cabisbaixo saindo do campo, bola firme debaixo do braço.",
            ),
            (
                "Ao chegar em casa, treinou e treinou. Aos pouquinhos, seus chutes iam melhorando.",
                "{NOME} treinando chutes ao entardecer, gol improvisado.",
            ),
            (
                "Na partida seguinte o treinador o chamou. Enfim era a sua vez de jogar.",
                "Treinador chamando {NOME}; ele levantando do banco com olhos brilhando.",
            ),
            (
                "{NOME} entrou em campo com o coração batendo forte e um sorriso de orelha a orelha.",
                "{NOME} entrando no gramado, sorriso enorme.",
            ),
            (
                "Correu sem parar, passou a bola aos companheiros e comemorou os gols com abraços "
                "e pulos de muita alegria.",
                "{NOME} comemorando gol abraçado aos companheiros.",
            ),
            (
                "No final, {NOME} aprendeu que tudo o que sonha pode conquistar com esforço, treino "
                "e muita vontade de crescer.",
                "{NOME} com a bola ao pôr do sol; pai aplaudindo ao fundo.",
            ),
        ],
    },
    "aventuras_dino": {
        "titulo": "As aventuras de {NOME} e Dino",
        "genero": "menino",
        "idade": "4-6",
        "tematica": "Aprender com os erros",
        "emoji": "🦕",
        "paginas": [
            (
                "A todos os pequenos aventureiros: que nunca deixem de tentar.",
                "Página de dedicatória: floresta amigável com pegadas de criança e de dinossauro.",
            ),
            (
                "{NOME} e seu amigo Dino brincam juntos todos os dias.",
                "{NOME} e Dino (dinossauro fofo verde) brincando de correr num campo.",
            ),
            (
                "Uma noite chove muito, muito, e o rio cresce e os deixa separados. Cada um de um lado.",
                "Chuva forte à noite; de manhã, rio largo entre os dois amigos.",
            ),
            (
                "{NOME} e Dino querem voltar a brincar juntos e decidem construir uma ponte.",
                "Os dois com caras decididas olhando o rio.",
            ),
            (
                "Primeiro juntam folhas grandes e as colocam sobre o rio com muito cuidado.",
                "Cada um colocando folhas gigantes sobre a água.",
            ),
            (
                "Mas o vento sopra... e leva todas as folhas voando.",
                "Vento soprando; folhas voando; caras de surpresa.",
            ),
            (
                "{NOME} e Dino ficam pensando e têm uma ideia nova: usar gravetos.",
                "Os dois pensando, lampadinha acesa, gravetos por perto.",
            ),
            (
                "Colocam os gravetos um ao lado do outro, formando um caminhozinho sobre a água.",
                "Caminhinho de gravetos atravessando o rio.",
            ),
            (
                "Mas o rio corre forte... e leva os gravetos boiando.",
                "Correnteza levando os gravetos; caras de 'ah, não!'.",
            ),
            (
                "{NOME} e Dino pensam mais uma vez e descobrem algo: podem usar pedras.",
                "Os dois animados apontando pedras grandes na margem.",
            ),
            (
                "Cada um coloca pedras do seu lado, uma por uma, chegando perto do meio.",
                "{NOME} de um lado e Dino do outro, empilhando pedras.",
            ),
            (
                "A ponte cresce pouquinho a pouquinho, firme e segura, até que os dois lados se "
                "encontram.",
                "As duas metades da ponte de pedras se encontrando no meio.",
            ),
            (
                "{NOME} e Dino se abraçam felizes por terem construído sua nova ponte.",
                "{NOME} e Dino se abraçando em cima da ponte pronta.",
            ),
            (
                "Nunca deixe de tentar. Quando uma ideia não funciona, sempre dá para encontrar "
                "outra. Com paciência, esforço e coragem, você pode conseguir coisas maravilhosas.",
                "Os dois brincando juntos; a ponte de pedras ao fundo como conquista.",
            ),
        ],
    },
    "bichinhos_fazenda": {
        "titulo": "{NOME} e os bichinhos da fazenda",
        "genero": "menina",
        "idade": "3-6",
        "tematica": "A arte de comunicar: pedir o que precisamos e escutar com atenção",
        "emoji": "🐑",
        "paginas": [
            (
                "A todos os pequenos sonhadores: que escutem com o coração.",
                "Página de dedicatória: porteira de fazenda com coraçõezinhos.",
            ),
            (
                "{NOME} adorava a fazenda da sua vovó.",
                "{NOME} correndo feliz pela fazenda; vovó acenando da varanda.",
            ),
            (
                "Um dia, um carneirinho baliu bem forte. Béee! Béee!",
                "Carneirinho fofo balindo; {NOME} se virando para olhar.",
            ),
            (
                "Ele queria alguma coisa. Mas ninguém entendia o quê.",
                "Carneirinho aflito; {NOME} e os animais com pontos de interrogação.",
            ),
            (
                "A vovó lhe ensinou um segredo: escutar com o coração.",
                "Vovó agachada cochichando no ouvido de {NOME}.",
            ),
            (
                "{NOME} pensou que ele estava com sede. Levou aguinha fresca para ele.",
                "{NOME} carregando um baldinho de água até o carneirinho.",
            ),
            (
                "Mas o carneirinho continuou balindo. Béee!",
                "Carneirinho ao lado do balde cheio, ainda balindo.",
            ),
            (
                "Ela o levou com muito cuidado até a sombrinha.",
                "{NOME} guiando o carneirinho até a sombra de uma árvore.",
            ),
            (
                "Mas o carneirinho baliu de novo. Béee! Béee!",
                "Carneirinho na sombra, ainda balindo; {NOME} pensativa.",
            ),
            (
                "{NOME} queria desistir. A vovó sorriu: aprender leva tempo.",
                "{NOME} desanimada num toco; vovó com a mão no ombro dela.",
            ),
            (
                "Então {NOME} sentou bem quietinha. E olhou com atenção.",
                "{NOME} sentada em silêncio na grama, observando com calma.",
            ),
            (
                "O carneirinho se aninhou juntinho dela. Ele só queria companhia!",
                "Carneirinho deitando a cabeça no colo de {NOME}.",
            ),
            (
                "Desde esse dia, o carneirinho e {NOME} se tornaram bons amigos.",
                "{NOME} e o carneirinho brincando juntos pela fazenda.",
            ),
            (
                "E toda tarde, na fazenda, aprendiam a se entender, coração com coração.",
                "Pôr do sol na fazenda; os dois lado a lado; coraçõezinhos no ar.",
            ),
            (
                "Quando escutamos com atenção e com o coração, descobrimos o que os outros "
                "realmente precisam.",
                "Vovó, {NOME} e o carneirinho juntos na varanda, tarde dourada.",
            ),
        ],
    },
    "fundo_do_mar": {
        "titulo": "{NOME} e seus amigos no fundo do mar",
        "genero": "unissex",
        "idade": "2-3",
        "tematica": "Cuidar do planeta",
        "emoji": "🧜",
        "paginas": [
            (
                "A todos os pequenos corações: que cuidem do oceano inteiro.",
                "Página de dedicatória: ondas suaves e bolhas com coraçõezinhos.",
            ),
            (
                "{NOME} é uma sereiazinha que vive num recife cheio de cores.",
                "{NOME} sereia (cauda colorida) diante de um recife vibrante.",
            ),
            (
                "Todos os dias nada pelo recife, dando oi para os amigos.",
                "{NOME} nadando e acenando para peixinhos, tartaruga e cavalo-marinho.",
            ),
            (
                "Um dia, uma correnteza a desvia um pouquinho do caminho. {NOME} vê partes do "
                "recife que não conhecia.",
                "Correnteza em linhas curvas levando {NOME} a uma área nova do recife.",
            ),
            (
                "Algo a surpreende: há lixo por toda parte. Garrafas, sacolas e latas cobrem as "
                "casinhas dos peixinhos.",
                "Área do recife com garrafas, sacolas e latas; cores apagadas.",
            ),
            (
                "Um peixinho pequeno aparece devagarinho. Ele conta que está doente por causa do lixo.",
                "Peixinho pálido e triste saindo de trás de uma lata.",
            ),
            (
                "{NOME} fica muito triste, e nada rápido para chamar seus amigos para ajudar.",
                "{NOME} nadando veloz com expressão determinada.",
            ),
            (
                "O baiacu, o polvo e a peixinha veloz se arrumam rapidinho para limpar o mar.",
                "Os três amigos em fila, prontos como uma equipe de limpeza.",
            ),
            (
                "{NOME} junta os papéis. O polvo junta as latas. O baiacu empurra as garrafas com "
                "sua barriguinha redonda, e a peixinha junta o que é pequenininho.",
                "Cena de mutirão: cada amigo com sua tarefa.",
            ),
            (
                "Pouco a pouco, o mar fica mais limpo. A água começa a brilhar de novo!",
                "Recife recuperando as cores, água com brilhos.",
            ),
            (
                "Os peixes saem de suas casinhas limpas. O peixinho doente já se sente bem melhor.",
                "Peixinhos saindo dos corais; o peixinho doente agora corado.",
            ),
            (
                "E brincam todos felizes entre as bolhas, num mar limpo, colorido e brilhante.",
                "Todos brincando entre bolhas num recife vibrante.",
            ),
            (
                "Cada pequena ação conta. Se jogamos o lixo no lugar certo e cuidamos dos nossos "
                "mares, ajudamos os peixes e todos os animais marinhos a terem um lar limpo e "
                "feliz. O mar também precisa do nosso carinho!",
                "{NOME} e os amigos em volta de um coração de bolhas.",
            ),
        ],
    },
}


def _load_json_templates() -> dict[str, dict]:
    """Carrega histórias extras em JSON (texto + nota + layout por página)."""
    out: dict[str, dict] = {}
    if not STORIES_DIR.is_dir():
        return out
    for path in sorted(STORIES_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        tid = str(data.get("id") or path.stem)
        pages = []
        for p in data.get("pages") or []:
            pages.append(
                {
                    "texto": p.get("text") or "",
                    "nota": p.get("illustration_note") or "",
                    "layout": p.get("layout") or "story",
                }
            )
        out[tid] = {
            "titulo": data.get("titulo") or data.get("title") or "{NOME}",
            "genero": data.get("genero") or "unissex",
            "idade": data.get("idade") or "3-7",
            "tematica": data.get("tematica") or data.get("theme") or "",
            "emoji": data.get("emoji") or "📖",
            "paginas": pages,
        }
    return out


STORY_TEMPLATES.update(_load_json_templates())


def _page_dict(item: tuple | dict) -> dict:
    if isinstance(item, dict):
        return {
            "texto": item.get("texto") or item.get("text") or "",
            "nota": item.get("nota") or item.get("illustration_note") or "",
            "layout": item.get("layout") or "story",
        }
    texto, nota = item
    return {"texto": texto, "nota": nota, "layout": "story"}


def name_letters(child_name: str) -> list[str]:
    """Letras A–Z do nome (sem acento), na ordem."""
    folded = unicodedata.normalize("NFKD", child_name or "")
    stripped = "".join(c for c in folded if not unicodedata.combining(c))
    return [c.upper() for c in stripped if "A" <= c.upper() <= "Z"][:12]


def _is_girl(gender: str | None) -> bool:
    return (gender or "").strip().lower() in ("girl", "menina", "f", "female")


def _child_role(gender: str | None) -> str:
    g = (gender or "").strip().lower()
    if g in ("boy", "menino", "m", "male"):
        return "menino valente"
    if _is_girl(gender):
        return "menina valente"
    return "coração valente"


def _gender_dedication(texto: str, gender: str | None) -> str:
    """Ajusta aventureiro/o leve na dedicatória (qualquer livro do catálogo)."""
    if not _is_girl(gender):
        return texto
    return texto.replace("pequeno aventureiro", "pequena aventureira").replace(
        " o leve a lugares", " a leve a lugares"
    )


def build_name_rhyme(child_name: str, gender: str | None = None) -> str:
    """P2: soletração + rima sobre a criança (nunca animal)."""
    name = (child_name or "").strip()
    letters = name_letters(name)
    if not name or not letters:
        return name
    spelled = " · ".join(letters)
    used: set[str] = set()
    bits: list[str] = []
    for letter in letters:
        options = list(_CHILD_QUALITIES.get(letter) or _QUALITY_FALLBACK)
        word = next((w for w in options if w not in used), None)
        if word is None:
            word = next((w for w in _QUALITY_FALLBACK if w not in used), options[0])
        used.add(word)
        bits.append(f"{letter} é {word}.")
    role = _child_role(gender)
    return (
        f"{name} se soletra assim: {spelled}.\n"
        f"{name}, {role}, caminha com a gente.\n" + " ".join(bits)
    )


def illustration_notes(template_id: str, child_name: str) -> list[str]:
    """Notas de ilustração já personalizadas (uma por página)."""
    template = STORY_TEMPLATES.get(template_id)
    if template is None:
        return []
    name = (child_name or "").strip()
    notes = []
    for item in template["paginas"]:
        page = _page_dict(item)
        notes.append(page["nota"].replace(PLACEHOLDER, name) if name else page["nota"])
    return notes


def page_layouts(template_id: str) -> list[str]:
    template = STORY_TEMPLATES.get(template_id)
    if template is None:
        return []
    return [_page_dict(item)["layout"] for item in template["paginas"]]


def list_templates() -> list[dict]:
    """Metadados dos templates para a listagem no app (sem o texto integral)."""
    return [
        {
            "id": tid,
            "titulo": t["titulo"],
            "genero": t["genero"],
            "idade": t["idade"],
            "tematica": t["tematica"],
            "emoji": t.get("emoji", "📖"),
            "paginas": len(t["paginas"]),
        }
        for tid, t in STORY_TEMPLATES.items()
    ]


def render_template(template_id: str, child_name: str, gender: str | None = None) -> str:
    """Gera o story_text no formato padrão da plataforma ('Título:' + 'Página N:').

    O nome da criança substitui {NOME} no título e em todas as páginas. As notas
    de ilustração NÃO entram no texto (são guia interno).
    """
    template = STORY_TEMPLATES.get(template_id)
    if template is None:
        raise KeyError(template_id)
    name = (child_name or "").strip()
    if not name:
        raise ValueError("child_name obrigatório para personalizar o template")

    lines = ["Título: " + template["titulo"].replace(PLACEHOLDER, name)]
    for i, item in enumerate(template["paginas"], 1):
        page = _page_dict(item)
        if template_id in ALPHABET_TEMPLATE_IDS and page["layout"] == "name":
            texto = build_name_rhyme(name, gender)
        else:
            texto = page["texto"].replace(PLACEHOLDER, name)
            if page["layout"] == "dedication":
                texto = _gender_dedication(texto, gender)
        lines.append(f"Página {i}: " + texto)
    return "\n".join(lines)
