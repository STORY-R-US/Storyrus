"""TextProvider real: Claude (Anthropic Messages API). Versos rimados por pagina."""

from __future__ import annotations

import httpx

from app.ai_clients.base import ProviderError, TextResult
from app.config import settings
from app.services.pricing import text_cost

_API_URL = "https://api.anthropic.com/v1/messages"
_VERSION = "2023-06-01"
_MODEL = "claude-opus-4-8"

_SYSTEM_PT = (
    "Você é um autor premiado de livros infantis personalizados (nível "
    "WonderWraps/TellMyTale). Escreva SEMPRE em português do Brasil impecável, com "
    "ortografia, gramática, pontuação e ACENTUAÇÃO corretas (nunca omita acentos: "
    "coração, você, céu, mãozinha).\n\n"
    "PERFIL DA CRIANÇA: quando o pedido trouxer um nome, uma idade, um TRAÇO CENTRAL "
    "(o ponto de partida que a história vai transformar) e um INTERESSE/TALENTO (a "
    "ferramenta que a criança usa para vencer o obstáculo), use-os como base do "
    'enredo — o traço central é o "antes"; a lição é o "depois". Nunca troque o '
    "traço central por outro no meio da história, e nunca deixe um adulto ou a sorte "
    "resolver o problema por ela: quem supera o obstáculo é a própria criança, usando "
    "o que já é seu.\n\n"
    "PERSONAGENS COMO CENÁRIO: cada personagem secundário funciona como peça de "
    "cenário — a descrição dele DEFINE que cena existe, nunca é decoração. O VILÃO da "
    "história pode ser um SENTIMENTO PERSONIFICADO (Medo-do-Escuro, Timidez, Ciúme, "
    "Vergonha, Impaciência, Frustração) para temas emocionais e de rotina, ou um "
    "DESAFIO-OBSTÁCULO concreto para temas de descoberta do mundo. Em ambos os casos, "
    'o vilão nunca é "mau" nem é destruído — ele é NOMEADO, COMPREENDIDO e ACALMADO '
    "(se sentimento) ou SUPERADO com o traço/interesse da própria criança (se "
    "obstáculo). É isso que torna a lição transferível para a vida real da criança.\n\n"
    "ESPAÇO: antes de escrever, construa o mundo da história em três camadas. (1) "
    "LUGAR MACRO em 1 frase — concreto e sensorial (fixe luz/hora do dia, cor "
    "dominante e som ambiente do lugar), o que ele já revela sobre o traço central "
    "da criança, e como contém literalmente o objetivo educacional (ex.: contar "
    "objetos → quarto cheio de blocos). (2) 2 ou 3 SUB-LUGARES dentro desse mundo "
    "(ex.: floresta → clareira → toca da raposa) para variar o enquadramento a cada "
    "página sem quebrar a coerência — nunca a mesma cena repetida do início ao fim. "
    "(3) A TOCA DO VILÃO: onde o sentimento ou obstáculo mora ou aparece dentro "
    "desse espaço (o canto escuro do quarto, a poça funda do riacho) — o vilão "
    "pertence ao mundo, não surge do nada. No clímax, o espaço ganha um detalhe "
    'novo CONCRETO e visível (nunca abstrato: não basta "algo mudou", diga o QUE '
    "mudou — a luz que entra pela primeira vez, o brinquedo agora dividido em cima "
    "da cama) — sinal visual direto de que a criança se transformou.\n\n"
    "HISTÓRIA (o mais importante): antes de escrever, planeje mentalmente um ENREDO "
    "COERENTE com começo, meio e fim — o espaço definido acima, um pequeno OBJETIVO "
    "ligado ao traço central da criança, uma jornada com 1 ou 2 obstáculos e o vilão "
    "(sentimento ou desafio), um clímax gentil onde a criança usa seu próprio "
    "traço/interesse para superar, e um final acolhedor com a lição sentida, não "
    "explicada. Cada página AVANÇA a história de forma lógica e se conecta à anterior "
    "— nunca cenas soltas, aleatórias ou sem nexo. O protagonista é o mesmo do início "
    "ao fim, com o mesmo nome. Seja concreto e sensorial (lugares, cores, sons), com "
    "ternura e sem medo, sempre adequado à IDADE indicada no pedido (se nenhuma idade "
    "for informada, escreva para 3 a 7 anos).\n\n"
    "FLUXO E RITMO: estruture as páginas em 5 fases — ABERTURA (~15%, ritmo calmo: "
    "criança + espaço + traço central), GATILHO (logo após: nasce o pequeno "
    "objetivo/desejo), CONTENÇÃO (~45-50%, ritmo cresce aos poucos: 1-2 obstáculos, o "
    "vilão aparece e cresce, a criança tenta e erra), CLÍMAX (1 página, pico breve: a "
    "criança nomeia/acalma/supera o vilão com seu próprio traço), RESOLUÇÃO (~15-20%, "
    "ritmo desacelera: o espaço muda de leve, final caloroso). TRANSIÇÃO: a última "
    "imagem ou verso de cada página deve plantar uma semente (som, pergunta, "
    "movimento) que a página seguinte responde — nunca feche uma página com um ponto "
    'final "morto".\n\n'
    "CRIATIVIDADE E ENCANTAMENTO: abra a página 1 com um GANCHO irresistível que dê "
    "vontade de virar a página. Crie um momento de DESCOBERTA ou uma pequena SURPRESA "
    "no meio, aumente a emoção e a tensão gentil até um CLÍMAX triunfante, e termine "
    "com um final memorável e afetuoso que dê um friozinho gostoso na barriga. Use "
    "imagens vívidas e inesperadas, palavras sonoras (plim!, zup!, splash!), um toque "
    "de humor ou magia, vocabulário rico e ideias ORIGINAIS — nada de clichês nem "
    "histórias repetidas. Cada livro deve ser único, emocionante e inesquecível.\n\n"
    "EDUCATIVO: cada história também ENSINA. Entrelace à ação e às falas as "
    "curiosidades verdadeiras pedidas no brief — a criança aprende brincando, sem "
    "tom de aula. Use o nome certo das coisas (animais, plantas, planetas, "
    "instrumentos) com uma explicação simples de 1 frase, e faça o final retomar "
    'com leveza o que o herói descobriu e sentiu — não apenas "aprendeu", mas '
    "sentiu na pele.\n\n"
    "FORMA: cada página é uma ESTROFE CURTA de 2 a 4 versos, musical, no máximo "
    "~40 palavras, descrevendo UMA cena visual clara (lugar + ação do protagonista).\n\n"
    "REGRA DE OURO DO SENTIDO: cada verso deve ser uma frase NATURAL do português, "
    "na ordem direta (sujeito + verbo + complemento), que faria sentido perfeito lida "
    "em voz alta como prosa. A rima é um enfeite, nunca o objetivo: use rima (AABB ou "
    "ABCB) apenas quando ela vier naturalmente; é PROIBIDO inverter a ordem das "
    "palavras, escolher palavras estranhas ao contexto ou sacrificar a lógica da cena "
    "só para rimar. Verso solto e claro vale mais que rima forçada e confusa.\n\n"
    "REVISÃO FINAL (obrigatória): antes de responder, releia a história inteira como "
    "se fosse prosa, do título à última página, e reescreva qualquer verso confuso, "
    "incoerente, sem nexo com a cena ou com rima forçada. Confira que: (1) a "
    "sequência de eventos faz sentido de uma página para a outra; (2) o final "
    "resolve o objetivo apresentado no começo; (3) o vilão foi nomeado e "
    "acalmado/superado pelo próprio traço da criança, não por um adulto ou pela "
    "sorte; (4) o espaço mudou de leve no clímax.\n\n"
    "Responda APENAS com o texto pedido — sem notas, comentários ou sugestões de imagem."
)
_SYSTEM_EN = (
    "You are an award-winning author of premium personalized children's books "
    "(WonderWraps/TellMyTale level). Write ALWAYS in flawless English.\n\n"
    "CHILD PROFILE: when the request includes a name, an age, a STARTING TRAIT (the "
    "starting point the story will transform) and a TALENT/INTEREST (the tool the "
    "child uses to overcome the obstacle), build the plot around them — the starting "
    'trait is the "before"; the lesson is the "after". Never swap the starting trait '
    "for another one mid-story, and never let an adult or luck solve the problem for "
    "her: the child overcomes the obstacle herself, using what is already hers.\n\n"
    "CHARACTERS AS SETTING: every side character works as a piece of set design — "
    "their description DEFINES which scene exists, never mere decoration. The "
    "VILLAIN of the story can be a PERSONIFIED FEELING (Fear-of-the-Dark, Shyness, "
    "Jealousy, Shame, Impatience, Frustration) for emotional and routine themes, or a "
    "concrete CHALLENGE-OBSTACLE for world-discovery themes. Either way, the villain "
    'is never "evil" nor destroyed — it is NAMED, UNDERSTOOD and CALMED (if a '
    "feeling) or OVERCOME with the child's own trait/interest (if an obstacle). "
    "That's what makes the lesson transferable to the child's real life.\n\n"
    "SETTING: before writing, build the story's world in three layers. (1) The "
    "MACRO PLACE in 1 sentence — concrete and sensory (fix the light/time of day, "
    "dominant color and ambient sound of the place), what it already reveals about "
    "the child's starting trait, and how it literally contains the learning goal "
    "(e.g., counting objects → a room full of blocks). (2) 2 or 3 SUB-LOCATIONS "
    "inside that world (e.g., forest → clearing → the fox's den) to vary the framing "
    "page by page without breaking coherence — never the same scene repeated start "
    "to finish. (3) The VILLAIN'S LAIR: where the feeling or obstacle lives or "
    "appears within that space (the dark corner of the room, the deep puddle in the "
    "creek) — the villain belongs to the world, it doesn't come from nowhere. At the "
    "climax, the setting gains one new CONCRETE, visible detail (never abstract — "
    'don\'t just say "something changed", say WHAT changed: the light coming in for '
    "the first time, the toy now shared on the bed) — a direct visual sign that the "
    "child has transformed.\n\n"
    "STORY (most important): before writing, mentally plan a COHERENT plot with a "
    "beginning, middle and end — the setting defined above, a small GOAL tied to the "
    "child's starting trait, a journey with 1 or 2 obstacles and the villain (feeling "
    "or challenge), a gentle climax where the child uses her own trait/interest to "
    "overcome it, and a warm ending with the lesson felt, not explained. Each page "
    "ADVANCES the story logically and connects to the previous one — never random, "
    "disconnected or nonsensical scenes. The hero stays the same throughout, with the "
    "same name. Be concrete and sensory (places, colors, sounds), warm and never "
    "scary, always suited to the AGE stated in the request (if no age is given, "
    "write for ages 3-7).\n\n"
    "FLOW AND PACING: structure the pages in 5 phases — OPENING (~15%, calm pace: "
    "child + setting + starting trait), TRIGGER (right after: the small goal/wish is "
    "born), BUILD-UP (~45-50%, pace grows gradually: 1-2 obstacles, the villain "
    "appears and grows, the child tries and stumbles), CLIMAX (1 page, brief peak: "
    "the child names/calms/overcomes the villain with her own trait), RESOLUTION "
    "(~15-20%, pace slows: the setting shifts slightly, warm ending). TRANSITION: the "
    "last image or line of each page must plant a seed (a sound, a question, a "
    'movement) that the next page answers — never close a page on a "dead" full '
    "stop.\n\n"
    "CREATIVITY AND WONDER: open page 1 with an irresistible HOOK that makes the "
    "reader want to turn the page. Add a moment of DISCOVERY or a small SURPRISE in "
    "the middle, build emotion and gentle tension to a triumphant CLIMAX, and end "
    "with a memorable, heart-warming finish that gives a delightful tingle. Use vivid, "
    "unexpected imagery, playful sound words (plink!, whoosh!, splash!), a touch of "
    "humor or magic, rich vocabulary and ORIGINAL ideas — no clichés or repeated "
    "plots. Every book must be unique, exciting and unforgettable.\n\n"
    "EDUCATIONAL: every story also TEACHES. Weave the true facts requested in the "
    "brief into the action and dialogue — the child learns while playing, never "
    "lectured. Name things correctly (animals, plants, planets, tools) with a simple "
    "one-sentence explanation, and let the ending lightly revisit what the hero "
    'discovered and felt — not just "learned", but felt firsthand.\n\n'
    "FORM: each page is a SHORT STANZA of 2 to 4 lines, musical, at most ~40 words, "
    "depicting ONE clear visual scene (place + the hero's action).\n\n"
    "GOLDEN RULE OF MEANING: every line must be a NATURAL English sentence, in "
    "direct order (subject + verb + complement), that would read perfectly as prose "
    "aloud. Rhyme is decoration, never the goal: rhyme (AABB or ABCB) only when it "
    "comes naturally; it is FORBIDDEN to invert word order, pick words foreign to the "
    "scene, or sacrifice the logic of the moment just to rhyme. A clear unrhymed line "
    "beats a forced, confusing rhyme.\n\n"
    "FINAL REVISION (mandatory): before replying, re-read the whole story as prose, "
    "from title to last page, and rewrite any line that is confusing, incoherent, "
    "disconnected from its scene, or forced into rhyme. Check that: (1) events flow "
    "logically page to page; (2) the ending resolves the goal set at the start; (3) "
    "the villain was named and calmed/overcome by the child's own trait, not by an "
    "adult or luck; (4) the setting shifted slightly at the climax.\n\n"
    "Reply ONLY with the requested text — no notes, comments or image suggestions."
)


def _lang(language: str | None) -> str:
    return "en" if (language or "").lower().startswith("en") else "pt-BR"


# --------------------------------------------------------------------------- #
# Adequação por idade: tom, vocabulário, forma e intensidade da aventura.
# --------------------------------------------------------------------------- #
def _age_rules(age: int | None, lang: str) -> str:
    if age is None:
        return ""
    if lang == "en":
        if age <= 2:
            rules = (
                "Baby/toddler book: NO plot or conflict — just one warm discovery in a "
                "familiar setting. Very short lines (3 to 7 words), lots of repetition "
                "and playful sounds (boom!, splash!), everyday words the child already "
                "knows, at most ~20 words per page. Soothing, sing-song, ideal to read aloud."
            )
        elif age <= 4:
            rules = (
                "Preschool: ONE small, concrete problem and a very simple, linear plot. "
                "Short sentences in direct order, familiar vocabulary, repetition and easy "
                "natural rhymes, zero scary moments. Emotions named simply (happy, curious)."
            )
        elif age <= 7:
            rules = (
                "Ages 5-7: a real little adventure with 1-2 obstacles, light humor and "
                "wonder. Rich but accessible vocabulary (explain any new word through the "
                "scene), gentle tension always resolved warmly."
            )
        elif age <= 10:
            rules = (
                "Ages 8-10: a layered plot with a twist or clever surprise, real stakes and "
                "smart humor. Broad vocabulary, varied sentences, NO babyish tone or "
                "excessive diminutives. The hero solves the problem through own ideas and effort."
            )
        else:
            rules = (
                "Preteen (11-12): confident, adventurous tone with a real challenge, "
                "dilemma and agency. Witty dialogue, no cutesy language at all, richer "
                "vocabulary and imagery. The lesson stays implicit in the action, never spelled out."
            )
        return (
            f"\nREADER AGE: the child is {age} years old. Adapt tone, vocabulary, plot "
            f"complexity and emotional intensity strictly to this age. {rules}\n"
        )
    if age <= 2:
        rules = (
            "Livro de bebê: SEM enredo ou conflito — apenas uma descoberta carinhosa num "
            "cenário familiar. Versos bem curtos (3 a 7 palavras), muita repetição e sons "
            "divertidos (bum!, splash!), palavras do dia a dia que a criança já conhece, "
            "no máximo ~20 palavras por página. Ritmo de cantiga, gostoso de ler em voz alta."
        )
    elif age <= 4:
        rules = (
            "Pré-escola: UM problema pequeno e concreto e um enredo bem simples e linear. "
            "Frases curtas na ordem direta, vocabulário familiar, repetição e rimas fáceis "
            "e naturais, nenhum momento assustador. Emoções nomeadas de forma simples "
            "(feliz, curioso)."
        )
    elif age <= 7:
        rules = (
            "5 a 7 anos: uma pequena aventura de verdade com 1 ou 2 obstáculos, humor leve "
            "e encantamento. Vocabulário rico mas acessível (explique palavra nova pela "
            "própria cena), tensão gentil sempre resolvida com acolhimento."
        )
    elif age <= 10:
        rules = (
            "8 a 10 anos: enredo com camadas, uma reviravolta ou surpresa inteligente, "
            "desafio real e humor esperto. Vocabulário amplo, frases variadas, SEM tom de "
            "bebê nem diminutivos em excesso. O herói resolve o problema com as próprias "
            "ideias e esforço."
        )
    else:
        rules = (
            "Pré-adolescente (11-12): tom confiante e aventureiro, com desafio real, "
            "dilema e protagonismo. Diálogos espertos, nada de linguagem infantilizada, "
            "vocabulário e imagens mais ricos. A lição fica implícita na ação, nunca "
            "explicada."
        )
    return (
        f"\nIDADE DO LEITOR: a criança tem {age} anos. Adapte tom, vocabulário, "
        f"complexidade do enredo e intensidade emocional exatamente a essa idade. {rules}\n"
    )


class AnthropicTextProvider:
    name = "claude"

    def __init__(self, api_key: str | None = None, timeout: float = 180.0):
        self._api_key = api_key or settings.anthropic_api_key
        self._timeout = timeout
        self.last_cost_usd: float | None = None

    async def generate_story(
        self,
        *,
        brief: str,
        style: str,
        pages: int,
        language: str = "pt-BR",
        age: int | None = None,
    ) -> TextResult:
        if not self._api_key:
            raise ProviderError("ANTHROPIC_API_KEY ausente", transient=False)

        lang = _lang(language)
        age_block = _age_rules(age, "en" if lang == "en" else "pt")
        if lang == "en":
            system = _SYSTEM_EN
            user = (
                f"Visual style: {style}. Number of pages: {pages}.\n"
                f"Character/theme brief: {brief}\n"
                f"{age_block}\n"
                "First, silently plan an original, coherent plot within the theme: a goal "
                "or small problem, a journey with an obstacle and friends who help, a gentle "
                "climax and a warm resolution with a subtle lesson. Then structure it across "
                f"the {pages} pages: page 1 introduces the hero and the world; the middle "
                "pages develop the adventure and the challenge; the last page gives a warm, "
                "satisfying ending. Every page must follow logically from the previous one.\n\n"
                "Return EXACTLY in this format:\n"
                f"Line 1 => 'Título: <book title featuring the hero's name, e.g. "
                f'"NAME and the Great Adventure">\'.\n'
                f"Then exactly {pages} pages, each starting with 'Página N:' followed by "
                "the stanza (2-4 short, natural lines; rhyme only when effortless). "
                "No image suggestions."
            )
        else:
            system = _SYSTEM_PT
            user = (
                f"Estilo visual: {style}. Número de páginas: {pages}.\n"
                f"Brief do personagem/tema: {brief}\n"
                f"{age_block}\n"
                "Primeiro, planeje em silêncio um enredo ORIGINAL e coerente dentro do "
                "tema: um objetivo ou pequeno problema, uma jornada com um obstáculo e "
                "amiguinhos que ajudam, um clímax gentil e um desfecho caloroso com uma "
                "lição sutil. Depois estruture nas "
                f"{pages} páginas: a página 1 apresenta o protagonista e o mundo; as "
                "páginas do meio desenvolvem a aventura e o desafio; a última traz um "
                "final acolhedor e satisfatório. Cada página deve seguir logicamente da "
                "anterior, sem cenas soltas.\n\n"
                "Devolva EXATAMENTE neste formato:\n"
                "Linha 1 => 'Título: <título do livro com o nome do protagonista, ex.: "
                '"NOME e a Grande Aventura">\'.\n'
                f"Depois exatamente {pages} páginas, cada uma iniciada por 'Página N:' "
                "seguida da estrofe (2 a 4 versos curtos e naturais; rime só quando sair "
                "sem esforço). Português do Brasil com acentuação correta, sem sugestões "
                "de imagem."
            )
        payload = {
            "model": _MODEL,
            "max_tokens": 4000,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _VERSION,
            "content-type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_API_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha de rede: {exc}", transient=True) from exc

        if resp.status_code in (429, 500, 502, 503, 504):
            raise ProviderError(
                f"Anthropic {resp.status_code}", transient=True, status_code=resp.status_code
            )
        if resp.status_code >= 400:
            raise ProviderError(
                f"Anthropic {resp.status_code}: {resp.text[:300]}",
                transient=False,
                status_code=resp.status_code,
            )

        data = resp.json()
        text = "".join(
            block.get("text", "")
            for block in data.get("content", [])
            if block.get("type") == "text"
        )
        usage = data.get("usage", {})
        return TextResult(
            text=text,
            cost_usd=text_cost(usage),
            meta={"usage": usage, "model": _MODEL},
        )

    async def generate_storyboard(
        self, *, story: str, theme: str, title: str = "", language: str = "pt-BR"
    ) -> TextResult:
        """Gera o ROTEIRO COMPLETO (storyboard) do vídeo a partir da história pronta.

        Retorna JSON com uma cena por página: narração, cenário, ação, câmera,
        clima, duração e prompts de imagem/vídeo — insumo para gerar o vídeo depois.
        """
        if not self._api_key:
            raise ProviderError("ANTHROPIC_API_KEY ausente", transient=False)

        if _lang(language) == "en":
            system = (
                "You are a senior children's picture-book art director AND animation "
                "scriptwriter. You receive a finished picture-book story and return "
                "the COMPLETE storyboard used both to illustrate each page and to "
                "produce a narrated animated video. Reply ONLY with valid UTF-8 JSON — "
                "no markdown, no comments, no extra text."
            )
            user = (
                f"Title: {title}\nTheme: {theme}\n\nSTORY (one page per stanza):\n{story}\n\n"
                "Build the full storyboard for this story (picture book + video).\n"
                "Rules:\n"
                "- One scene per page, in the SAME order (do not skip pages).\n"
                "- narration: the page text, proofread — it will be read aloud.\n"
                "- setting and action: concrete and visual (place, light, what the hero does).\n"
                "- scene: one visual description to ILLUSTRATE the page (composition, "
                "who is where, key object). This is what the image model follows.\n"
                "- expression: one of alegria, curiosidade, medo_gentil, determinacao, "
                "surpresa, calma, tristeza_leve, concentracao, carinho, orgulho, "
                "vergonha, animacao.\n"
                "- shot: one of close, medium, wide, detail.\n"
                "- costume: ONE short line for the whole book (story outfit, not the "
                "photo clothes). Repeat the SAME costume on every scene.\n"
                "- text_band: top or bottom — empty band of the frame for the printed stanza.\n"
                "- camera: one simple move (slow push-in, pan, lateral tracking, zoom out...).\n"
                "- mood: the emotional tone of the scene.\n"
                "- duration_s: integer from 4 to 8.\n"
                "- image_prompt: detailed prompt to illustrate the scene (same hero "
                "as the reference image; story costume, not the photo outfit).\n"
                "- video_prompt: 1-2 sentences describing the scene motion for an "
                "image-to-video generator.\n"
                "- logline: one-sentence summary. moral: what the child learns.\n"
                "Reply ONLY with valid JSON in this format:\n"
                '{"title": "...", "logline": "...", "moral": "...", "scenes": [{"n": 1, '
                '"narration": "...", "setting": "...", "action": "...", "scene": "...", '
                '"expression": "alegria", "shot": "medium", "costume": "...", '
                '"text_band": "bottom", "camera": "...", "mood": "...", "duration_s": 5, '
                '"image_prompt": "...", "video_prompt": "..."}]}'
            )
        else:
            system = (
                "Você é diretor de arte de livro infantil E roteirista de animação. "
                "Recebe a história pronta e devolve o ROTEIRO COMPLETO (storyboard) "
                "usado tanto para ilustrar cada página quanto para o vídeo narrado. "
                "Responda APENAS com JSON válido em UTF-8 — sem markdown, sem "
                "comentários, sem texto extra."
            )
            user = (
                f"Título: {title}\nTema: {theme}\n\nHISTÓRIA (uma página por estrofe):\n{story}\n\n"
                "Monte o roteiro completo desta história (livro ilustrado + vídeo).\n"
                "Regras:\n"
                "- Uma cena por página, na MESMA ordem (não pule páginas).\n"
                "- narration: o texto da página revisado (ortografia e acentos perfeitos) — "
                "será narrado em voz alta.\n"
                "- setting e action: concretos e visuais (lugar, luz, o que o protagonista faz).\n"
                "- scene: uma descrição visual para ILUSTRAR a página (composição, quem "
                "está onde, objeto-chave). É o que o modelo de imagem segue.\n"
                "- expression: uma de alegria, curiosidade, medo_gentil, determinacao, "
                "surpresa, calma, tristeza_leve, concentracao, carinho, orgulho, "
                "vergonha, animacao.\n"
                "- shot: uma de close, medium, wide, detail.\n"
                "- costume: UMA linha só para o livro inteiro (figurino da história, "
                "não a roupa da foto). Repita o MESMO figurino em todas as cenas.\n"
                "- text_band: top ou bottom — faixa vazia do quadro para a estrofe impressa.\n"
                "- camera: um movimento simples (aproximação lenta, panorâmica, travelling "
                "lateral, zoom out...).\n"
                "- mood: o clima emocional da cena.\n"
                "- duration_s: inteiro de 4 a 8.\n"
                "- image_prompt: prompt detalhado para ilustrar o keyframe da cena (mesmo "
                "protagonista da imagem de referência; figurino da história, não a roupa da foto).\n"
                "- video_prompt: 1-2 frases descrevendo o movimento da cena para um gerador "
                "de vídeo image-to-video.\n"
                "- logline: resumo de 1 frase. moral: o que a criança aprende.\n"
                "Responda SOMENTE com JSON válido neste formato:\n"
                '{"title": "...", "logline": "...", "moral": "...", "scenes": [{"n": 1, '
                '"narration": "...", "setting": "...", "action": "...", "scene": "...", '
                '"expression": "alegria", "shot": "medium", "costume": "...", '
                '"text_band": "bottom", "camera": "...", "mood": "...", "duration_s": 5, '
                '"image_prompt": "...", "video_prompt": "..."}]}'
            )

        payload = {
            "model": _MODEL,
            "max_tokens": 8000,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _VERSION,
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_API_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha de rede: {exc}", transient=True) from exc
        if resp.status_code in (429, 500, 502, 503, 504):
            raise ProviderError(
                f"Anthropic {resp.status_code}", transient=True, status_code=resp.status_code
            )
        if resp.status_code >= 400:
            raise ProviderError(
                f"Anthropic {resp.status_code}: {resp.text[:300]}",
                transient=False,
                status_code=resp.status_code,
            )
        data = resp.json()
        text = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )
        usage = data.get("usage", {})
        return TextResult(
            text=text,
            cost_usd=text_cost(usage),
            meta={"usage": usage, "model": _MODEL},
        )

    async def summarize_pages(
        self, *, pages: list[str], style: str = "", language: str = "pt-BR"
    ) -> list[str]:
        """Resume cada trecho da historia numa legenda curta (1 frase) por pagina.

        Retorna uma lista do mesmo tamanho de `pages`. O texto integral continua
        sendo usado para ILUSTRAR (contexto completo); a legenda e o que aparece
        impresso na pagina do e-book.
        """
        if not self._api_key:
            raise ProviderError("ANTHROPIC_API_KEY ausente", transient=False)
        if not pages:
            return []

        numbered = "\n\n".join(f"[{i + 1}] {p}" for i, p in enumerate(pages))
        if _lang(language) == "en":
            system = (
                "You write short captions for an illustrated children's book, in correct "
                "ENGLISH. For each excerpt, write ONE short, warm, child-friendly sentence "
                "that will be printed on that page. PROOFREAD spelling, grammar and "
                "punctuation. Reply ONLY with the captions, one per line, in the same "
                "order, without numbering or quotes."
            )
            user = f"One caption per excerpt, in order ({len(pages)} excerpts):\n\n{numbered}"
        else:
            system = (
                "Voce escreve legendas curtas para um livro infantil ilustrado, em "
                "PORTUGUES DO BRASIL correto. Para cada trecho recebido, escreva UMA frase "
                "curta, calorosa e adequada a criancas, que sera o texto impresso naquela "
                "pagina. REVISE e CORRIJA ortografia, gramatica, pontuacao e acentuacao — a "
                "legenda final deve estar perfeita em portugues, mesmo que o trecho original "
                "tenha erros. Responda APENAS com as legendas, uma por linha, na mesma ordem, "
                "sem numeracao e sem aspas."
            )
            user = f"Gere uma legenda por trecho, na ordem ({len(pages)} trechos):\n\n{numbered}"
        payload = {
            "model": _MODEL,
            "max_tokens": 1500,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": _VERSION,
            "content-type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(_API_URL, json=payload, headers=headers)
        except httpx.RequestError as exc:
            raise ProviderError(f"Falha de rede: {exc}", transient=True) from exc
        if resp.status_code in (429, 500, 502, 503, 504):
            raise ProviderError(f"Anthropic {resp.status_code}", transient=True)
        if resp.status_code >= 400:
            raise ProviderError(f"Anthropic {resp.status_code}: {resp.text[:200]}", transient=False)

        data = resp.json()
        text = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )
        usage = data.get("usage", {})
        self.last_cost_usd = text_cost(usage)
        lines = [ln.strip(" -•\t").strip() for ln in text.splitlines() if ln.strip()]
        return lines
