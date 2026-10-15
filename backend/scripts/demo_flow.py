"""Demo ponta a ponta contra uma API em execução.

Exercita: signup -> créditos -> projeto -> upload de foto -> dispara etapas ->
acompanha os jobs até concluir/falhar, imprimindo o estado. Tolera ausência de
chaves de IA (os jobs vão a FAILED e o crédito é estornado — o que valida a
orquestração mesmo sem provedores reais).

Uso:
    API_URL=http://localhost:8000 python scripts/demo_flow.py
"""
import os
import sys
import time
import uuid

import httpx

API_URL = os.environ.get("API_URL", "http://localhost:8000")
# PNG 1x1 transparente (base64 embutido) para o upload de exemplo.
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4"
    "890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
)


def log(msg: str) -> None:
    print(f"[demo] {msg}", flush=True)


def main() -> int:
    email = f"demo+{uuid.uuid4().hex[:8]}@storyrus.app"
    password = "demo12345"

    with httpx.Client(base_url=API_URL, timeout=30) as c:
        # health
        try:
            c.get("/health").raise_for_status()
        except Exception as exc:  # noqa: BLE001
            log(f"API indisponível em {API_URL}: {exc}")
            return 1

        token = c.post("/v1/auth/signup", json={"email": email, "password": password}).json()[
            "access_token"
        ]
        c.headers["Authorization"] = f"Bearer {token}"
        log(f"signup ok: {email}")
        log(f"créditos: {c.get('/v1/credits').json()['credits']}")

        project = c.post("/v1/projects", json={"style": "cartoon"}).json()
        pid = project["id"]
        log(f"projeto: {pid} (status={project['status']})")

        up = c.post(
            f"/v1/projects/{pid}/photos", json={"content_type": "image/png", "ext": "png"}
        ).json()
        log(f"upload url emitida: {up['storage_key']}")
        try:
            httpx.put(up["upload_url"], content=PNG_1x1, headers={"Content-Type": "image/png"},
                      timeout=10)
        except Exception:  # noqa: BLE001 - storage stub local
            log("(upload pulado: storage stub / sem credenciais)")

        for step in ("avatar", "story"):
            r = c.post(f"/v1/projects/{pid}/{step}", headers={"Idempotency-Key": str(uuid.uuid4())})
            if r.status_code == 202:
                log(f"etapa '{step}' enfileirada: job={r.json()['job_id']}")
            else:
                log(f"etapa '{step}' recusada: {r.status_code} {r.text}")

        # acompanha os jobs por até ~30s
        log("acompanhando jobs...")
        for _ in range(15):
            jobs = c.get(f"/v1/projects/{pid}/jobs").json()
            states = ", ".join(f"{j['type']}={j['status']}(t{j['attempts']})" for j in jobs)
            log(f"  {states or 'sem jobs'}")
            if jobs and all(j["status"] in ("DONE", "FAILED") for j in jobs):
                break
            time.sleep(2)

        proj = c.get(f"/v1/projects/{pid}").json()
        log(f"projeto final: status={proj['status']} ebook={proj['ebook_url']} video={proj['video_url']}")
        log(f"créditos finais: {c.get('/v1/credits').json()['credits']} (estorno em falhas)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
