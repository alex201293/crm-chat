from src.modules.crm.infrastructure.repositories.contact_repository import (
    ContactRepository,
)
from src.modules.crm.infrastructure.repositories.company_repository import (
    CompanyRepository,
)
from src.modules.crm.infrastructure.repositories.deal_repository import (
    DealRepository,
)
from src.modules.crm.infrastructure.repositories.pipeline_repository import (
    PipelineRepository,
)
from src.modules.crm.infrastructure.repositories.task_repository import (
    TaskRepository,
)
from src.modules.crm.infrastructure.repositories.note_repository import (
    NoteRepository,
)
from src.modules.crm.infrastructure.repositories.activity_repository import (
    ActivityRepository,
)

__all__ = [
    "ActivityRepository",
    "CompanyRepository",
    "ContactRepository",
    "DealRepository",
    "NoteRepository",
    "PipelineRepository",
    "TaskRepository",
]
