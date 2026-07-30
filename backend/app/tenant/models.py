"""Reúne todos os modelos replicados em cada schema `tenant_{slug}`.

Mesmo papel do `app/platform/models.py`, para a outra linhagem de migration: é daqui que o
Alembic do tenant enxerga as tabelas.

Nenhum modelo aqui declara `schema`. Quem decide em qual schema a query roda é o
`search_path`, definido por requisição pelo middleware de tenant.
"""

from app.tenant.categories.models import ContractCategory
from app.tenant.messages.models import ContractMessage, MessageKind
from app.tenant.requests.models import ContractRequest, RequestOrigin, RequestStatus

__all__ = [
    "ContractCategory",
    "ContractMessage",
    "ContractRequest",
    "MessageKind",
    "RequestOrigin",
    "RequestStatus",
]
