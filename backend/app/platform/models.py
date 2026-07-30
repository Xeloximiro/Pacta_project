"""Reúne todos os modelos do schema `public`.

Existe por dois motivos: o Alembic precisa que os modelos estejam importados para enxergá-los
no `Base.metadata` ao gerar migration, e o SQLAlchemy precisa deles carregados para resolver
as referências por string entre `relationship()` de módulos diferentes.

Importar um módulo de modelo isoladamente não basta — tem que passar por aqui.
"""

from app.platform.billing.models import Plan, PlanCode, Subscription, SubscriptionStatus
from app.platform.identity.models import PlatformUser, TenantMembership, TenantRole
from app.platform.integrations.models import IntegrationProvider, TenantIntegration
from app.platform.tenants.models import SectorPack, Tenant, TenantStatus

__all__ = [
    "IntegrationProvider",
    "Plan",
    "PlanCode",
    "PlatformUser",
    "SectorPack",
    "Subscription",
    "SubscriptionStatus",
    "Tenant",
    "TenantIntegration",
    "TenantMembership",
    "TenantRole",
    "TenantStatus",
]
