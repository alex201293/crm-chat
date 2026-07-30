"""Domain events for the Campaigns module."""

import uuid

from src.shared.domain.base_entity import DomainEvent


class CampaignCreated(DomainEvent):
    def __init__(self, campaign_id: uuid.UUID, tenant_id: uuid.UUID, channel: str) -> None:
        super().__init__()
        self.campaign_id = campaign_id
        self.tenant_id = tenant_id
        self.channel = channel


class CampaignStarted(DomainEvent):
    def __init__(self, campaign_id: uuid.UUID, tenant_id: uuid.UUID, total: int) -> None:
        super().__init__()
        self.campaign_id = campaign_id
        self.tenant_id = tenant_id
        self.total = total


class CampaignCompleted(DomainEvent):
    def __init__(self, campaign_id: uuid.UUID, tenant_id: uuid.UUID, sent: int, failed: int) -> None:
        super().__init__()
        self.campaign_id = campaign_id
        self.tenant_id = tenant_id
        self.sent = sent
        self.failed = failed
