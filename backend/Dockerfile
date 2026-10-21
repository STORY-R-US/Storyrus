FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org && \
    pip install --no-cache-dir . --trusted-host pypi.org --trusted-host pypi.python.org --trusted-host files.pythonhosted.org

COPY . .

# Fonte do ebook: Megifera Indica (Risma Type) — baixada no build.
# Nao fatal: os hosts atuais exigem JS ou podem sair do ar; ebook.py cai no
# fallback (fontes base do reportlab) quando o TTF nao existe em runtime.
RUN python scripts/fetch_fonts.py || echo "[fonts] download falhou, seguindo com fallback"

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
