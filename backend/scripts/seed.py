"""Seed de desenvolvimento: usuário demo + créditos + projeto de exemplo.

Idempotente — pode rodar várias vezes. Uso:

    cd backend && python scripts/seed.py
    # ou no docker:
    docker compose run --rm api python scripts/seed.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import UTC, datetime

from sqlalchemy import select

from app.database import Base, SessionLocal, engine
from app.models import Project, ProjectStatus, ProjectStyle, User
from app.security import hash_password

DEMO_EMAIL = "demo@storyrus.app"
DEMO_PASSWORD = "demo12345"
DEMO_CREDITS = 50


def _ensure_demo_profile(user: User) -> None:
    """Perfil + e-mail verificado para o login demo continuar funcionando."""
    user.full_name = user.full_name or "Demo Storyrus"
    user.phone = user.phone or "11999990000"
    user.postal_code = user.postal_code or "01310100"
    user.street = user.street or "Av Paulista"
    user.number = user.number or "1000"
    user.district = user.district or "Bela Vista"
    user.city = user.city or "Sao Paulo"
    user.state = user.state or "SP"
    user.country = user.country or "BR"
    if user.terms_accepted_at is None:
        user.terms_accepted_at = datetime.now(UTC)
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)


def main() -> None:
    # Cria as tabelas se ainda não existirem (conveniência em dev/SQLite).
    Base.metadata.create_all(engine)

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.email == DEMO_EMAIL))
        if user is None:
            user = User(
                email=DEMO_EMAIL,
                password_hash=hash_password(DEMO_PASSWORD),
                credits=DEMO_CREDITS,
            )
            _ensure_demo_profile(user)
            db.add(user)
            db.flush()
            print(f"[seed] usuário criado: {DEMO_EMAIL} / {DEMO_PASSWORD}")
        else:
            if user.credits < DEMO_CREDITS:
                user.credits = DEMO_CREDITS
            _ensure_demo_profile(user)
            print(f"[seed] usuário já existia: {DEMO_EMAIL} (créditos={user.credits})")

        has_project = db.scalar(select(Project).where(Project.user_id == user.id))
        if has_project is None:
            project = Project(
                user_id=user.id,
                status=ProjectStatus.CREATED.value,
                style=ProjectStyle.CARTOON.value,
            )
            db.add(project)
            db.flush()
            print(f"[seed] projeto de exemplo criado: {project.id}")
        else:
            print(f"[seed] projeto de exemplo já existia: {has_project.id}")

        db.commit()
        print(f"[seed] OK. Créditos do demo: {user.credits}")
        print("[seed] login na web/mobile:", DEMO_EMAIL, "/", DEMO_PASSWORD)
    finally:
        db.close()


if __name__ == "__main__":
    main()
