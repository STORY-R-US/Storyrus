"""Run checks with local test settings, without loading production credentials."""

import ast
import os
import subprocess
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[2]
env = os.environ.copy()
settings = next(
    n
    for n in ast.parse((root / "backend/app/config.py").read_text(encoding="utf-8")).body
    if isinstance(n, ast.ClassDef) and n.name == "Settings"
)
for field in settings.body:
    if isinstance(field, ast.AnnAssign) and isinstance(field.target, ast.Name):
        env.pop(field.target.id.upper(), None)
env.update(
    {
        "APP_ENV": "dev",
        "DATABASE_URL": "sqlite+pysqlite:///:memory:",
        "JWT_SECRET": "purchase-test-secret",
        "WEBHOOK_SIGNING_SECRET": "purchase-webhook-secret",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "STORAGE_LOCAL_DIR": str(root / "backend/.pytest_cache/purchase-storage"),
        "AWS_EC2_METADATA_DISABLED": "true",
        "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1",
        "PYTHONPATH": str(root / "backend"),
        "PYTHONIOENCODING": "utf-8",
        "NO_COLOR": "1",
    }
)
result = subprocess.run(
    [
        sys.executable,
        "-m",
        "pytest",
        "-p",
        "pytest_asyncio.plugin",
        "-p",
        "anyio.pytest_plugin",
        "-q",
        "--tb=short",
        *sys.argv[1:],
    ],
    cwd=root / "backend",
    env=env,
)
sys.exit(result.returncode)
