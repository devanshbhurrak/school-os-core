"""Notification channel providers — Phase 3 in-app engine, Phase-4 hooks.

Phase 3 ships the in-app channel (writes `notifications` rows, surfaced via
the portal bell + list page). External channels (Email, WhatsApp) are defined
as interfaces + no-op stubs so Phase 4 drops in real providers without
touching the dispatcher or handlers:

    from app.workers.channels import register_channel
    register_channel(WhatsAppProvider(...))  # Phase 4

A channel send must be idempotent: the dispatcher retries failed events, so a
provider that cannot dedupe (e.g. raw SMTP) should record a sent-marker or use
the notification row id as the idempotency key.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ChannelMessage:
    """A single deliverable unit, fanned out to one user."""

    user_id: str
    organization_id: str
    school_id: str | None
    type: str  # NotificationType value: ANNOUNCEMENT | ATTENDANCE | ENROLLMENT | SYSTEM
    title: str
    body: str | None = None
    entity_type: str | None = None
    entity_id: str | None = None
    # Idempotency key: f"{event_name}:{event_id}:{user_id}". Providers reuse it.
    dedupe_key: str = ""


class ChannelProvider(Protocol):
    """Interface every channel (in-app, email, WhatsApp, ...) implements."""

    name: str

    async def send(self, session: AsyncSession, message: ChannelMessage) -> None:
        """Deliver one message. Must be safe to call twice (idempotent)."""
        ...


class InAppChannel:
    """Phase 3 default: persist a notification row (portal bell + list page)."""

    name = "inapp"

    async def send(self, session: AsyncSession, message: ChannelMessage) -> None:
        # Idempotency: skip when this event already produced a row for the user.
        conditions = [
            Notification.user_id == message.user_id,
            Notification.organization_id == message.organization_id,
            Notification.type == message.type,
        ]
        for column, value in (
            (Notification.related_entity_type, message.entity_type),
            (Notification.related_entity_id, message.entity_id),
        ):
            conditions.append(column.is_(None) if value is None else column == value)
        existing = await session.scalar(select(Notification.id).where(*conditions))
        if existing is not None:
            return
        session.add(
            Notification(
                user_id=message.user_id,
                organization_id=message.organization_id,
                school_id=message.school_id,
                type=message.type,
                title=message.title,
                body=message.body,
                related_entity_type=message.entity_type,
                related_entity_id=message.entity_id,
            )
        )
        await session.flush()


class EmailChannelStub:
    """Phase-4 hook: logs instead of sending. Replace with SES/SendGrid."""

    name = "email"

    async def send(self, session: AsyncSession, message: ChannelMessage) -> None:
        logger.info(
            "email_stub_send",
            extra={"user_id": message.user_id, "title": message.title},
        )


class WhatsAppChannelStub:
    """Phase-4 hook: logs instead of sending. Replace with Meta Cloud API."""

    name = "whatsapp"

    async def send(self, session: AsyncSession, message: ChannelMessage) -> None:
        logger.info(
            "whatsapp_stub_send",
            extra={"user_id": message.user_id, "title": message.title},
        )


@dataclass
class ChannelRegistry:
    """Ordered set of channels; every message fans out to all enabled ones."""

    _channels: dict[str, ChannelProvider] = field(default_factory=dict)

    def register(self, provider: ChannelProvider) -> None:
        self._channels[provider.name] = provider

    def unregister(self, name: str) -> None:
        self._channels.pop(name, None)

    @property
    def channels(self) -> list[ChannelProvider]:
        return list(self._channels.values())

    async def broadcast(self, session: AsyncSession, message: ChannelMessage) -> None:
        for provider in self.channels:
            await provider.send(session, message)


# Default registry: in-app only. Phase 4 registers email/WhatsApp providers.
default_registry = ChannelRegistry()
default_registry.register(InAppChannel())


def register_channel(provider: ChannelProvider) -> None:
    """Phase-4 entry point: `register_channel(EmailProvider(...))`."""
    default_registry.register(provider)
