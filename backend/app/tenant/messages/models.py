"""Chat interno de Solicitação e Contrato.

Toda conversa sobre um contrato precisa morar no contrato. Hoje ela se espalha entre
e-mail, WhatsApp e conversa de corredor — e quando alguém pergunta "por que aceitamos esse
prazo?", seis meses depois, ninguém sabe responder.

**Esta tabela é separada de `negotiation_comments` por decisão de segurança.** O chat
interno contém exatamente o que nunca pode chegar à contraparte: margem aceitável, limite
de negociação, avaliação de risco do fornecedor. Se as duas conversas dividissem a mesma
tabela, um único erro num filtro de visibilidade vazaria a estratégia interna pelo link
público de negociação. Separar no armazenamento troca *verificação em tempo de execução*
por **garantia estrutural**: a mensagem interna não tem como sair, porque não está na
tabela que o endereço externo lê.

**Sem `updated_at` e sem `deleted_at`**, contrariando a convenção dos demais modelos de
tenant. Também é deliberado: mensagem não é editável nem apagável. Um histórico de
decisões que pode ser reescrito não serve de prova em auditoria nem em litígio — e é
justamente nesses dois momentos que ele importa. Correção se faz por mensagem nova,
preservando o que foi dito antes. Um `deleted_at` seria precisamente a porta de reescrita
que o PRD quer fechada.

**`contract_id` ainda não existe aqui.** A tabela `contracts` não foi construída; por
enquanto toda mensagem pertence a uma Solicitação e `request_id` é obrigatório. Quando
`contracts` chegar, a migration torna `request_id` anulável, acrescenta `contract_id` e a
`CHECK` de exatamente-um que o PRD especifica. Mensagens já gravadas continuam válidas: a
conversa da Solicitação aparece no contrato seguindo `contracts.request_id`, sem perder
autoria nem data.
"""

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import Uuid

from app.core.db import Base, UUIDPrimaryKey, pg_enum


class MessageKind(str, enum.Enum):
    """Origem da entrada na linha do tempo.

    `SISTEMA` cobre os eventos de ciclo de vida — triada, recusada, aprovada, assinada,
    aditivada. Eles entram na **mesma** linha do tempo das mensagens humanas de propósito:
    quem lê a conversa seis meses depois precisa ver "por que aceitamos esse prazo" e
    "quando isso foi aprovado" numa leitura só, não em duas telas separadas.
    """

    HUMANO = "humano"
    SISTEMA = "sistema"


class ContractMessage(UUIDPrimaryKey, Base):
    __tablename__ = "contract_messages"
    __table_args__ = (
        # Mensagem humana tem autor; entrada de sistema não tem. Sem esta restrição, uma
        # mensagem humana poderia acabar sem autoria — e mensagem sem autor não serve de
        # registro de decisão, que é o motivo de a tabela existir.
        CheckConstraint(
            "(kind = 'humano' AND author_id IS NOT NULL) "
            "OR (kind = 'sistema' AND author_id IS NULL)",
            name="ck_message_autor_conforme_tipo",
        ),
    )

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("contract_requests.id", ondelete="CASCADE"), index=True
    )

    # Nulo quando `kind = sistema`. O ator que provocou o evento é nomeado no corpo.
    author_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("public.platform_users.id")
    )
    kind: Mapped[MessageKind] = mapped_column(
        pg_enum(MessageKind, "message_kind", schema=None),
        default=MessageKind.HUMANO,
    )
    body: Mapped[str] = mapped_column(Text)

    # Menções (@). Cada uma gerará um `notification_item` para o digest da pessoa quando o
    # motor de notificação existir; por ora o dado é gravado e usado na exibição.
    mentioned_user_ids: Mapped[list[UUID]] = mapped_column(
        ARRAY(Uuid), default=list, server_default="{}"
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<ContractMessage {self.kind.value} em {self.request_id}>"
