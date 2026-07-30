"""Hash de senha e emissão/validação de tokens de acesso."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings

ALGORITHM = "HS256"

# Argon2id nos parâmetros padrão da biblioteca. É o algoritmo recomendado hoje para
# senha, e não usamos passlib de propósito: ele adiciona uma camada de abstração entre
# nós e o argon2 que só se paga quando há vários algoritmos em jogo — aqui há um só.
_hasher = PasswordHasher()


def hash_password(plain_password: str) -> str:
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Confere a senha contra o hash.

    Devolve False em vez de propagar exceção, inclusive quando o hash está corrompido ou
    em formato desconhecido: para quem chama, "não confere" e "não consigo verificar"
    levam à mesma decisão, e distinguir os dois na resposta HTTP entregaria informação
    sobre o estado interno da conta.
    """
    try:
        _hasher.verify(password_hash, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
    return True


def needs_rehash(password_hash: str) -> bool:
    """Indica se o hash foi gerado com parâmetros mais fracos que os atuais."""
    return _hasher.check_needs_rehash(password_hash)


def create_access_token(*, user_id: UUID, tenant_id: UUID, role: str) -> str:
    """Emite um token ligado a **um** tenant.

    O `tid` no payload é o que impede um token emitido para um tenant de valer em outro.
    Um mesmo e-mail pode pertencer a várias empresas clientes — o consultor jurídico que
    atende duas delas é o caso citado no PRD — e cada vínculo tem papel próprio. Sem o
    `tid`, um token obtido no tenant onde a pessoa é `admin` daria acesso de admin ao
    tenant onde ela é apenas `visualizador`.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "tid": str(tenant_id),
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    """Decodifica e valida o token. Devolve None se for inválido ou expirado."""
    try:
        return jwt.decode(
            token, get_settings().secret_key, algorithms=[ALGORITHM]
        )
    except jwt.PyJWTError:
        return None
