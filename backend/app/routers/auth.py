"""Cadastro completo, verificação de e-mail, login, guest, refresh/resume e perfil."""

import logging
import uuid
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import rate_limit
from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_registered_user
from app.models import User
from app.owner_auth import promote_verified_owner
from app.schemas import (
    ForgotPasswordIn,
    ForgotPasswordOut,
    LoginIn,
    ProfileUpdateIn,
    ResendVerifyIn,
    ResetPasswordIn,
    ResumeIn,
    SignupIn,
    SignupOut,
    TokenOut,
    UserOut,
    VerifyEmailIn,
)
from app.security import (
    create_access_token,
    decode_access_token_allow_expired,
    decode_email_verify_token,
    decode_password_reset_token,
    hash_password,
    hash_token,
    is_guest_user,
    new_email_verify_secret,
    new_password_reset_secret,
    normalize_verify_token,
    verify_password,
)
from app.services.transactional_email import send_password_reset_email, send_verify_email

router = APIRouter(prefix="/v1/auth", tags=["auth"])
logger = logging.getLogger(__name__)

_SIGNUP_MSG = "Cadastro recebido. Confirme seu e-mail pelo link que enviamos."
_FORGOT_MSG = "Se este e-mail estiver cadastrado, enviamos um link para redefinir a senha."
_RESEND_MSG = "Se este e-mail estiver cadastrado e pendente, enviamos um novo link de confirmação."


def _is_legacy_unverified(user: User) -> bool:
    """Conta real anterior à verificação: senha permanente, sem token pendente."""
    return (
        user.email_verified_at is None
        and not user.email_verify_token_hash
        and not is_guest_user(email=user.email, password_hash=user.password_hash)
    )


def _norm_email(value: str) -> str:
    return str(value).strip().lower()


def _user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == _norm_email(email)))


def _issue_verify_email(user: User, db: Session) -> str:
    raw_token = new_email_verify_secret()
    user.email_verify_token_hash = hash_token(raw_token)
    db.add(user)
    db.commit()
    db.refresh(user)
    send_verify_email(to_email=user.email, token=raw_token)
    return raw_token


def _user_out(user: User) -> UserOut:
    from app.owner_auth import user_is_admin

    guest = is_guest_user(email=user.email, password_hash=user.password_hash)
    admin = user_is_admin(user)
    return UserOut(
        id=user.id,
        email=user.email,
        credits=user.credits,
        created_at=user.created_at,
        is_guest=guest,
        email_verified=guest or user.email_verified_at is not None,
        is_admin=admin,
        is_owner=admin,
        full_name=user.full_name,
        phone=user.phone,
        postal_code=user.postal_code,
        street=user.street,
        number=user.number,
        complement=user.complement,
        district=user.district,
        city=user.city,
        state=user.state,
        country=user.country,
    )


def _apply_profile(user: User, body: SignupIn | ProfileUpdateIn) -> None:
    data = body.model_dump(exclude_unset=True)
    for key in (
        "full_name",
        "phone",
        "postal_code",
        "street",
        "number",
        "complement",
        "district",
        "city",
        "state",
        "country",
    ):
        if key in data:
            setattr(user, key, data[key])


@router.post("/signup", response_model=SignupOut, status_code=status.HTTP_201_CREATED)
def signup(body: SignupIn, db: Session = Depends(get_db)) -> SignupOut:
    email = _norm_email(str(body.email))
    if _user_by_email(db, email):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail ja cadastrado")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        credits=settings.signup_bonus_credits,
        terms_accepted_at=datetime.now(UTC),
        email_verified_at=None,
    )
    _apply_profile(user, body)
    db.add(user)
    db.flush()
    raw_token = _issue_verify_email(user, db)
    verify_token = raw_token if settings.app_env != "prod" else None
    return SignupOut(ok=True, message=_SIGNUP_MSG, verify_token=verify_token)


@router.post("/verify-email", response_model=TokenOut)
def verify_email(body: VerifyEmailIn, db: Session = Depends(get_db)) -> TokenOut:
    token = normalize_verify_token(body.token)
    if not token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link invalido ou expirado")
    digest = hash_token(token)
    user = db.scalar(select(User).where(User.email_verify_token_hash == digest))
    if user is None:
        payload = decode_email_verify_token(token)
        if payload and payload.get("sub"):
            try:
                user = db.get(User, uuid.UUID(str(payload["sub"])))
            except ValueError:
                user = None
    if user is None or is_guest_user(email=user.email, password_hash=user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link invalido ou expirado")
    expected = user.email_verify_token_hash
    if expected and expected == digest:
        user.email_verified_at = datetime.now(UTC)
        user.email_verify_token_hash = None
        promote_verified_owner(user)
        db.add(user)
        db.commit()
        return TokenOut(access_token=create_access_token(str(user.id)))
    if user.email_verified_at is not None:
        if promote_verified_owner(user):
            db.add(user)
            db.commit()
        return TokenOut(access_token=create_access_token(str(user.id)))
    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link invalido ou expirado")


@router.post("/guest", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def guest(request: Request, db: Session = Depends(get_db)) -> TokenOut:
    """Cria um usuario isolado por sessao (sem e-mail real) e devolve JWT."""
    rate_limit.check_guest(request)
    uid = uuid.uuid4()
    user = User(
        email=f"guest-{uid}@storyrus.app",
        password_hash="!guest",
        credits=settings.signup_bonus_credits,
        email_verified_at=datetime.now(UTC),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.post("/refresh", response_model=TokenOut)
def refresh(user: User = Depends(get_current_user)) -> TokenOut:
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.post("/resume", response_model=TokenOut)
def resume(body: ResumeIn, request: Request, db: Session = Depends(get_db)) -> TokenOut:
    rate_limit.check_session_resume(request)
    payload = decode_access_token_allow_expired(body.access_token)
    if not payload or "sub" not in payload:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")

    try:
        user_id = uuid.UUID(str(payload["sub"]))
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido") from exc

    iat = payload.get("iat")
    if iat is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")
    try:
        issued_at = datetime.fromtimestamp(int(iat), tz=UTC)
    except (TypeError, ValueError, OSError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido") from exc

    max_age = timedelta(minutes=settings.access_token_ttl_min + settings.guest_resume_grace_min)
    if datetime.now(UTC) - issued_at > max_age:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessao expirada demais")

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sessao invalida")

    rate_limit.check_session_resume(request, user_id=str(user.id))
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.post("/upgrade", response_model=SignupOut)
def upgrade(
    body: SignupIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SignupOut:
    """Converte convidado em conta real no mesmo `user_id` (exige verificar e-mail)."""
    if not is_guest_user(email=user.email, password_hash=user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Conta ja e permanente")
    if _user_by_email(db, str(body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "E-mail ja cadastrado")

    user.email = _norm_email(str(body.email))
    user.password_hash = hash_password(body.password)
    user.terms_accepted_at = datetime.now(UTC)
    user.email_verified_at = None
    _apply_profile(user, body)
    raw_token = _issue_verify_email(user, db)
    verify_token = raw_token if settings.app_env != "prod" else None
    return SignupOut(ok=True, message=_SIGNUP_MSG, verify_token=verify_token)


@router.post("/login", response_model=TokenOut)
def login(body: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = _user_by_email(db, str(body.email))
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais invalidas")
    if is_guest_user(email=user.email, password_hash=user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciais invalidas")
    if user.email_verified_at is None:
        if _is_legacy_unverified(user):
            user.email_verified_at = datetime.now(UTC)
            promote_verified_owner(user)
            db.add(user)
            db.commit()
        else:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "Confirme seu e-mail antes de entrar",
            )
    elif promote_verified_owner(user):
        db.add(user)
        db.commit()
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.post("/resend-verify", response_model=SignupOut)
def resend_verify(
    body: ResendVerifyIn,
    request: Request,
    db: Session = Depends(get_db),
) -> SignupOut:
    """Reenvia o link de confirmação. Sempre OK genérico (não revela se o e-mail existe)."""
    rate_limit.check_password_reset(request, email=_norm_email(str(body.email)))
    user = _user_by_email(db, str(body.email))
    verify_token: str | None = None
    if (
        user is not None
        and not is_guest_user(email=user.email, password_hash=user.password_hash)
        and user.email_verified_at is None
    ):
        raw_token = _issue_verify_email(user, db)
        if settings.app_env != "prod":
            verify_token = raw_token
    return SignupOut(ok=True, message=_RESEND_MSG, verify_token=verify_token)


@router.post("/forgot-password", response_model=ForgotPasswordOut)
def forgot_password(
    body: ForgotPasswordIn,
    request: Request,
    db: Session = Depends(get_db),
) -> ForgotPasswordOut:
    """Sempre responde OK genérico (não revela se o e-mail existe)."""
    rate_limit.check_password_reset(request, email=_norm_email(str(body.email)))
    user = _user_by_email(db, str(body.email))
    reset_token: str | None = None
    if user is not None and not is_guest_user(email=user.email, password_hash=user.password_hash):
        raw_token = new_password_reset_secret()
        user.password_reset_token_hash = hash_token(raw_token)
        db.add(user)
        db.commit()
        sent = send_password_reset_email(to_email=user.email, token=raw_token)
        if not sent:
            logger.warning(
                "password_reset_email_not_sent to=%s (verifique RESEND_API_KEY / domínio)",
                user.email,
            )
        if settings.app_env != "prod":
            reset_token = raw_token
    return ForgotPasswordOut(ok=True, message=_FORGOT_MSG, reset_token=reset_token)


@router.post("/reset-password", response_model=TokenOut)
def reset_password(body: ResetPasswordIn, db: Session = Depends(get_db)) -> TokenOut:
    token = normalize_verify_token(body.token)
    if not token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link invalido ou expirado")
    digest = hash_token(token)
    user = db.scalar(select(User).where(User.password_reset_token_hash == digest))
    if user is None:
        payload = decode_password_reset_token(token)
        if payload and payload.get("sub"):
            try:
                user = db.get(User, uuid.UUID(str(payload["sub"])))
            except ValueError:
                user = None
    if user is None or is_guest_user(email=user.email, password_hash=user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link invalido ou expirado")
    expected = user.password_reset_token_hash
    if not expected or expected != digest:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Link invalido ou expirado")
    user.password_hash = hash_password(body.password)
    user.password_reset_token_hash = None
    # Link no e-mail prova posse da caixa — libera login sem verify separado.
    if user.email_verified_at is None:
        user.email_verified_at = datetime.now(UTC)
        user.email_verify_token_hash = None
    db.add(user)
    db.commit()
    return TokenOut(access_token=create_access_token(str(user.id)))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)


@router.patch("/me", response_model=UserOut)
def update_me(
    body: ProfileUpdateIn,
    db: Session = Depends(get_db),
    user: User = Depends(require_registered_user),
) -> UserOut:
    _apply_profile(user, body)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user)
