"""Exporta o codigo versionado da base ativa em um ZIP independente."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".local-storage",
    "coverage",
    "test-results",
    "playwright-report",
    ".expo",
    ".vercel",
}
SECRET_EXTENSIONS = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".dump",
    ".db",
    ".sqlite",
    ".sqlite3",
}
ENV_TEMPLATES = {".env.example", ".env.sample", ".env.template"}


def git(*args: str) -> bytes:
    executable = shutil.which("git")
    if executable is None:
        raise RuntimeError("Instale o Git para exportar os arquivos versionados.")
    return subprocess.check_output([executable, "-C", str(ROOT), *args])


def clean_repository() -> None:
    if git("status", "--porcelain").strip():
        raise RuntimeError("Registre as alteracoes da base antes de exportar o pacote.")


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def export(output: Path, metadata_dir: Path) -> dict:
    clean_repository()
    commit = git("rev-parse", "HEAD").decode().strip()
    paths = sorted(
        entry.decode("utf-8") for entry in git("ls-files", "-z").split(b"\0") if entry
    )
    files = []
    for relative in paths:
        path = ROOT / relative
        parts = Path(relative).parts
        if any(part in SKIP_PARTS for part in parts):
            raise RuntimeError(f"Artefato gerado inesperado no Git: {relative}")
        if path.suffix.lower() in SECRET_EXTENSIONS:
            raise RuntimeError(
                f"Arquivo reservado fora do pacote de codigo: {relative}"
            )
        if path.name.startswith(".env") and path.name not in ENV_TEMPLATES:
            raise RuntimeError(
                f"Arquivo de ambiente real nao pode ser exportado: {relative}"
            )
        if not path.is_file() or path.is_symlink():
            raise RuntimeError(f"Arquivo ausente ou link simbolico: {relative}")
        with path.open("rb") as stream:
            if stream.read(200).startswith(
                b"version https://git-lfs.github.com/spec/v1"
            ):
                raise RuntimeError(
                    f"Baixe o asset com Git LFS antes da exportacao: {relative}"
                )
        files.append((relative, path))

    required = {
        "backend/alembic/versions/0027_purchase_flow.py",
        "backend/app/routers/projects/purchase.py",
        "backend/app/services/purchase_flow.py",
        "apps/web/src/studio/PostPreviewFlow.tsx",
        "apps/web/src/studio/PrintCheckout.tsx",
        "apps/web/src/MyOrders.tsx",
    }
    if required - set(paths):
        raise RuntimeError(
            f"Fluxo de impressao incompleto: {sorted(required - set(paths))}"
        )

    output = output.resolve()
    metadata_dir = metadata_dir.resolve()
    if output.is_relative_to(ROOT) or metadata_dir.is_relative_to(ROOT):
        raise RuntimeError("Grave o ZIP e os metadados fora da pasta do repositorio.")
    output.parent.mkdir(parents=True, exist_ok=True)
    metadata_dir.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(output.name + ".partial")
    manifest = []
    with zipfile.ZipFile(
        temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=6
    ) as archive:
        for relative, path in files:
            name = f"Storyrus/{relative}"
            manifest.append(
                {
                    "arquivo": name,
                    "bytes": path.stat().st_size,
                    "sha256": digest_file(path),
                }
            )
            archive.write(path, name)
    with zipfile.ZipFile(temporary) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("A verificacao de integridade do ZIP falhou.")
        if len(archive.namelist()) != len(manifest):
            raise RuntimeError("A quantidade de arquivos do ZIP diverge do manifesto.")
        if {name.split("/")[0] for name in archive.namelist()} != {"Storyrus"}:
            raise RuntimeError("O pacote precisa conter uma unica pasta Storyrus.")
        for row in manifest:
            if (
                hashlib.sha256(archive.read(row["arquivo"])).hexdigest()
                != row["sha256"]
            ):
                raise RuntimeError(
                    f"O arquivo mudou durante a exportacao: {row['arquivo']}"
                )
    clean_repository()
    if git("rev-parse", "HEAD").decode().strip() != commit:
        raise RuntimeError(
            "O commit da base mudou durante a exportacao. Gere o pacote novamente."
        )
    os.replace(temporary, output)
    metadata = {
        "pasta": str(ROOT),
        "pacote": str(output),
        "commit": commit,
        "branch": git("branch", "--show-current").decode().strip(),
        "arquivos": len(manifest),
        "bytes_fontes": sum(row["bytes"] for row in manifest),
        "bytes_zip": output.stat().st_size,
        "sha256_zip": digest_file(output),
        "fluxo_impressao_incluido": True,
        "zip_verificado": True,
        "sem_ponteiros_lfs": True,
    }
    (metadata_dir / "manifesto-sha256.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (metadata_dir / "entrega.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--metadata-dir", required=True, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(export(args.output, args.metadata_dir), ensure_ascii=False, indent=2)
    )


if __name__ == "__main__":
    main()
