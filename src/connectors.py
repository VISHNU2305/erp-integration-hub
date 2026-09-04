"""
Peripheral system connectors: EDI supplier feeds + expense reimbursement.

Real ERP deployments pull data from many external systems, each with
its own format. The integration layer's job is to normalize everything
into one consistent shape (Transaction) so downstream logic (security
monitoring, reporting, GenAI queries) never has to know or care where
the data originally came from.

In production these would be real API/file connectors (SFTP pickup of
EDI 850/856 files, a REST pull from an expense-management SaaS, etc.).
Here they simulate incoming batches so the integration logic itself —
the part that actually matters for the interview — is fully real and
testable without needing live external systems.
"""

import random
import uuid
from datetime import datetime, timedelta

from models import Transaction, TransactionSource

DEPARTMENTS = ["Engineering", "Procurement", "Sales", "IT", "Operations"]


class EDIConnector:
    """
    Simulates an EDI feed of supplier order confirmations landing in a
    drop folder (a common real-world pattern: EDI 850/856 documents
    arriving via SFTP on a schedule, then parsed into structured data).
    """

    def fetch_batch(self, count: int = 5) -> list[Transaction]:
        transactions = []
        for _ in range(count):
            transactions.append(Transaction(
                transaction_id=f"EDI-{uuid.uuid4().hex[:8].upper()}",
                source=TransactionSource.EDI_FEED,
                department=random.choice(DEPARTMENTS),
                amount=round(random.uniform(10_000, 800_000), 2),
                description=f"Supplier order confirmation #{random.randint(1000,9999)}",
                timestamp=datetime.now() - timedelta(days=random.randint(0, 5)),
            ))
        return transactions


class ExpenseSystemConnector:
    """
    Simulates an employee expense-reimbursement system feed — a
    peripheral system explicitly named in the JD alongside EDI.
    """

    EXPENSE_TYPES = ["Travel", "Client Entertainment", "Office Supplies", "Training", "Software License"]

    def fetch_batch(self, count: int = 5) -> list[Transaction]:
        transactions = []
        for _ in range(count):
            expense_type = random.choice(self.EXPENSE_TYPES)
            transactions.append(Transaction(
                transaction_id=f"EXP-{uuid.uuid4().hex[:8].upper()}",
                source=TransactionSource.EXPENSE_SYSTEM,
                department=random.choice(DEPARTMENTS),
                amount=round(random.uniform(2_000, 150_000), 2),
                description=f"{expense_type} reimbursement claim",
                timestamp=datetime.now() - timedelta(days=random.randint(0, 5)),
            ))
        return transactions


def sync_all_peripheral_systems() -> list[Transaction]:
    """
    Pulls a batch from every connected peripheral system and returns one
    normalized list — this is the function the rest of the platform
    calls when it wants "everything that came in from outside the core."
    """
    edi = EDIConnector()
    expense = ExpenseSystemConnector()

    all_transactions = []
    all_transactions.extend(edi.fetch_batch())
    all_transactions.extend(expense.fetch_batch())
    return all_transactions