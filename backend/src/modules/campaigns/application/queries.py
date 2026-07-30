"""Query handlers for campaigns data retrieval."""

import uuid
from dataclasses import dataclass

from src.modules.campaigns.domain.entities import Campaign
from src.modules.campaigns.domain.interfaces import (
    ICampaignMessageRepository,
    ICampaignRepository,
)
from src.modules.campaigns.domain.value_objects import CampaignStatus


@dataclass
class CampaignStatsDTO:
    total_recipients: int
    sent: int
    delivered: int
    read: int
    clicked: int
    failed: int
    delivery_rate: float
    open_rate: float
    click_rate: float
    status_breakdown: dict[str, int]


class ListCampaignsHandler:
    def __init__(self, campaign_repo: ICampaignRepository) -> None:
        self._campaign_repo = campaign_repo

    async def execute(
        self,
        tenant_id: uuid.UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Campaign], int]:
        s = CampaignStatus(status) if status else None
        offset = (page - 1) * page_size
        campaigns = await self._campaign_repo.list_by_tenant(
            tenant_id, status=s, offset=offset, limit=page_size
        )
        total = await self._campaign_repo.count_by_tenant(tenant_id)
        return campaigns, total


class GetCampaignStatsHandler:
    def __init__(
        self,
        campaign_repo: ICampaignRepository,
        message_repo: ICampaignMessageRepository,
    ) -> None:
        self._campaign_repo = campaign_repo
        self._message_repo = message_repo

    async def execute(
        self, campaign_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> CampaignStatsDTO:
        campaign = await self._campaign_repo.get_by_id(campaign_id, tenant_id)
        if not campaign:
            from src.shared.api.exceptions import EntityNotFoundError
            raise EntityNotFoundError("Campaign", str(campaign_id))

        status_breakdown = await self._message_repo.count_by_status(campaign_id)

        return CampaignStatsDTO(
            total_recipients=campaign.total_recipients,
            sent=campaign.sent_count,
            delivered=campaign.delivered_count,
            read=campaign.read_count,
            clicked=campaign.clicked_count,
            failed=campaign.failed_count,
            delivery_rate=campaign.delivery_rate,
            open_rate=campaign.open_rate,
            click_rate=campaign.click_rate,
            status_breakdown=status_breakdown,
        )
