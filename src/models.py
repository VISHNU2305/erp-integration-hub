"""
Core data models for the Cloud ERP Integration Hub.

These mirror the kind of structured entities a real Cloud ERP
(SAP S/4HANA, Oracle Fusion, NetSuite, etc.) exposes via its API —
purchase requisitions, transactions, and security events. Every other
module in this project is written against these models, so if you
later point this at a real ERP's API, only the connector layer needs
to change.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class RequisitionStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PROCURED = "PROCURED"


class TransactionSource(str, Enum):
    ERP_CORE = "ERP_CORE"
    EDI_FEED = "EDI_FEED"           # electronic data interchange (supplier orders)
    EXPENSE_SYSTEM = "EXPENSE_SYSTEM"


@dataclass
class PurchaseRequisition:
    """One purchase request moving through the approval workflow."""
    requisition_id: str
    requester: str
    department: str
    item_description: str
    quantity: int
    unit_cost: float
    status: RequisitionStatus = RequisitionStatus.DRAFT
    approver: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def total_cost(self) -> float:
        return self.quantity * self.unit_cost


@dataclass
class Transaction:
    """
    A generic financial/inventory movement — used both for transactions
    originating inside the ERP core and ones pulled in from peripheral
    systems (EDI supplier feeds, expense reimbursement).
    """
    transaction_id: str
    source: TransactionSource
    department: str
    amount: float
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    linked_requisition_id: Optional[str] = None


@dataclass
class SecurityEvent:
    """A flagged anomaly from the governance/security layer."""
    severity: str            # "HIGH" | "MEDIUM" | "LOW"
    event_type: str          # e.g. "UNUSUAL_AMOUNT", "DUPLICATE_TRANSACTION"
    transaction_id: str
    message: str
    timestamp: datetime = field(default_factory=datetime.now)