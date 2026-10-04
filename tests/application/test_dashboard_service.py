from datetime import datetime, timezone, date
from decimal import Decimal
from uuid import uuid4
from paybridge.application.dashboard_service import DashboardService
from paybridge.domain.enums import BeneficiaryType, PaymentState, Rail, ReconciliationStatus, RefundStatus
from paybridge.domain.models import Beneficiary, Payment, Refund, SettlementEntry

class Payments:
    def __init__(self,p,state): self.p=p; self.state=state
    def list_payments(self): return self.p
    def get_current_state(self,pid): return self.state
class Routes:
    def get_route(self,pid): return Rail.NEFT
class Settlements:
    def __init__(self,e): self.e=e
    def list_reconciliation_results(self,d): return self.e
class Refunds:
    def __init__(self,r): self.r=r
    def list_refunds(self): return self.r

def make_payment():
    return Payment(uuid4(),Beneficiary('123456789012','ABCD0123456',BeneficiaryType.RETAIL,'Demo User'),Decimal('12.00'),'demo','dash-test-1','INR',datetime.now(timezone.utc),'actor')

def test_AC_10_summary_counts_rail_and_status():
    p=make_payment(); service=DashboardService(Payments([p],PaymentState.PENDING),Routes(),Settlements([]),Refunds([])); summary=service.summary(p.created_at.date()); assert summary.volumes_by_status['PENDING']==1; assert summary.volumes_by_rail['NEFT']==1

def test_AC_10_summary_returns_unmatched_queue():
    p=make_payment(); e=SettlementEntry('ext',p.payment_id,Decimal('12'),'INR',p.created_at.date(),ReconciliationStatus.UNMATCHED); service=DashboardService(Payments([p],PaymentState.PENDING),Routes(),Settlements([e]),Refunds([])); assert len(service.summary(p.created_at.date()).unmatched_queue)==1

def test_AC_10_summary_returns_refund_queue():
    p=make_payment(); refund=Refund(uuid4(),p.payment_id,uuid4(),Decimal('12'),RefundStatus.COMPLETED,datetime.now(timezone.utc),'actor'); service=DashboardService(Payments([p],PaymentState.REFUNDED),Routes(),Settlements([]),Refunds([refund])); assert len(service.summary(p.created_at.date()).refund_queue)==1
