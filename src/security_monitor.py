"""
Security/governance monitoring layer — the CSIRT-style anomaly
detection piece of the platform.

Real enterprise security monitoring isn't just network firewalls —
transaction-level anomaly detection is a core part of internal
governance and fraud prevention. This module implements three
practical, explainable heuristics rather than a black-box ML model,
because in a governance context, an analyst needs to be able to see
*why* something was flagged.
"""

from collections import defaultdict
from statistics import median

from models import SecurityEvent, Transaction

OFF_HOURS_START = 20   # 8 PM
OFF_HOURS_END = 6      # 6 AM
DUPLICATE_WINDOW_MINUTES = 60
MAD_Z_SCORE_THRESHOLD = 3.5   # Iglewicz & Hoaglin's recommended threshold


class SecurityMonitor:
    def scan(self, transactions: list[Transaction]) -> list[SecurityEvent]:
        events: list[SecurityEvent] = []
        events.extend(self._detect_unusual_amount(transactions))
        events.extend(self._detect_duplicate_transactions(transactions))
        events.extend(self._detect_off_hours_activity(transactions))
        return events

    # -----------------------------------------------------------------
    def _detect_unusual_amount(self, transactions: list[Transaction]) -> list[SecurityEvent]:
        """
        Flags transactions that are statistical outliers within their
        department, using Median Absolute Deviation (MAD) rather than
        mean/stdev. MAD is robust to the outlier itself skewing the
        baseline — a known weakness of simple z-score detection on
        small samples (the outlier inflates its own stdev, hiding itself).
        """
        events = []
        by_department: dict[str, list[Transaction]] = defaultdict(list)
        for t in transactions:
            by_department[t.department].append(t)

        for dept, txns in by_department.items():
            if len(txns) < 3:
                continue  # not enough data to judge what's "unusual"
            amounts = [t.amount for t in txns]
            med = median(amounts)
            deviations = [abs(a - med) for a in amounts]
            mad = median(deviations)
            if mad == 0:
                continue

            # 0.6745 scales MAD to be comparable to standard deviation
            # under a normal distribution (standard robust-statistics constant)
            for t in txns:
                robust_z = 0.6745 * (t.amount - med) / mad
                if abs(robust_z) > MAD_Z_SCORE_THRESHOLD:
                    events.append(SecurityEvent(
                        severity="HIGH" if abs(robust_z) > 5 else "MEDIUM",
                        event_type="UNUSUAL_AMOUNT",
                        transaction_id=t.transaction_id,
                        message=(
                            f"Transaction amount {t.amount:,.0f} has a robust z-score "
                            f"of {robust_z:.1f} vs. the {dept} department median "
                            f"({med:,.0f})."
                        ),
                    ))
        return events

    # -----------------------------------------------------------------
    def _detect_duplicate_transactions(self, transactions: list[Transaction]) -> list[SecurityEvent]:
        """Flags transactions with the same department + amount within a short window."""
        events = []
        sorted_txns = sorted(transactions, key=lambda t: t.timestamp)

        for i, t1 in enumerate(sorted_txns):
            for t2 in sorted_txns[i + 1:]:
                delta_minutes = abs((t2.timestamp - t1.timestamp).total_seconds()) / 60
                if delta_minutes > DUPLICATE_WINDOW_MINUTES:
                    break  # sorted by time, no need to keep scanning further
                if (
                    t1.department == t2.department
                    and abs(t1.amount - t2.amount) < 0.01
                    and t1.transaction_id != t2.transaction_id
                ):
                    events.append(SecurityEvent(
                        severity="MEDIUM",
                        event_type="POSSIBLE_DUPLICATE",
                        transaction_id=t2.transaction_id,
                        message=(
                            f"Transaction {t2.transaction_id} matches {t1.transaction_id} "
                            f"in department and amount ({t2.amount:,.0f}) within "
                            f"{delta_minutes:.0f} minutes."
                        ),
                    ))
        return events

    # -----------------------------------------------------------------
    def _detect_off_hours_activity(self, transactions: list[Transaction]) -> list[SecurityEvent]:
        """Flags transactions timestamped outside normal business hours."""
        events = []
        for t in transactions:
            hour = t.timestamp.hour
            if hour >= OFF_HOURS_START or hour < OFF_HOURS_END:
                events.append(SecurityEvent(
                    severity="LOW",
                    event_type="OFF_HOURS_ACTIVITY",
                    transaction_id=t.transaction_id,
                    message=(
                        f"Transaction {t.transaction_id} was recorded at "
                        f"{t.timestamp.strftime('%H:%M')}, outside normal business hours."
                    ),
                ))
        return events