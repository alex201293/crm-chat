"""Use cases for campaign management."""

import uuid
from dataclasses import dataclass
from datetime import datetime

import structlog

from src.modules.campaigns.domain.entities import Campaign, CampaignMessage, Segment
from src.modules.campaigns.domain.interfaces import (
    ICampaignMessageRepository,
    ICampaignRepository,
    ISegmentRepository,
)
from src.modules.campaigns.domain.value_objects import (
    CampaignChannel,
    CampaignStatus,
    MessageDeliveryStatus,
)
from src.modules.campaigns.infrastructure.dispatchers import CampaignDispatcher
from src.shared.api.exceptions import EntityNotFoundError, ValidationError_
from src.shared.domain.events import event_bus
from src.modules.campaigns.domain.events import CampaignStarted, CampaignCompleted

logger = structlog.get_logger()


# =============================================================================
# Create Campaign
# =============================================================================
@dataclass
class CreateCampaignCommand:
    tenant_id: uuid.UUID
    name: str
    channel: str
    template_content: str
    segment_id: uuid.UUID | None = None
    template_name: str | None = None
    subject: str | None = None


class CreateCampaignHandler:
    def __init__(self, campaign_repo: ICampaignRepository) -> None:
        self._campaign_repo = campaign_repo

    async def execute(self, cmd: CreateCampaignCommand) -> Campaign:
        if not cmd.name.strip():
            raise ValidationError_("Campaign name is required", "name")
        if not cmd.template_content.strip():
            raise ValidationError_("Template content is required", "template_content")

        campaign = Campaign.create(
            tenant_id=cmd.tenant_id,
            name=cmd.name,
            channel=CampaignChannel(cmd.channel),
            template_content=cmd.template_content,
            segment_id=cmd.segment_id,
            template_name=cmd.template_name,
            subject=cmd.subject,
        )
        await self._campaign_repo.create(campaign)
        return campaign


# =============================================================================
# Schedule Campaign
# =============================================================================
@dataclass
class ScheduleCampaignCommand:
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID
    send_at: datetime


class ScheduleCampaignHandler:
    def __init__(self, campaign_repo: ICampaignRepository) -> None:
        self._campaign_repo = campaign_repo

    async def execute(self, cmd: ScheduleCampaignCommand) -> Campaign:
        campaign = await self._campaign_repo.get_by_id(cmd.campaign_id, cmd.tenant_id)
        if not campaign:
            raise EntityNotFoundError("Campaign", str(cmd.campaign_id))

        if not campaign.is_sendable:
            raise ValidationError_(f"Campaign in status '{campaign.status.value}' cannot be scheduled")

        if cmd.send_at <= datetime.utcnow():
            raise ValidationError_("Scheduled time must be in the future", "send_at")

        campaign.schedule(cmd.send_at)
        await self._campaign_repo.update(campaign)
        return campaign


# =============================================================================
# Send Campaign (immediate)
# =============================================================================
@dataclass
class SendCampaignCommand:
    tenant_id: uuid.UUID
    campaign_id: uuid.UUID


class ExecuteCampaignHandler:
    """
    Executes a campaign: resolves segment → creates message records → dispatches.
    In production, this runs as a Celery task for large campaigns.
    """

    def __init__(
        self,
        campaign_repo: ICampaignRepository,
        segment_repo: ISegmentRepository,
        message_repo: ICampaignMessageRepository,
        dispatcher: CampaignDispatcher,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._segment_repo = segment_repo
        self._message_repo = message_repo
        self._dispatcher = dispatcher

    async def execute(self, cmd: SendCampaignCommand) -> Campaign:
        campaign = await self._campaign_repo.get_by_id(cmd.campaign_id, cmd.tenant_id)
        if not campaign:
            raise EntityNotFoundError("Campaign", str(cmd.campaign_id))

        if not campaign.is_sendable:
            raise ValidationError_(f"Campaign in status '{campaign.status.value}' cannot be sent")

        # 1. Resolve recipients from segment
        contact_ids: list[uuid.UUID] = []
        if campaign.segment_id:
            contact_ids = await self._segment_repo.get_contact_ids(
                campaign.segment_id, cmd.tenant_id
            )

        if not contact_ids:
            raise ValidationError_("No recipients found for this campaign segment")

        # 2. Start campaign
        campaign.start_sending(total_recipients=len(contact_ids))
        await self._campaign_repo.update(campaign)

        await event_bus.publish(CampaignStarted(
            campaign_id=campaign.id, tenant_id=cmd.tenant_id, total=len(contact_ids)
        ))

        # 3. Create message records in batch
        messages = [
            CampaignMessage(
                tenant_id=cmd.tenant_id,
                campaign_id=campaign.id,
                contact_id=cid,
                status=MessageDeliveryStatus.PENDING,
            )
            for cid in contact_ids
        ]
        await self._message_repo.create_batch(messages)

        # 4. Dispatch messages (in production: chunked via Celery)
        # Here we process synchronously for simplicity
        # Production would use: celery_app.send_task('campaigns.send_batch', ...)
        await self._dispatch_batch(campaign, cmd.tenant_id)

        # 5. Mark complete
        campaign.complete()
        await self._campaign_repo.update(campaign)

        await event_bus.publish(CampaignCompleted(
            campaign_id=campaign.id, tenant_id=cmd.tenant_id,
            sent=campaign.sent_count, failed=campaign.failed_count,
        ))

        logger.info(
            "Campaign completed",
            campaign_id=str(campaign.id),
            sent=campaign.sent_count,
            failed=campaign.failed_count,
        )
        return campaign

    async def _dispatch_batch(self, campaign: Campaign, tenant_id: uuid.UUID) -> None:
        """Dispatch pending messages for a campaign."""
        pending = await self._message_repo.get_pending_for_campaign(campaign.id, limit=500)

        # Get contact details for recipient resolution
        from src.modules.crm.infrastructure.models import ContactModel
        from sqlalchemy import select

        for msg in pending:
            # Resolve recipient address based on channel
            recipient = await self._resolve_recipient(
                msg.contact_id, campaign.channel, tenant_id
            )
            if not recipient:
                msg.mark_failed("No valid recipient address")
                await self._message_repo.update_status(
                    msg.id, status="failed", error_message="No valid recipient"
                )
                campaign.increment_failed()
                continue

            # Dispatch
            result = await self._dispatcher.send(
                channel=campaign.channel,
                tenant_id=tenant_id,
                recipient=recipient,
                content=campaign.template_content,
                subject=campaign.subject,
                template_name=campaign.template_name,
            )

            if result.success:
                await self._message_repo.update_status(
                    msg.id,
                    status="sent",
                    channel_message_id=result.channel_message_id,
                    sent_at=datetime.utcnow(),
                )
                campaign.increment_sent()
            else:
                await self._message_repo.update_status(
                    msg.id,
                    status="failed",
                    error_message=result.error,
                    failed_at=datetime.utcnow(),
                )
                campaign.increment_failed()

        # Update campaign metrics
        await self._campaign_repo.update(campaign)

    async def _resolve_recipient(
        self, contact_id: uuid.UUID, channel: CampaignChannel, tenant_id: uuid.UUID
    ) -> str | None:
        """Get the correct address for a contact based on channel."""
        # In production: query contact repo
        # Simplified: use session from message_repo
        if hasattr(self._message_repo, "_session"):
            from src.modules.crm.infrastructure.models import ContactModel
            from sqlalchemy import select

            session = self._message_repo._session
            stmt = select(ContactModel).where(
                ContactModel.id == contact_id,
                ContactModel.tenant_id == tenant_id,
            )
            result = await session.execute(stmt)
            contact = result.scalar_one_or_none()
            if not contact:
                return None

            if channel == CampaignChannel.WHATSAPP:
                return contact.phone or contact.whatsapp_id
            elif channel == CampaignChannel.EMAIL:
                return contact.email
            elif channel == CampaignChannel.SMS:
                return contact.phone
            elif channel == CampaignChannel.TELEGRAM:
                return contact.telegram_id
            elif channel == CampaignChannel.FACEBOOK:
                return contact.facebook_id
            elif channel == CampaignChannel.INSTAGRAM:
                return contact.instagram_id

        return None


# =============================================================================
# Pause Campaign
# =============================================================================
class PauseCampaignHandler:
    def __init__(self, campaign_repo: ICampaignRepository) -> None:
        self._campaign_repo = campaign_repo

    async def execute(self, campaign_id: uuid.UUID, tenant_id: uuid.UUID) -> Campaign:
        campaign = await self._campaign_repo.get_by_id(campaign_id, tenant_id)
        if not campaign:
            raise EntityNotFoundError("Campaign", str(campaign_id))

        if campaign.status != CampaignStatus.SENDING:
            raise ValidationError_("Only sending campaigns can be paused")

        campaign.pause()
        await self._campaign_repo.update(campaign)
        return campaign
