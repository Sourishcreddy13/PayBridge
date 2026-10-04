from datetime import datetime, timezone
from uuid import uuid4
from paybridge.application.timeline_service import TimelineService
from paybridge.domain.enums import PaymentState
from paybridge.domain.models import PaymentTransition

class StubRepo:
    def __init__(self, value): self.value=value
    def list_transitions(self, payment_id): return self.value

def test_timeline_summary():
    pid=uuid4(); items=[PaymentTransition(pid,PaymentState.PENDING,PaymentState.PROCESSING,datetime.now(timezone.utc),'actor')]
    s=TimelineService(StubRepo(items)); assert s.summarize(s.get_timeline(pid))==['PENDING -> PROCESSING']
