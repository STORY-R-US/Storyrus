"""Run from backend: python -m scripts.privacy_retention --days 90 [--execute]."""

import argparse
import json

from app.database import SessionLocal
from app.routers.projects.common import purge_project
from app.services.privacy_retention import UNPAID_RETENTION_DAYS, retention_candidates


def main():
    parser = argparse.ArgumentParser(
        description="Revisar ou excluir projetos abandonados sem pagamento"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=UNPAID_RETENTION_DAYS,
        help="Prazo aprovado: 90 dias de inatividade",
    )
    parser.add_argument("--execute", action="store_true", help="Efetivar a exclusão dos candidatos")
    args = parser.parse_args()
    if args.days < 1:
        parser.error("--days deve ser maior que zero")
    with SessionLocal() as db:
        ids = [project.id for project in retention_candidates(db, days=args.days)]
        print(
            json.dumps(
                {
                    "mode": "execute" if args.execute else "review",
                    "count": len(ids),
                    "project_ids": [str(pid) for pid in ids],
                }
            )
        )
        if args.execute:
            for pid in ids:
                try:
                    purge_project(db, pid)
                    db.commit()
                except Exception:
                    db.rollback()
                    raise


if __name__ == "__main__":
    main()
