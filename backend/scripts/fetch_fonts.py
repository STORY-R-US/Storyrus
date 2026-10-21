"""Baixa a Megifera Indica (fonte do ebook) e salva os TTFs estaticos.

Fonte oficial do ebook: Megifera Indica — https://www.behance.net/gallery/217517361/Megifera-Indica
Designer: Risma Mulyasari (Risma Type).

Rodado automaticamente no build do Docker (ver Dockerfile). Para rodar local:
    cd backend
    python scripts/fetch_fonts.py

Saida: app/assets/fonts/MegiferaIndica-Regular.ttf e MegiferaIndica-Italic.ttf.
Idempotente: se os arquivos ja existem, nao baixa de novo.

NOTA: A maioria dos sites de fontes usa JavaScript para downloads.
Se o download automatico falhar, baixe manualmente de:
  - https://www.behance.net/gallery/217517361/Megifera-Indica
  - https://www.1001freefonts.com/megifera-indica.font
E coloque o TTF em: app/assets/fonts/MegiferaIndica-Regular.ttf
"""
from __future__ import annotations

import io
import sys
import urllib.request
import zipfile
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "app" / "assets" / "fonts"

# Megifera Indica — URLs de download (free for personal use)
# Todas as URLs usam JavaScript para download real; tentamos com headers de browser
FONT_URLS = [
    "https://exfont.com/downfile/5b8288396a26257218e2aa14f3d4e805.475737",
    "https://www.1001freefonts.com/d/63931/megifera-indica.zip",
    "https://www.cdnfonts.com/dl/megifera-indica",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/octet-stream,*/*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _download(url: str) -> bytes | None:
    """Tenta baixar a fonte; retorna None se falhar ou se o conteudo nao for fonte."""
    print(f"[fonts] tentando {url}")
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
            data = resp.read()
            ct = resp.headers.get("Content-Type", "")
            # Se retornou HTML, o download real requer JavaScript
            if data[:5] == b"<!DOC" or b"<html" in data[:200].lower():
                print(f"[fonts]   -> retornou HTML (download requer JavaScript)")
                return None
            if len(data) < 1000:
                print(f"[fonts]   -> arquivo muito pequeno ({len(data)} bytes), possivel erro")
                return None
            print(f"[fonts]   -> {len(data)} bytes, Content-Type: {ct}")
            return data
    except Exception as e:
        print(f"[fonts]   -> erro: {e}")
        return None


def _extract_ttf(data: bytes) -> bytes:
    """Se o dado for ZIP, extrai o primeiro TTF; senao retorna os dados originais."""
    if data[:4] == b"PK\x03\x04":
        print("[fonts]   -> arquivo ZIP, extraindo TTF...")
        zf = zipfile.ZipFile(io.BytesIO(data))
        for name in zf.namelist():
            if name.lower().endswith(".ttf") and "italic" not in name.lower():
                return zf.read(name)
        # Se nao encontrou TTF sem italic, pega qualquer TTF
        for name in zf.namelist():
            if name.lower().endswith(".ttf"):
                return zf.read(name)
    return data


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    dest = OUT_DIR / "MegiferaIndica-Regular.ttf"

    if dest.exists() and dest.stat().st_size > 0:
        print(f"[fonts] ja existe, pulando: {dest}")
        return 0

    for url in FONT_URLS:
        data = _download(url)
        if data is None:
            continue
        ttf_data = _extract_ttf(data)
        # Verifica se parece um TTF valido (magic number \x00\x01\x00\x00 ou OTF)
        if ttf_data[:4] in (b"\x00\x01\x00\x00", b"OTTO", b"ttcf"):
            dest.write_bytes(ttf_data)
            print(f"[fonts] salvo {dest} ({len(ttf_data)} bytes)")
            return 0
        print(f"[fonts]   -> formato nao identificado como TTF")

    # Se todas as URLs falharam, instrucao para download manual
    print("\n" + "=" * 60)
    print("[fonts] FALHA: Nao foi possivel baixar a fonte automaticamente.")
    print("[fonts] Download manual necessario:")
    print("[fonts]   1. Acesse: https://www.behance.net/gallery/217517361/Megifera-Indica")
    print("[fonts]   2. Baixe o arquivo ZIP (botao Download)")
    print("[fonts]   3. Extraia e copie MegiferaIndica-Regular.ttf para:")
    print(f"[fonts]      {dest}")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())
