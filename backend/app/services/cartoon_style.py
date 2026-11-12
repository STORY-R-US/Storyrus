"""Shared Cartoon art direction; customer photos alone define identity."""

import re
from functools import lru_cache
from pathlib import Path

MARKER = "STORYRUS_CARTOON_BISAVO_V1"
DIRECTION = (
    f"{MARKER}: Cartoon 3D premium, ilustracao claramente DESENHADA no padrao visual de Amor de Bisavo. "
    "Rostos esculpidos suaves e reconheciveis, formas arredondadas, olhos expressivos "
    "com estilizacao moderada que preserva cor e formato dos olhos naturais, "
    "cabelo modelado delicadamente, luz difusa quente, "
    "cores coordenadas, tecidos tateis e cenarios ilustrados com textura sutil. "
    "Pessoa inteira em Cartoon coerente, sem rosto fotografico colado, filtro de foto, "
    "plastico brilhante, chibi ou caricatura extrema. Preserve idade, etnia, pele, "
    "cabelo, tracos individuais e anatomia; adulto continua adulto. Animais mantem "
    "raca, porte, pelagem, manchas, focinho e orelhas. A referencia Amor de Bisavo "
    "define SOMENTE estilo, nunca personagens, nomes, roupas, objetos ou historia. "
    "Capa quadrada e livro aberto com duas paginas quadradas; na LEITURA, pessoas "
    "e ambiente externos sao fotograficos e a capa Cartoon aprovada e impressa identica. "
    "PT, EN e ES preservam personagens, cenas, figurino e enquadramento; so o texto muda."
)


def applies(style: str | None) -> bool:
    value = (style or "").strip()
    # Do not activate for realistic directions containing 'sem cartoon'/'no cartoon'.
    return MARKER in value or bool(
        re.match(r"^(?:ilustra[cç][aã]o\s+)?cartoon\b|^premium\s+soft\s+cartoon\b", value, re.I)
    )


@lru_cache(maxsize=1)
def reference() -> bytes:
    return (
        Path(__file__).resolve().parents[1]
        / "assets/composition_examples/catalog_models/cartoon-8-cover.jpg"
    ).read_bytes()


def inputs(prompt: str, images: list[bytes], style: str) -> tuple[str, list[bytes]]:
    if not applies(style):
        return prompt, images
    if "COMPLETE CATALOG BOOK DESIGN" in prompt:
        # The caller supplies the selected model and may append saved art to edit.
        # An unrelated generic cover would change both style and LAST-image roles.
        return prompt, images
    note = (
        " ULTIMA IMAGEM: referencia de ESTILO Amor de Bisavo, nunca identidade. "
        "As imagens anteriores conservam os papeis indicados na tarefa. "
        "Nao copie pessoas, texto, nomes, figurino ou objetos da ultima imagem. "
        "Esta direcao Cartoon prevalece sobre instrucoes antigas de rosto fotografico. "
    )
    # Keep edit targets stable when a generic style guide is appended.
    prompt = prompt.replace("LAST ATTACHED IMAGE", f"IMAGE {len(images)}")
    prompt = prompt.replace("ÚLTIMA REFERÊNCIA", f"IMAGEM {len(images)}")
    return prompt + "\n" + DIRECTION + note, [*images, reference()]
