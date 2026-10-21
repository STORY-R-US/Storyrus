"""Story and storyboard job handlers."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import storage
from app.ai_clients.base import ImageResult, ProviderError
from app.ai_clients.book_prompts import (
    CHARACTER_SHEET_PROMPT,
    EXPRESSION_SHEET_KEYS,
    EXPRESSION_SHEET_PROMPT,
    book_art_direction,
    build_scene_prompt,
    costume_extras_for_template,
    costume_extras_for_theme,
    costume_lock_prompt,
    identity_shot,
    infer_expression,
    normalize_expression,
    normalize_shot,
    normalize_text_band,
)
from app.ai_clients.book_prompts import (
    STYLE as BOOK_STYLE,
)
from app.ai_clients.identity_lock import (
    IDENTITY_MISMATCH_ERROR,
    IdentityLock,
    build_identity_lock,
    judge_identity,
)
from app.config import settings
from app.models import Asset, AssetKind, Job, JobStatus, JobType, Project, ProjectStatus
from app.observability.opik_trace import (
    job_metadata,
    log_feedback,
    track,
    update_span,
    update_trace,
)
from app.observability.story_judge import score_and_log_story
from app.services import preview_chain
from app.services.pricing import add_usd
from app.services.usage_ledger import (
    lines_of,
)

from .avatar import _refine_scene
from .common import (
    _ext,
    _parse_pages,
    _parse_title,
    _payload,
    _project,
    _set_status,
    _tag_image,
)

logger = logging.getLogger("worker")


def _pkg():
    """Package root — tests monkeypatch providers/score on app.workers.handlers."""
    from app.workers import handlers as pkg

    return pkg


# --------------------------------------------------------------------------- #
# Guias educativos por tema: (o que a história ensina, sequência lógica da jornada)
# --------------------------------------------------------------------------- #
THEME_EDU: dict[str, dict[str, tuple[str, str]]] = {
    "pt": {
        "adventure": (
            "exploração e orientação: como usar um mapa, os pontos cardeais e o respeito à natureza",
            "preparar a mochila e o mapa → seguir a trilha lendo o mapa → atravessar um obstáculo "
            "da natureza (rio, colina) com uma ideia inteligente → a grande descoberta → voltar "
            "para casa e contar o que aprendeu",
        ),
        "princess": (
            "empatia, gentileza e cuidado com os outros: um reino funciona quando todos se ajudam",
            "um pedido de ajuda chega ao castelo → a jornada pelos jardins e vilarejos → ajudar "
            "dois moradores com gentileza (cada um ensina algo) → resolver o problema do reino no "
            "clímax → festa no castelo e a lição de cuidar dos outros",
        ),
        "superhero": (
            "responsabilidade, hábitos saudáveis e trabalho em equipe: herói de verdade treina, "
            "ajuda e também pede ajuda",
            "descobrir um talento especial → treinar com dedicação (comer bem, dormir, praticar) → "
            "surgir um problema na vizinhança → resolver com inteligência e trabalho em equipe → "
            "celebração e a lição de que ajudar é o maior superpoder",
        ),
        "space": (
            "astronomia para crianças: a Lua, os planetas, as estrelas e a gravidade (tudo flutua!)",
            "preparar o foguete e a contagem regressiva → chegar à Lua e flutuar (gravidade "
            "fraquinha) → visitar um planeta colorido (com um fato real sobre ele) → admirar as "
            "estrelas → voltar à Terra com saudade e conhecimento novo",
        ),
        "underwater": (
            "vida marinha: recifes de coral são casas de peixinhos, tartarugas sobem para "
            "respirar, golfinhos conversam por sons",
            "o mergulho começa na praia → conhecer o recife de corais e seus moradores → um "
            "amiguinho marinho em apuros → travessia da correnteza com uma ideia esperta → "
            "resgate e festa no recife → volta à praia ao entardecer",
        ),
        "dinosaurs": (
            "paleontologia para crianças: espécies reais e suas características (braquiossauro de "
            "pescoço comprido come plantas, tricerátopo tem três chifres, pterossauro plana no "
            "vento) e o que são fósseis",
            "encontrar uma pegada ou fóssil misterioso → chegar ao vale dos dinossauros → conhecer "
            "três espécies (um fato divertido sobre cada uma) → ajudar um filhote perdido a voltar "
            "ao ninho → despedida e volta para casa guardando um tesourinho da aventura",
        ),
        "fantasy": (
            "segredos da natureza com um toque de magia: vaga-lumes brilham para conversar, "
            "cogumelos ajudam a floresta, plantas precisam de cuidado para crescer",
            "a entrada na floresta encantada → um ser mágico pede ajuda → duas boas ações no "
            "caminho (cada uma revela um segredo da natureza) → a floresta inteira se ilumina no "
            "clímax → a lição de que a gentileza ilumina o mundo",
        ),
        # ---- Datas comemorativas ----
        "birthday": (
            "celebração, gratidão e o valor de crescer: cada ano novo é uma página em branco "
            "para preencher com aventuras e boas memórias",
            "acordar no dia especial e sentir a magia no ar → preparar surpresas para os amigos → "
            "uma aventura divertida com obstáculos engraçados → a festa surpresa no clímax → "
            "aprender que o melhor presente é ter quem a gente ama por perto",
        ),
        "christmas": (
            "generosidade, união familiar e espírito natalino: dar é melhor que receber, "
            "e a magia está nas pequenas coisas",
            "ajudar a decorar a casa e a árvore → uma aventura para encontrar o presente "
            "perfeito → encontrar alguém que precisa de ajuda → a ceia de Natal reunindo "
            "todos → a lição de que o espírito do Natal está no coração",
        ),
        "easter": (
            "esperança, renascimento e alegria de descobrir coisas novas: como os "
            "pintinhos nascem e as flores voltam a brotar",
            "pela manhã, encontrar os primeiros ovos escondidos → seguir pistas pelo "
            "jardim → ajudar um filhote perdido a encontrar o ninho → a grande festa "
            "de Páscoa com todos os amigos → aprender que depois do inverno sempre vem "
            "a primavera",
        ),
        "childrens_day": (
            "a importância de ser criança: brincar, imaginar e sonhar são os "
            "superpoderes mais poderosos do mundo",
            "acordar sabendo que hoje é o dia especial → escolher a brincadeira "
            "perfeita → uma aventura onde a imaginação se torna realidade → compartilhar "
            "alegria com todos os amigos → aprender que ser criança é o maior presente",
        ),
        "mothers_day": (
            "gratidão, amor incondicional e o valor de cuidar uns dos outros: "
            "mamãe é quem nos ensina a amar",
            "acordar cedo para preparar uma surpresa → uma aventura para encontrar "
            "o presente perfeito → ajudar alguém no caminho → entregar o presente "
            "com um abraço → aprender que o melhor presente é o amor",
        ),
        "fathers_day": (
            "gratidão, coragem e o valor de ter um herói ao nosso lado: papai "
            "nos ensina a ser fortes e gentis",
            "acordar com uma ideia especial para o papai → uma aventura onde "
            "aprendemos algo que ele adora → encontrar um presente que representa "
            "nossa admiração → entregar com orgulho → aprender que papai é nosso "
            "maior herói",
        ),
        "new_year": (
            "novos começos, esperança e o poder de sonhar alto: cada ano novo "
            "é uma página em branco para escrever nossa história",
            "contar os últimos segundos do ano → fazer um pedido especial → "
            "uma aventura simbólica representando o novo ano → compartilhar "
            "alegria com a família → aprender que novos sonhos trazem "
            "novas possibilidades",
        ),
    },
    "en": {
        "adventure": (
            "exploration and orientation: how to read a map, the cardinal directions and respect for nature",
            "pack the backpack and map → follow the trail reading the map → cross a natural "
            "obstacle (river, hill) with a clever idea → the big discovery → return home and share "
            "what was learned",
        ),
        "princess": (
            "empathy, kindness and caring for others: a kingdom works when everyone helps",
            "a call for help reaches the castle → a journey through gardens and villages → help two "
            "villagers with kindness (each teaches something) → solve the kingdom's problem at the "
            "climax → castle celebration and the lesson of caring for others",
        ),
        "superhero": (
            "responsibility, healthy habits and teamwork: a real hero trains, helps and also asks for help",
            "discover a special talent → train with dedication (eat well, sleep, practice) → a "
            "problem appears in the neighborhood → solve it with cleverness and teamwork → "
            "celebration and the lesson that helping is the greatest superpower",
        ),
        "space": (
            "astronomy for kids: the Moon, the planets, the stars and gravity (everything floats!)",
            "prepare the rocket and the countdown → reach the Moon and float (weak gravity) → visit "
            "a colorful planet (with one real fact about it) → admire the stars → return to Earth "
            "with new knowledge",
        ),
        "underwater": (
            "marine life: coral reefs are homes for fish, turtles surface to breathe, dolphins talk "
            "through sounds",
            "the dive starts at the beach → meet the coral reef and its residents → a little sea "
            "friend in trouble → cross the current with a clever idea → rescue and reef celebration "
            "→ back to the beach at sunset",
        ),
        "dinosaurs": (
            "paleontology for kids: real species and their traits (long-necked Brachiosaurus eats "
            "plants, Triceratops has three horns, Pterosaurs glide on the wind) and what fossils are",
            "find a mysterious footprint or fossil → arrive at the dinosaur valley → meet three "
            "species (one fun fact about each) → help a lost hatchling back to its nest → farewell "
            "and journey home keeping a little treasure from the adventure",
        ),
        "fantasy": (
            "nature's secrets with a touch of magic: fireflies glow to talk, mushrooms help the "
            "forest, plants need care to grow",
            "enter the enchanted forest → a magical creature asks for help → two good deeds along "
            "the way (each reveals a secret of nature) → the whole forest lights up at the climax → "
            "the lesson that kindness lights up the world",
        ),
        # ---- Special dates ----
        "birthday": (
            "celebration, gratitude and the value of growing up: each new year is a blank page "
            "to fill with adventures and happy memories",
            "wake up on the special day and feel the magic in the air → prepare surprises for "
            "friends → a fun adventure with silly obstacles → the surprise party at the climax → "
            "learn that the best gift is having loved ones around",
        ),
        "christmas": (
            "generosity, family unity and the Christmas spirit: giving is better than receiving, "
            "and magic lives in small things",
            "help decorate the house and tree → an adventure to find the perfect gift → find "
            "someone who needs help → the Christmas dinner bringing everyone together → the "
            "lesson that the Christmas spirit lives in the heart",
        ),
        "easter": (
            "hope, renewal and the joy of discovering new things: how chicks hatch and flowers "
            "bloom again",
            "wake up to find the first hidden eggs → follow clues through the garden → help a "
            "lost chick find its nest → the big Easter celebration with all friends → learn that "
            "after winter always comes spring",
        ),
        "childrens_day": (
            "the importance of being a child: playing, imagining and dreaming are the most "
            "powerful superpowers in the world",
            "wake up knowing today is the special day → choose the perfect game → an adventure "
            "where imagination becomes reality → share joy with all friends → learn that being "
            "a child is the greatest gift",
        ),
        "mothers_day": (
            "gratitude, unconditional love and the value of caring for each other: mom teaches "
            "us how to love",
            "wake up early to prepare a surprise → an adventure to find the perfect gift → help "
            "someone along the way → deliver the gift with a hug → learn that the best gift is love",
        ),
        "fathers_day": (
            "gratitude, courage and the value of having a hero by our side: dad teaches us to "
            "be strong and kind",
            "wake up with a special idea for dad → an adventure where we learn something he loves "
            "→ find a gift that represents our admiration → deliver it with pride → learn that dad "
            "is our greatest hero",
        ),
        "new_year": (
            "new beginnings, hope and the power of dreaming big: each new year is a blank page "
            "to write our story",
            "count down the last seconds of the year → make a special wish → a symbolic adventure "
            "representing the new year → share joy with family → learn that new dreams bring "
            "new possibilities",
        ),
    },
}


# --------------------------------------------------------------------------- #
# Objetivos educacionais estruturados: foco, vilão, cenário e sequência da jornada.
# Usado por handle_story() para compor o brief com informações granulares.
# --------------------------------------------------------------------------- #
LEARNING_GOALS: dict[str, dict[str, dict[str, str]]] = {
    "pt": {
        # ---- Linguagem & Conceitos Fundamentais ----
        "alfabetizacao_inicial": {
            "foco": "consciência fonêmica: o alfabeto, rimas e a leitura da esquerda para a direita",
            "vilao": "a Timidez, que faz a criança guardar as palavras só para si",
            "espaco": "um cantinho de leitura cheio de livros e letras coloridas",
            "sequencia": (
                "encontrar uma letra ou palavra misteriosa → seguir pistas rimadas pela "
                "casa → a Timidez tenta calar a criança bem na hora de dizer a palavra em "
                "voz alta → a criança usa a curiosidade para soletrar e ler mesmo com medo "
                "→ celebrar lendo a palavra inteira para todos"
            ),
        },
        "pensamento_matematico": {
            "foco": "contar de 1 a 5, separar por tamanho e reconhecer círculo, quadrado e triângulo",
            "vilao": "a Pressa, que faz contar errado e pular números",
            "espaco": "um quarto ou quintal cheio de blocos, brinquedos e formas para organizar",
            "sequencia": (
                "objetos espalhados pedem para ser organizados → contar um a um devagar → "
                "a Pressa tenta atropelar a contagem → a criança respira e conta de novo, "
                "com calma → tudo organizado por tamanho e forma, missão cumprida"
            ),
        },
        "cores": {
            "foco": "cores primárias e secundárias, reconhecidas em objetos do mundo real",
            "vilao": "a Confusão, que embaralha as cores na cabeça da criança",
            "espaco": "um jardim ou caixa de tintas cheio de cores para nomear",
            "sequencia": (
                "algo perdeu a cor certa e precisa ser combinado → percorrer o espaço "
                "nomeando cores em objetos conhecidos → a Confusão troca as cores de lugar "
                "→ a criança usa o que já sabe (o que é amarelo? o que é azul?) para desfazer "
                "a troca → tudo com a cor certa de novo"
            ),
        },
        "opostos_espacial": {
            "foco": "grande/pequeno, em cima/embaixo, dentro/fora",
            "vilao": "o Embolado, um sentimento de estar perdido no espaço",
            "espaco": "uma casa ou parquinho com cantos altos, baixos, dentro e fora bem marcados",
            "sequencia": (
                "algo precisa ser guardado ou encontrado no lugar certo → explorar o "
                "espaço nomeando opostos a cada passo → o Embolado confunde as direções → a "
                "criança usa os opostos como mapa (não é embaixo, é em cima!) → encontra o "
                "caminho certo"
            ),
        },
        # ---- Habilidades de Vida & Rotinas Diárias ----
        "higiene_desfralde": {
            "foco": "a transição do banheiro, lavar as mãos e escovar os dentes em passos previsíveis",
            "vilao": "a Vergonha, que faz esconder quando precisa ir ao banheiro",
            "espaco": "o banheiro de casa, arrumado e acolhedor",
            "sequencia": (
                "a criança sente que precisa ir ao banheiro → a Vergonha sussurra para "
                "esconder o sinal → a criança nomeia o que sente e pede ajuda → consegue "
                "sozinha, passo a passo (calça, sentar, papel, descarga, lavar as mãos) → "
                "orgulho de ter conseguido"
            ),
        },
        "rotina_dormir": {
            "foco": "a ansiedade de separação e uma rotina calma antes de dormir",
            "vilao": "o Medo-do-Escuro, que aparece quando a luz apaga",
            "espaco": "o quarto da criança à noite, com uma luminária e um brinquedo favorito",
            "sequencia": (
                "o dia termina e chega a hora de dormir → passos da rotina (banho, pijama, "
                "escovar os dentes, história) → o Medo-do-Escuro aparece quando a luz apaga "
                "→ a criança nomeia o medo e acende a luminária/abraça o brinquedo → "
                "adormece tranquila"
            ),
        },
        "alimentacao_saudavel": {
            "foco": "grupos de alimentos, frutas e verduras, coragem para experimentar texturas novas",
            "vilao": "o Enjoo, que faz recusar tudo que é novo no prato",
            "espaco": "a cozinha ou horta de casa, colorida com frutas e legumes",
            "sequencia": (
                "aparece um alimento novo e diferente no prato ou na horta → o Enjoo "
                "encolhe o nariz da criança → a criança usa a curiosidade (cheirar, tocar, "
                "provar um pouquinho) para vencer o Enjoo → descobre um sabor novo → orgulho "
                "de ter experimentado"
            ),
        },
        "vestir_autonomia": {
            "foco": "identificar peças de roupa, botões, zíperes e sapatos, e vestir-se sozinho",
            "vilao": "a Impaciência, que quer que outra pessoa faça tudo",
            "espaco": "o guarda-roupa ou quarto, com roupas espalhadas para escolher",
            "sequencia": (
                "a criança precisa se vestir para algo especial → a Impaciência tenta fazer "
                "desistir no primeiro botão emperrado → a criança tenta de novo, devagar, "
                "peça por peça → consegue se vestir sozinha → orgulho de ter feito por "
                "conta própria"
            ),
        },
        # ---- Autoconsciência & Aprendizagem Socioemocional ----
        "literacia_emocional": {
            "foco": "nomear sentimentos grandes — raiva, tristeza, frustração, alegria",
            "vilao": "o sentimento grande do dia (Raiva, Tristeza ou Frustração), como personagem",
            "espaco": "um lugar familiar e calmo, como a sala de casa ou o pátio da escola",
            "sequencia": (
                "algo não sai como a criança queria → o sentimento grande aparece e cresce "
                "→ a criança tenta ignorá-lo, mas ele só cresce mais → a criança para, nomeia "
                "o que sente e respira fundo → o sentimento fica pequeno e vira aprendizado"
            ),
        },
        "consciencia_corporal": {
            "foco": "nomes das partes do corpo, o que elas fazem e limites espaciais básicos",
            "vilao": "o Desatento, que faz a criança não perceber o próprio corpo",
            "espaco": "um espaço de brincar livre, como o quintal ou a sala",
            "sequencia": (
                "uma brincadeira de imitação ou dança começa → cada parte do corpo entra em "
                "ação (mãos, pés, cabeça) → o Desatento tenta bagunçar os movimentos → a "
                "criança presta atenção no próprio corpo e acerta o ritmo → brincadeira "
                "concluída com orgulho"
            ),
        },
        "compartilhar_revezar": {
            "foco": "brincar em paralelo, dividir e esperar a vez com gentileza",
            "vilao": "o Ciúme, que não quer soltar o brinquedo",
            "espaco": "um parquinho ou sala de brincar com outra criança por perto",
            "sequencia": (
                "um amiguinho quer brincar com o mesmo brinquedo → o Ciúme aperta o brinquedo "
                "contra o peito → a criança sente o Ciúme, mas lembra como é bom brincar junto "
                "→ propõe revezar ou dividir → os dois brincam juntos e se divertem mais ainda"
            ),
        },
        # ---- Descoberta & Exploração do Mundo ----
        "animais_sons": {
            "foco": "nomes e sons de animais, e seus habitats (fazenda, oceano, selva)",
            "vilao": "o Silêncio-Enroscado, que embaralha os sons dos animais",
            "espaco": "uma fazenda, floresta ou aquário para visitar",
            "sequencia": (
                "um som de animal escapa e ninguém sabe de quem é → seguir o som até o "
                "habitat certo → o Silêncio-Enroscado tenta confundir o som com outro animal "
                "→ a criança escuta com atenção e acerta o animal e seu som → o habitat "
                "inteiro canta junto"
            ),
        },
        "transporte_ajudantes": {
            "foco": "veículos (caminhão, trem, avião) e figuras da comunidade (bombeiro, médico, carteiro)",
            "vilao": "a Pressa-Perdida, que atrapalha o caminho até o ajudante certo",
            "espaco": "uma rua ou cidade pequena com diferentes veículos passando",
            "sequencia": (
                "algo precisa ser entregue ou resolvido rápido → a criança escolhe o veículo "
                "certo para o trajeto → a Pressa-Perdida embaralha o caminho → a criança para, "
                "pensa e escolhe a rota certa com a ajuda de um profissional da comunidade → "
                "missão entregue com sucesso"
            ),
        },
        "clima_estacoes": {
            "foco": "padrões de clima (chuva, sol, neve) e a roupa certa para cada estação",
            "vilao": "o Friozinho-Sem-Aviso (ou Solzão-Repentino), que muda o tempo de repente",
            "espaco": "o quintal ou uma janela que mostra o tempo mudando",
            "sequencia": (
                "a criança se prepara para sair de um jeito → o tempo muda de repente → o "
                "vilão do clima brinca de confundir a roupa certa → a criança observa o céu e "
                "escolhe a roupa certa para a nova estação/clima → sai para brincar preparada "
                "e feliz"
            ),
        },
    },
    "en": {
        # ---- Language & Fundamental Concepts ----
        "alfabetizacao_inicial": {
            "foco": "phonemic awareness: the alphabet, rhymes and reading left to right",
            "vilao": "Shyness, who makes the child keep words to herself",
            "espaco": "a cozy reading corner full of books and colorful letters",
            "sequencia": (
                "a mysterious letter or word appears → follow rhyming clues around the house "
                "→ Shyness tries to silence the child right when it's time to say the word "
                "out loud → the child uses curiosity to spell and read despite the fear → "
                "celebrate by reading the whole word to everyone"
            ),
        },
        "pensamento_matematico": {
            "foco": "counting from 1 to 5, sorting by size and recognizing circles, squares and triangles",
            "vilao": "Hurry, who makes counting go wrong and skip numbers",
            "espaco": "a room or backyard full of blocks, toys and shapes to organize",
            "sequencia": (
                "scattered objects need organizing → count them one by one, slowly → Hurry "
                "tries to rush the counting → the child breathes and counts again, calmly → "
                "everything sorted by size and shape, mission complete"
            ),
        },
        "cores": {
            "foco": "primary and secondary colors, recognized in real-world objects",
            "vilao": "Confusion, who scrambles the colors in the child's mind",
            "espaco": "a garden or paint box full of colors to name",
            "sequencia": (
                "something lost its right color and needs matching → move through the space "
                "naming colors on familiar objects → Confusion swaps the colors around → the "
                "child uses what she already knows to undo the swap → everything has the "
                "right color again"
            ),
        },
        "opostos_espacial": {
            "foco": "big/small, up/down, inside/outside",
            "vilao": "the Muddle, a feeling of being lost in space",
            "espaco": "a house or playground with clearly marked high, low, inside and outside corners",
            "sequencia": (
                "something needs to be put away or found in the right spot → explore the "
                "space naming opposites at each step → the Muddle confuses the directions → "
                "the child uses opposites as a map → finds the right way"
            ),
        },
        # ---- Life Skills & Daily Routines ----
        "higiene_desfralde": {
            "foco": "the bathroom transition, handwashing and toothbrushing in predictable steps",
            "vilao": "Shame, who makes the child hide when she needs the bathroom",
            "espaco": "the home bathroom, tidy and welcoming",
            "sequencia": (
                "the child feels she needs the bathroom → Shame whispers to hide the signal "
                "→ the child names what she feels and asks for help → manages alone, step by "
                "step → pride in having done it"
            ),
        },
        "rotina_dormir": {
            "foco": "separation anxiety and a calm routine before sleep",
            "vilao": "Fear-of-the-Dark, who shows up when the light goes off",
            "espaco": "the child's bedroom at night, with a nightlight and a favorite toy",
            "sequencia": (
                "the day ends and bedtime arrives → routine steps (bath, pajamas, brushing "
                "teeth, story) → Fear-of-the-Dark appears when the light goes off → the "
                "child names the fear and turns on the nightlight or hugs the toy → falls "
                "asleep peacefully"
            ),
        },
        "alimentacao_saudavel": {
            "foco": "food groups, fruits and vegetables, courage to try new textures",
            "vilao": "Queasy, who makes the child refuse anything new on the plate",
            "espaco": "the kitchen or garden at home, colorful with fruits and vegetables",
            "sequencia": (
                "a new, different food appears on the plate or in the garden → Queasy "
                "scrunches up the child's nose → the child uses curiosity to overcome Queasy "
                "→ discovers a new flavor → pride in having tried it"
            ),
        },
        "vestir_autonomia": {
            "foco": "identifying clothing items, buttons, zippers and shoes, and dressing independently",
            "vilao": "Impatience, who wants someone else to do it all",
            "espaco": "the closet or bedroom, with clothes spread out to choose from",
            "sequencia": (
                "the child needs to get dressed for something special → Impatience tries to "
                "make her give up at the first stuck button → the child tries again, slowly, "
                "piece by piece → manages to dress herself → pride in doing it on her own"
            ),
        },
        # ---- Self-Awareness & Social-Emotional Learning ----
        "literacia_emocional": {
            "foco": "naming big feelings — anger, sadness, frustration, joy",
            "vilao": "the day's big feeling itself, as a character (Anger, Sadness or Frustration)",
            "espaco": "a familiar, calm place, like the living room or the school yard",
            "sequencia": (
                "something doesn't go as the child wanted → the big feeling appears and grows "
                "→ the child tries to ignore it, but it only grows more → the child stops, "
                "names what she feels and takes a deep breath → the feeling shrinks and "
                "becomes a lesson"
            ),
        },
        "consciencia_corporal": {
            "foco": "names of body parts, what they do and basic spatial limits",
            "vilao": "the Absent-Minded, who makes the child not notice her own body",
            "espaco": "a free-play space, like the backyard or living room",
            "sequencia": (
                "an imitation game or dance begins → each body part comes into action (hands, "
                "feet, head) → the Absent-Minded tries to mess up the movements → the child "
                "pays attention to her own body and gets the rhythm right → the game ends "
                "with pride"
            ),
        },
        "compartilhar_revezar": {
            "foco": "parallel play, sharing and waiting your turn with kindness",
            "vilao": "Jealousy, who won't let go of the toy",
            "espaco": "a playground or playroom with another child nearby",
            "sequencia": (
                "a friend wants to play with the same toy → Jealousy clutches the toy close "
                "→ the child feels Jealousy, but remembers how fun it is to play together → "
                "offers to take turns or share → the two play together and have even more fun"
            ),
        },
        # ---- Discovery & Exploring the World ----
        "animais_sons": {
            "foco": "animal names and sounds, and their habitats (farm, ocean, jungle)",
            "vilao": "the Tangled Silence, who scrambles the animal sounds",
            "espaco": "a farm, forest or aquarium to visit",
            "sequencia": (
                "an animal sound escapes and no one knows whose it is → follow the sound to "
                "the right habitat → the Tangled Silence tries to mix it up with another "
                "animal → the child listens carefully and matches the animal to its sound → "
                "the whole habitat sings along"
            ),
        },
        "transporte_ajudantes": {
            "foco": "vehicles (truck, train, plane) and community figures (firefighter, doctor, mail carrier)",
            "vilao": "Lost-in-a-Hurry, who muddles the way to the right helper",
            "espaco": "a street or small town with different vehicles passing by",
            "sequencia": (
                "something needs to be delivered or solved quickly → the child picks the "
                "right vehicle for the trip → Lost-in-a-Hurry scrambles the route → the "
                "child stops, thinks and picks the right path with a community helper's "
                "guidance → mission delivered successfully"
            ),
        },
        "clima_estacoes": {
            "foco": "weather patterns (rain, sun, snow) and the right clothing for each season",
            "vilao": "Sudden-Chill (or Sudden-Sun), who changes the weather without warning",
            "espaco": "the backyard or a window showing the weather changing",
            "sequencia": (
                "the child gets ready to go out one way → the weather suddenly changes → the "
                "weather villain plays tricks on the right outfit → the child looks at the "
                "sky and picks the right clothing for the new season → heads out to play, "
                "ready and happy"
            ),
        },
    },
}


async def handle_story(db: Session, job: Job) -> None:
    project = _project(db, job)
    from app.services import book_profile

    if book_profile.enabled(project):
        from . import master_book

        await master_book.story(db, job, project)
        return
    _set_status(db, project, ProjectStatus.STORY_RUNNING)

    theme = project.theme or "adventure"
    extra_theme = (project.extra_theme or "").strip() or None
    if extra_theme == theme:
        extra_theme = None
    name = (project.child_name or "").strip()
    language = project.language or "pt-BR"
    is_en = (language or "").lower().startswith("en")
    if is_en:
        who = f"the child named {name}" if name else "the child from the photo"
        brief = (
            _payload(job).get("brief")
            or f"Invent an ORIGINAL, coherent story in the theme '{theme}': give {who} "
            "a small goal or problem, a journey with one or two obstacles and friends "
            "who help, a gentle climax and a warm ending with a subtle lesson (courage, "
            f"friendship or kindness). {who} is the hero from beginning to end."
            + (f" Use the name '{name}' for the hero throughout the whole story." if name else "")
        )
    else:
        who = f"a crianca chamada {name}" if name else "o personagem da foto"
        brief = (
            _payload(job).get("brief")
            or f"Invente uma historia ORIGINAL e coerente no tema '{theme}': de a {who} "
            "um pequeno objetivo ou problema, uma jornada com um ou dois obstaculos e "
            "amiguinhos que ajudam, um climax gentil e um final acolhedor com uma licao "
            f"sutil (coragem, amizade ou gentileza). {who} e o protagonista do inicio ao fim."
            + (
                f" Use o nome '{name}' como protagonista ao longo de toda a historia."
                if name
                else ""
            )
        )

    # Guia educativo do tema: foco, vilão, cenário e sequência da jornada.
    # Prioriza LEARNING_GOALS (temas educacionais estruturados); senão usa THEME_EDU
    # (aventura/datas comemorativas — foco e sequência embutidos nas strings).
    lang_key = "en" if is_en else "pt"
    goals = LEARNING_GOALS.get(lang_key, {}).get(theme)
    guides = THEME_EDU[lang_key]
    if goals:
        # Tema educacional estruturado: campos separados
        focus = goals["foco"]
        vilao = goals.get("vilao", "")
        espaco = goals.get("espaco", "")
        sequence = goals["sequencia"]
        if is_en:
            brief += " LEARNING (essential): the story must playfully TEACH — " + focus + "."
            if vilao:
                brief += f" The villain is {vilao}."
            if espaco:
                brief += f" Setting: {espaco}."
            brief += (
                " Weave 2 or 3 REAL, simple, age-appropriate facts about the theme into "
                "the action or dialogue (never lecture-like). MANDATORY LOGICAL SEQUENCE "
                "of the journey, adapted creatively: "
                + sequence
                + ". At the end, the hero happily realizes what they learned."
            )
        else:
            brief += (
                " APRENDIZADO (essencial): a história deve ENSINAR de forma lúdica — " + focus + "."
            )
            if vilao:
                brief += f" O vilão da jornada é {vilao}."
            if espaco:
                brief += f" Cenário: {espaco}."
            brief += (
                " Insira 2 ou 3 curiosidades REAIS, simples e adequadas à idade sobre "
                "o tema dentro da ação ou das falas (nunca em tom de aula). SEQUÊNCIA "
                "LÓGICA obrigatória da jornada, adaptada com criatividade: "
                + sequence
                + ". No final, o protagonista percebe com alegria o que aprendeu."
            )
    else:
        # Aventura/datas comemorativas: foco e sequência embutidos na string
        focus, sequence = guides.get(theme, guides["adventure"])
        if is_en:
            brief += (
                " LEARNING (essential): the story must playfully TEACH — "
                + focus
                + ". Weave 2 or 3 REAL, simple, age-appropriate facts about the theme into "
                "the action or dialogue (never lecture-like). MANDATORY LOGICAL SEQUENCE "
                "of the journey, adapted creatively: "
                + sequence
                + ". At the end, the hero happily realizes what they learned."
            )
        else:
            brief += (
                " APRENDIZADO (essencial): a história deve ENSINAR de forma lúdica — "
                + focus
                + ". Insira 2 ou 3 curiosidades REAIS, simples e adequadas à idade sobre "
                "o tema dentro da ação ou das falas (nunca em tom de aula). SEQUÊNCIA "
                "LÓGICA obrigatória da jornada, adaptada com criatividade: "
                + sequence
                + ". No final, o protagonista percebe com alegria o que aprendeu."
            )

    # Segundo tema opcional (máx. 2 por história): o tema principal continua com o
    # vilão/cenário/arco (sequência acima); o segundo tema só soma um objetivo de
    # aprendizado extra tecido na mesma jornada — nunca uma jornada paralela.
    if extra_theme:
        extra_goals = LEARNING_GOALS.get(lang_key, {}).get(extra_theme)
        extra_edu = guides.get(extra_theme)
        if extra_goals:
            extra_focus = extra_goals["foco"]
        elif extra_edu:
            extra_focus, _ = extra_edu
        else:
            extra_focus = None

        if extra_focus:
            if is_en:
                brief += (
                    " SECOND THEME (blend into the same journey, never a separate plot): "
                    "also playfully teach — " + extra_focus + ". Keep the primary theme's "
                    "setting, sequence and pace as the backbone; weave this second learning "
                    "goal into an existing beat of that same journey (a detail of the "
                    "setting, something a friend says or does, a small moment inside the "
                    "obstacle already planned) instead of adding a new scene. If each theme "
                    "implies a different villain, pick whichever fits this specific journey "
                    "better, or merge them into one coherent antagonist — never two separate "
                    "villains in the same story."
                )
            else:
                brief += (
                    " SEGUNDO TEMA (funda com a mesma jornada, nunca um enredo à parte): "
                    "ensine também, de forma lúdica — " + extra_focus + ". Mantenha o "
                    "espaço, a sequência e o ritmo do tema principal como espinha dorsal; "
                    "teça esse segundo objetivo de aprendizado dentro de um momento já "
                    "previsto dessa mesma jornada (um detalhe do cenário, algo que um "
                    "amiguinho diz ou faz, um instante dentro do obstáculo já planejado) "
                    "em vez de criar uma cena nova. Se cada tema sugerir um vilão "
                    "diferente, escolha o que fizer mais sentido para essa jornada "
                    "específica, ou funda os dois num só antagonista coerente — nunca dois "
                    "vilões separados na mesma história."
                )

    # Perfil educativo da criança: o traço central (o que a história transforma) e o
    # interesse/talento (a ferramenta que o herói usa para superar o vilão no clímax).
    trait = (project.child_trait or "").strip()
    interest = (project.child_interest or "").strip()
    if trait or interest:
        if is_en:
            brief += (
                " CHILD PROFILE (use it to shape the plot): "
                + (
                    f"the hero's starting trait is '{trait}' — this is the story's starting "
                    f"point, exactly what the journey transforms into growth. "
                    if trait
                    else ""
                )
                + (
                    f"the hero's talent/interest is '{interest}' — this is the tool the hero "
                    f"uses to name, calm or overcome the villain at the climax; never let an "
                    f"adult or luck solve it instead. "
                    if interest
                    else ""
                )
            )
        else:
            brief += (
                " PERFIL DA CRIANÇA (use para moldar o enredo): "
                + (
                    f"o traço inicial do herói é '{trait}' — esse é o ponto de partida da "
                    f"história, exatamente o que a jornada transforma em crescimento. "
                    if trait
                    else ""
                )
                + (
                    f"o talento/interesse do herói é '{interest}' — é a ferramenta que ele usa "
                    f"para nomear, acalmar ou superar o vilão no clímax; nunca deixe um adulto "
                    f"ou a sorte resolverem por ele. "
                    if interest
                    else ""
                )
            )

    size_cm = (
        "20×20 cm"
        if project.book_size == "M"
        else "15×15 cm"
        if project.book_size == "P"
        else "20×20 cm"
    )
    brief += (
        " FORMATO: livro quadrado "
        + size_cm
        + ", corte reto, páginas em sangria total. Cada página é uma estrofe curta, "
        "educativa, com leve rima só quando sair natural. " + book_art_direction(project.style)
    )
    update_trace(
        metadata={
            **job_metadata(job),
            "theme": theme,
            "language": language,
            "age": project.child_age,
        },
        input={"brief": brief[:2000], "theme": theme, "language": language},
        tags=["STORY"],
    )
    provider = _pkg().get_text_provider(job.provider)
    result = await provider.generate_story(
        brief=brief,
        style=book_art_direction(project.style),
        pages=settings.ebook_pages,
        language=language,
        age=project.child_age,
    )
    project.story_text = result.text
    job.cost_usd = result.cost_usd
    update_span(output={"story_chars": len(result.text or "")})
    await score_and_log_story(
        brief=brief,
        story=result.text,
        age=project.child_age,
        language=language,
        theme=theme,
    )
    _set_status(db, project, ProjectStatus.STORY_READY)

    # Storyboard alimenta o vídeo; na prévia automática pulamos (sem VIDEO).
    if not preview_chain.is_preview_chain(job):
        _enqueue_auto_storyboard(db, project, job)
    # Prévia automática: enfileira o ebook (trio OpenAI).
    preview_chain.continue_preview_chain(db, project, job, JobType.EBOOK)


def _enqueue_auto_storyboard(db: Session, project: Project, source_job: Job) -> None:
    """Agenda em background (sem custo) o roteiro completo do vídeo para este projeto.

    Idempotente por job de história: reprocessar o STORY não duplica o storyboard.
    """
    key = f"auto-storyboard-{source_job.id}"
    if db.scalar(select(Job).where(Job.idempotency_key == key)):
        return
    db.add(
        Job(
            project_id=project.id,
            type=JobType.STORYBOARD.value,
            status=JobStatus.PENDING.value,
            provider=settings.text_provider,
            idempotency_key=key,
            request_id=source_job.request_id,
            cost_credits=0,
            result={"payload": {"auto": True}},
        )
    )
    db.commit()


def _catalog_template_id(db: Session, project: Project) -> str | None:
    """template_id se a história veio do catálogo (último job STORY)."""
    job = db.scalar(
        select(Job)
        .where(
            Job.project_id == project.id,
            Job.type == JobType.STORY.value,
            Job.status == JobStatus.DONE.value,
        )
        .order_by(Job.created_at.desc())
    )
    if job is None or not isinstance(job.result, dict):
        return None
    if job.result.get("source") != "template":
        return None
    tid = (job.result.get("template_id") or "").strip()
    return tid or None


def _book_costume_line(briefs: list[dict], template_id: str | None, theme: str | None) -> str:
    for brief in briefs:
        line = (brief.get("costume") or "").strip()
        if line:
            return line
    return costume_extras_for_template(template_id) or costume_extras_for_theme(theme)


def _scene_to_brief(
    sc: dict, page_text: str, *, page_index: int = 0, layout: str = "story"
) -> dict:
    """Normaliza uma cena de storyboard num brief de pagina do ebook."""
    scene = (
        str(sc.get("scene") or "").strip()
        or str(sc.get("action") or "").strip()
        or str(sc.get("setting") or "").strip()
        or str(sc.get("image_prompt") or "").strip()
        or page_text
    )
    expression = normalize_expression(
        sc.get("expression") or sc.get("mood") or infer_expression(page_text, scene)
    )
    band = sc.get("text_band") or ("top" if page_index % 2 == 0 else "bottom")
    return {
        "n": int(sc.get("n") or page_index + 1),
        "scene": scene,
        "expression": expression,
        "shot": identity_shot(sc.get("shot"), layout=layout),
        "costume": str(sc.get("costume") or "").strip(),
        "text_band": normalize_text_band(band),
    }


def _fallback_page_briefs(
    pages: list[str],
    *,
    notes: list[str] | None = None,
    costume: str = "",
    layouts: list[str] | None = None,
) -> list[dict]:
    briefs = []
    for i, page in enumerate(pages):
        note = notes[i] if notes and i < len(notes) else ""
        scene = (note or page).strip()
        layout = layouts[i] if layouts and i < len(layouts) else "story"
        briefs.append(
            {
                "n": i + 1,
                "scene": scene,
                "expression": infer_expression(page, note),
                "shot": identity_shot(None, layout=layout),
                "costume": costume,
                "text_band": "left" if layout == "name" else ("top" if i % 2 == 0 else "bottom"),
            }
        )
    return briefs


def _save_storyboard_asset(db: Session, project: Project, sb: dict, *, auto: bool) -> None:
    key = storage.new_key(project.id, AssetKind.STORYBOARD.value, "json")
    storage.put_bytes(
        key, json.dumps(sb, ensure_ascii=False, indent=2).encode("utf-8"), "application/json"
    )
    db.add(
        Asset(
            project_id=project.id,
            kind=AssetKind.STORYBOARD.value,
            storage_key=key,
            meta={"scenes": len(sb.get("scenes") or []), "auto": auto},
        )
    )
    db.commit()


async def _compose_storyboard(
    db: Session,
    project: Project,
    pages: list[str],
    *,
    title: str,
    theme_combined: str,
    language: str,
    auto: bool = False,
    require_ai: bool = False,
    job: Job | None = None,
) -> dict:
    """Carrega o storyboard se bater com as paginas; senao gera (OpenAI ou fallback)."""
    existing = _latest_storyboard(db, project)
    if existing and len(existing.get("scenes") or []) == len(pages):
        return existing

    sb: dict | None = None
    text_provider = _pkg().get_text_provider()
    gen = getattr(text_provider, "generate_storyboard", None)
    if gen is not None:
        try:
            result = await gen(
                story=project.story_text,
                theme=theme_combined,
                title=title,
                language=language,
            )
            sb = _parse_storyboard_json(result.text)
            if job is not None:
                job.cost_usd = result.cost_usd
        except ProviderError as exc:
            if require_ai and exc.transient:
                raise
            sb = None
    if not sb:
        sb = _fallback_storyboard(pages, title=title, theme=theme_combined)

    extra_theme = (project.extra_theme or "").strip() or None
    theme = project.theme or "adventure"
    if extra_theme == theme:
        extra_theme = None
    sb.update(
        {
            "version": 1,
            "theme": theme,
            "extra_theme": extra_theme,
            "language": language,
            "title": sb.get("title") or title,
            "total_duration_s": sum(s.get("duration_s", 5) for s in sb["scenes"]),
        }
    )
    _save_storyboard_asset(db, project, sb, auto=auto)
    return sb


async def ensure_page_briefs(
    db: Session,
    project: Project,
    pages: list[str],
    *,
    template_id: str | None,
    notes: list[str],
    layouts: list[str] | None,
    language: str,
) -> list[dict]:
    """Roteiro visual por pagina: catálogo preserva illustration_notes na scene."""
    costume = (
        costume_extras_for_template(template_id)
        if template_id
        else costume_extras_for_theme(project.theme)
    )
    if template_id:
        briefs = _fallback_page_briefs(pages, notes=notes, costume=costume, layouts=layouts)
        for i, brief in enumerate(briefs):
            if i < len(notes) and (notes[i] or "").strip():
                brief["scene"] = notes[i].strip()
        return briefs

    title = _parse_title(project.story_text) or ""
    theme = project.theme or "adventure"
    extra_theme = (project.extra_theme or "").strip() or None
    if extra_theme == theme:
        extra_theme = None
    theme_combined = f"{theme} + {extra_theme}" if extra_theme else theme
    sb = await _compose_storyboard(
        db,
        project,
        pages,
        title=title,
        theme_combined=theme_combined,
        language=language,
        auto=True,
    )
    scenes = sb.get("scenes") or []
    briefs = []
    for i, page in enumerate(pages):
        sc = scenes[i] if i < len(scenes) else {}
        layout = layouts[i] if layouts and i < len(layouts) else "story"
        brief = _scene_to_brief(sc, page, page_index=i, layout=layout)
        if not brief.get("costume"):
            brief["costume"] = costume
        briefs.append(brief)
    return briefs


async def _store_bible_asset(
    db: Session, project: Project, kind: AssetKind, result: ImageResult
) -> bytes:
    key = storage.new_key(project.id, kind.value, _ext(result.mime_type))
    storage.put_bytes(key, result.image_bytes, result.mime_type)
    db.add(
        Asset(
            project_id=project.id,
            kind=kind.value,
            storage_key=key,
            meta={"mime": result.mime_type},
        )
    )
    return result.image_bytes


async def _generate_character_bible(
    db: Session,
    project: Project,
    provider,
    *,
    photo: bytes | None,
    avatar: bytes,
    costume: str,
    style: str,
    lines: list | None = None,
) -> tuple[dict[str, bytes], float]:
    """3 folhas (turnaround, expressoes, figurino) a partir do avatar.

    `photo` so entra se nao houver avatar: a foto ja foi absorvida no retrato.
    Best-effort: falha nao aborta o livro.
    """
    bible: dict[str, bytes] = {}
    costs: list[float] = []
    refs = [avatar] if avatar else [img for img in (photo,) if img]
    store_lock = asyncio.Lock()

    async def _one(kind: AssetKind, prompt: str, extra: list[bytes]) -> None:
        try:
            result = await provider.generate_character(
                prompt=prompt,
                reference_images=refs + extra,
                style=style,
            )
        except Exception:  # noqa: BLE001
            logger.warning("Ficha %s falhou; ebook segue sem ela", kind.value)
            return
        if not result or not result.image_bytes:
            return
        _tag_image(
            result,
            action="generate_character",
            label=f"Ficha — {kind.value}",
        )
        async with store_lock:
            costs.append(float(result.cost_usd or 0.0))
            if lines is not None:
                lines.extend(lines_of(result))
            bible[kind.value] = await _store_bible_asset(db, project, kind, result)

    await _one(AssetKind.CHARACTER_SHEET, CHARACTER_SHEET_PROMPT, [])
    sheet = bible.get(AssetKind.CHARACTER_SHEET.value)
    extra_sheet = [sheet] if sheet else []
    await asyncio.gather(
        _one(AssetKind.EXPRESSION_SHEET, EXPRESSION_SHEET_PROMPT, extra_sheet),
        _one(AssetKind.COSTUME_LOCK, costume_lock_prompt(costume), extra_sheet),
    )
    db.commit()
    return bible, add_usd(*costs)


def _scene_extra_refs(
    bible: dict[str, bytes], expression: str, *, style_ref: bytes | None = None
) -> list[bytes]:
    extras: list[bytes] = []
    costume = bible.get(AssetKind.COSTUME_LOCK.value)
    sheet = bible.get(AssetKind.CHARACTER_SHEET.value)
    expr_sheet = bible.get(AssetKind.EXPRESSION_SHEET.value)
    if costume:
        extras.append(costume)
    if sheet:
        extras.append(sheet)
    if expr_sheet and normalize_expression(expression) in EXPRESSION_SHEET_KEYS:
        extras.append(expr_sheet)
    if style_ref:
        extras.append(style_ref)
    return extras


async def _score_page_face(
    probe: bytes | None, scene: bytes, *, domain: str = "photo"
) -> float | None:
    """Nota do juiz da pagina, com retry. None so apos esgotar (STO-37).

    Caller usa None para disparar refine_scene; o portao fail-closed
    (`_judge_page`) recusa a pagina se a nota continuar ausente.
    """
    if not settings.ebook_face_match or not probe or not scene:
        return None
    attempts = max(1, settings.face_match_retries)
    for attempt in range(1, attempts + 1):
        try:
            score = await _pkg().score_face_match(probe, scene, domain=domain)
        except Exception as exc:  # noqa: BLE001 - retenta; portao fail-closed depois
            logger.warning(
                "Juiz de rosto da pagina falhou (tentativa %s/%s): %s",
                attempt,
                attempts,
                exc,
            )
            score = None
        else:
            if score is not None:
                return score
            logger.warning(
                "Juiz de rosto da pagina sem nota (tentativa %s/%s)",
                attempt,
                attempts,
            )
        if attempt < attempts:
            await asyncio.sleep(min(4.0, 0.8 * attempt))
    logger.warning("Juiz de rosto da pagina sem nota apos retry; segue para refine/portao")
    return None


async def _judge_page(lock: IdentityLock, scene: bytes, *, avatar: bytes | None):
    async def scorer(truth, scene_bytes, avatar=None, **_k):
        domain = "same" if avatar else "photo"
        return await _pkg().score_face_match(truth, scene_bytes, domain=domain, avatar=avatar)

    return await judge_identity(lock, scene, scorer=scorer)


async def lock_page_identity(
    provider,
    *,
    headed: ImageResult,
    avatar: bytes | None,
    photo: bytes | None,
    style: str,
    refine_first: bool = True,
    page_idx: int | None = None,
) -> tuple[ImageResult, float | None]:
    """Trava a cara da pagina: refine_scene OpenAI se a nota cair.

    A nota compara o AVATAR com a cena (mesmo estilo). Sem avatar, cai no
    recorte da foto. Sem passe Fal/PuLID — so edits GPT Image.
    `refine_first=False` quando o caller ja rodou refine_scene (script).
    """
    probe = avatar or photo
    domain = "same" if avatar else "photo"
    threshold = settings.ebook_avatar_match_min if avatar else settings.ebook_face_match_min
    judge = bool(settings.ebook_face_match and probe)
    last_score = await _score_page_face(probe, headed.image_bytes, domain=domain)
    if not judge:
        return headed, last_score

    def _below(score: float | None) -> bool:
        return score is not None and score < threshold

    needs_refine = _below(last_score) or last_score is None or last_score == 0.0
    if not (refine_first and needs_refine):
        return headed, last_score

    headed = await _refine_scene(provider, avatar or photo or b"", headed, style)
    if page_idx is not None:
        for line in lines_of(headed):
            if line.get("action") == "refine_scene":
                line["label"] = f"Página {page_idx} — refine avatar"
    last_score = await _score_page_face(probe, headed.image_bytes, domain=domain)
    return headed, last_score


async def _accept_illustrated_page(
    headed: ImageResult,
    *,
    spent_lines: list,
    style_lock: asyncio.Lock,
    good_style: list[bytes],
    last_score: float | None = None,
) -> ImageResult:
    async with style_lock:
        if headed.image_bytes not in good_style:
            good_style.append(headed.image_bytes)
    meta = dict(headed.meta or {})
    meta["usage_lines"] = spent_lines
    if last_score is not None:
        meta["face_score"] = last_score
        log_feedback("face_score", last_score, reason="page identity")
    headed.meta = meta
    return headed


@track(name="illustrate_page", capture_input=False, capture_output=False)
async def _illustrate_page(
    provider,
    *,
    idx: int,
    caption: str,
    brief: dict,
    extras: str,
    child_name: str,
    char_bytes: bytes,
    photo_bytes: bytes | None,
    bible: dict[str, bytes],
    style_lock: asyncio.Lock,
    good_style: list[bytes],
    art_style: str = BOOK_STYLE,
) -> ImageResult:
    """Cena no avatar; refine_scene OpenAI se o juiz achar o rosto fraco."""
    prompt = build_scene_prompt(
        page=idx,
        text=caption,
        scene=(brief.get("scene") or caption)[:900],
        expression=brief.get("expression"),
        extras=extras,
        child_name=child_name,
        shot=brief.get("shot") or "",
        text_band=brief.get("text_band") or "",
    )
    update_span(
        metadata={"action": "illustrate_page", "page": idx},
        input={"page": idx, "prompt": prompt, "caption": caption[:400]},
    )
    probe = char_bytes or photo_bytes
    threshold = settings.ebook_avatar_match_min if char_bytes else settings.ebook_face_match_min
    lock = build_identity_lock(
        character_ref=char_bytes,
        face_crop=photo_bytes,
        photo=photo_bytes,
    )
    judge = bool(settings.ebook_face_match and probe)
    attempts = 2 if judge else 1
    last_score: float | None = None
    last_verdict = None
    spent = 0.0
    spent_lines: list = []
    headed: ImageResult | None = None

    def _take(result: ImageResult) -> ImageResult:
        nonlocal spent, spent_lines
        spent = add_usd(spent, result.cost_usd)
        spent_lines = spent_lines + lines_of(result)
        result.cost_usd = spent
        return result

    for attempt in range(attempts):
        style_ref = None
        if attempt > 0:
            async with style_lock:
                if good_style:
                    style_ref = good_style[0]
        extra_refs = _scene_extra_refs(bible, brief.get("expression") or "", style_ref=style_ref)
        scene = await provider.generate_scene(
            prompt=prompt,
            character_ref=char_bytes,
            style=art_style,
            extra_refs=extra_refs or None,
        )
        _tag_image(
            scene,
            action="generate_scene",
            label=f"Página {idx} — geração" if attempt == 0 else f"Página {idx} — retry",
        )
        headed = scene
        if not judge:
            return await _accept_illustrated_page(
                _take(headed),
                spent_lines=spent_lines,
                style_lock=style_lock,
                good_style=good_style,
            )

        headed, last_score = await lock_page_identity(
            provider,
            headed=headed,
            avatar=char_bytes,
            photo=photo_bytes,
            style=BOOK_STYLE,
            refine_first=True,
            page_idx=idx,
        )
        last_verdict = await _judge_page(lock, headed.image_bytes, avatar=char_bytes)
        if last_verdict.accepted(threshold):
            return await _accept_illustrated_page(
                _take(headed),
                spent_lines=spent_lines,
                style_lock=style_lock,
                good_style=good_style,
                last_score=last_verdict.score if last_verdict.score is not None else last_score,
            )
        headed = _take(headed)

    assert headed is not None
    note = (
        f"{last_verdict.score:.2f}"
        if last_verdict is not None and last_verdict.score is not None
        else "sem nota"
    )
    why = (last_verdict.reason if last_verdict is not None else "") or "sem nota"
    raise ProviderError(
        f"Pagina {idx}: {IDENTITY_MISMATCH_ERROR} (nota={note}; {why})",
        transient=False,
    )


def _clear_page_images(db: Session, project: Project) -> None:
    old = db.scalars(
        select(Asset).where(
            Asset.project_id == project.id,
            Asset.kind == AssetKind.PAGE_IMAGE.value,
        )
    ).all()
    for asset in old:
        db.delete(asset)


def _set_job_progress(job: Job, *, stage: str, done: int, total: int) -> None:
    job.result = {
        **(job.result or {}),
        "progress": {"stage": stage, "done": done, "total": total},
    }


def _persist_page_image(db: Session, project: Project, idx: int, scene: ImageResult) -> None:
    img_key = storage.new_key(project.id, AssetKind.PAGE_IMAGE.value, _ext(scene.mime_type))
    storage.put_bytes(img_key, scene.image_bytes, scene.mime_type)
    db.add(
        Asset(
            project_id=project.id,
            kind=AssetKind.PAGE_IMAGE.value,
            storage_key=img_key,
            meta={"page": idx},
        )
    )


# --------------------------------------------------------------------------- #
# Etapa 12-13: storyboard (roteiro completo em JSON + keyframes para o video)
# --------------------------------------------------------------------------- #
_CAMERA_FALLBACK = [
    "aproximação lenta (push-in)",
    "panorâmica suave da esquerda para a direita",
    "travelling lateral acompanhando o protagonista",
    "zoom out revelando o cenário",
]


def _fallback_storyboard(pages: list[str], *, title: str, theme: str) -> dict:
    """Roteiro determinístico local (sem IA): uma cena por página da história."""
    scenes = []
    for i, page in enumerate(pages, 1):
        flat = page.replace("\n", " ").strip()
        first = re.split(r"(?<=[.!?])\s+", flat)[0] if flat else ""
        scenes.append(
            {
                "n": i,
                "narration": page.strip(),
                "setting": "",
                "action": first[:220],
                "scene": flat[:400],
                "expression": infer_expression(page),
                "shot": "medium",
                "costume": costume_extras_for_theme(theme.split(" + ")[0] if theme else None),
                "text_band": "top" if (i - 1) % 2 == 0 else "bottom",
                "camera": _CAMERA_FALLBACK[(i - 1) % len(_CAMERA_FALLBACK)],
                "mood": "",
                "duration_s": 5,
                "image_prompt": f"Cena {i} da história (tema {theme}): {flat[:400]}",
                "video_prompt": f"Anime a cena com movimento suave e expressivo: {first[:200]}",
            }
        )
    return {"title": title, "logline": "", "moral": "", "scenes": scenes}


def _parse_storyboard_json(text: str) -> dict | None:
    """Extrai e normaliza o JSON do roteiro (tolerante a cercas de código e texto extra)."""
    if not text:
        return None
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.DOTALL)
    m = re.search(r"\{.*\}", t, flags=re.DOTALL)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except Exception:  # noqa: BLE001 - JSON inválido -> caller usa fallback
        return None
    raw_scenes = data.get("scenes")
    if not isinstance(raw_scenes, list):
        return None
    scenes = []
    for i, sc in enumerate(raw_scenes, 1):
        if not isinstance(sc, dict):
            continue
        try:
            dur = int(sc.get("duration_s") or 5)
        except (TypeError, ValueError):
            dur = 5
        scenes.append(
            {
                "n": i,
                "narration": str(sc.get("narration") or "").strip(),
                "setting": str(sc.get("setting") or "").strip(),
                "action": str(sc.get("action") or "").strip(),
                "scene": str(
                    sc.get("scene") or sc.get("action") or sc.get("setting") or ""
                ).strip(),
                "expression": normalize_expression(sc.get("expression") or sc.get("mood")),
                "shot": normalize_shot(sc.get("shot")),
                "costume": str(sc.get("costume") or "").strip(),
                "text_band": normalize_text_band(sc.get("text_band")),
                "camera": str(sc.get("camera") or "").strip(),
                "mood": str(sc.get("mood") or "").strip(),
                "duration_s": min(8, max(4, dur)),
                "image_prompt": str(sc.get("image_prompt") or "").strip(),
                "video_prompt": str(sc.get("video_prompt") or "").strip(),
            }
        )
    if not scenes:
        return None
    return {
        "title": str(data.get("title") or "").strip(),
        "logline": str(data.get("logline") or "").strip(),
        "moral": str(data.get("moral") or "").strip(),
        "scenes": scenes,
    }


def _latest_storyboard(db: Session, project: Project) -> dict | None:
    """Carrega o roteiro mais recente do projeto (ou None)."""
    asset = db.scalar(
        select(Asset)
        .where(Asset.project_id == project.id, Asset.kind == AssetKind.STORYBOARD.value)
        .order_by(Asset.created_at.desc())
    )
    if not asset:
        return None
    try:
        return json.loads(storage.get_bytes(asset.storage_key).decode("utf-8"))
    except Exception:  # noqa: BLE001 - roteiro corrompido não deve travar o vídeo
        return None


async def handle_storyboard(db: Session, job: Job) -> None:
    """Gera o ROTEIRO COMPLETO (JSON) para o ebook e o vídeo.

    Não gera mais keyframes: o vídeo usa as page_image do ebook.
    """
    project = _project(db, job)
    if not (project.story_text or "").strip():
        raise ProviderError("Historia ausente: rode STORY antes", transient=False)

    language = project.language or "pt-BR"
    theme = project.theme or "adventure"
    extra_theme = (project.extra_theme or "").strip() or None
    if extra_theme == theme:
        extra_theme = None
    theme_combined = f"{theme} + {extra_theme}" if extra_theme else theme
    title = _parse_title(project.story_text) or ""
    pages = _parse_pages(project.story_text)
    await _compose_storyboard(
        db,
        project,
        pages,
        title=title,
        theme_combined=theme_combined,
        language=language,
        auto=bool(_payload(job).get("auto")),
        require_ai=True,
        job=job,
    )
