"""Value objects for the Campaigns bounded context."""

from enum import Enum


class CampaignChannel(str, Enum):
    """Channels available for campaigns."""

    WHATSAPP = "whatsapp"
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"


class CampaignStatus(str, Enum):
    """Campaign lifecycle states."""

    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class MessageDeliveryStatus(str, Enum):
    """Individual message delivery tracking."""

    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    CLICKED = "clicked"
    FAILED = "failed"
    BOUNCED = "bounced"
    UNSUBSCRIBED = "unsubscribed"


class SegmentOperator(str, Enum):
    """Operators for segment filter conditions."""

    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    IN = "in"
    NOT_IN = "not_in"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
