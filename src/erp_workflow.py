"""
Core ERP workflow engine: purchase requisition -> approval -> procurement.

This is a simplified but realistic implementation of a standard business
process, the kind an ERP system enforces. Business rules encoded here:

  1. A requisition cannot be approved by the same person who created it
     (segregation of duties — a real audit/governance requirement).
  2. Purchases above a threshold require a higher-level approver role
     (simple escalation rule).
  3. Once PROCURED, a requisition generates a Transaction record that
     flows into the rest of the system (e.g. for security monitoring).

In production this logic would live inside (or call out to) the real
Cloud ERP's workflow module — this class simulates that layer so the
rest of the platform (connectors, security, GenAI assistant) has
something real to integrate with.
"""

import uuid
from typing import Optional

from models import PurchaseRequisition, RequisitionStatus, Transaction, TransactionSource

APPROVAL_ESCALATION_THRESHOLD = 500_000  # JPY - above this needs a senior approver


class WorkflowError(Exception):
    """Raised when a requested workflow transition violates a business rule."""
    pass


class WorkflowEngine:
    def __init__(self):
        self.requisitions: dict[str, PurchaseRequisition] = {}
        self.transactions: list[Transaction] = []

    # -----------------------------------------------------------------
    # Requisition lifecycle
    # -----------------------------------------------------------------

    def create_requisition(
        self, requester: str, department: str, item_description: str,
        quantity: int, unit_cost: float
    ) -> PurchaseRequisition:
        req = PurchaseRequisition(
            requisition_id=f"REQ-{uuid.uuid4().hex[:8].upper()}",
            requester=requester,
            department=department,
            item_description=item_description,
            quantity=quantity,
            unit_cost=unit_cost,
            status=RequisitionStatus.DRAFT,
        )
        self.requisitions[req.requisition_id] = req
        return req

    def submit_for_approval(self, requisition_id: str) -> PurchaseRequisition:
        req = self._get(requisition_id)
        if req.status != RequisitionStatus.DRAFT:
            raise WorkflowError(
                f"Cannot submit requisition in status '{req.status}'. Must be DRAFT."
            )
        req.status = RequisitionStatus.PENDING_APPROVAL
        return req

    def approve_requisition(self, requisition_id: str, approver: str) -> PurchaseRequisition:
        req = self._get(requisition_id)

        if req.status != RequisitionStatus.PENDING_APPROVAL:
            raise WorkflowError(
                f"Cannot approve requisition in status '{req.status}'. "
                f"Must be PENDING_APPROVAL."
            )

        # Rule 1: segregation of duties
        if approver == req.requester:
            raise WorkflowError(
                "Segregation-of-duties violation: requester cannot approve their own requisition."
            )

        # Rule 2: escalation threshold check (informational — in a real
        # system this would route to a different approver role instead)
        if req.total_cost > APPROVAL_ESCALATION_THRESHOLD and "senior" not in approver.lower():
            raise WorkflowError(
                f"Requisition total ({req.total_cost:,.0f} JPY) exceeds escalation "
                f"threshold ({APPROVAL_ESCALATION_THRESHOLD:,.0f} JPY). "
                f"Requires a senior approver."
            )

        req.status = RequisitionStatus.APPROVED
        req.approver = approver
        return req

    def reject_requisition(self, requisition_id: str, approver: str) -> PurchaseRequisition:
        req = self._get(requisition_id)
        if req.status != RequisitionStatus.PENDING_APPROVAL:
            raise WorkflowError(
                f"Cannot reject requisition in status '{req.status}'. "
                f"Must be PENDING_APPROVAL."
            )
        req.status = RequisitionStatus.REJECTED
        req.approver = approver
        return req

    def mark_procured(self, requisition_id: str) -> Transaction:
        req = self._get(requisition_id)
        if req.status != RequisitionStatus.APPROVED:
            raise WorkflowError(
                f"Cannot procure requisition in status '{req.status}'. Must be APPROVED."
            )
        req.status = RequisitionStatus.PROCURED

        txn = Transaction(
            transaction_id=f"TXN-{uuid.uuid4().hex[:8].upper()}",
            source=TransactionSource.ERP_CORE,
            department=req.department,
            amount=req.total_cost,
            description=f"Procurement: {req.item_description} (x{req.quantity})",
            linked_requisition_id=req.requisition_id,
        )
        self.transactions.append(txn)
        return txn

    # -----------------------------------------------------------------
    # Helpers
    # -----------------------------------------------------------------

    def _get(self, requisition_id: str) -> PurchaseRequisition:
        req = self.requisitions.get(requisition_id)
        if not req:
            raise WorkflowError(f"No requisition found with id '{requisition_id}'.")
        return req

    def list_requisitions(self, status: Optional[RequisitionStatus] = None) -> list[PurchaseRequisition]:
        reqs = list(self.requisitions.values())
        if status:
            reqs = [r for r in reqs if r.status == status]
        return reqs