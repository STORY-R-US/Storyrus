FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
# Sem --trusted-host: o pip confere o TLS do PyPI (auditoria 25/11).
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

COPY . .

# Fonte do ebook: Megifera Indica (Risma Type) — baixada no build.
# Nao fatal: os hosts atuais exigem JS ou podem sair do ar; ebook.py cai no
# fallback (fontes base do reportlab) quando o TTF nao existe em runtime.
RUN python scripts/fetch_fonts.py || echo "[fonts] download falhou, seguindo com fallback"

# Roda sem root. /app e o HOME (cache de modelos) ficam graváveis pelo app.
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
