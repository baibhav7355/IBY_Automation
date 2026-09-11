"""Step 3 Working Automation Prototype: Supplier Communication & Order Workflow Engine.

Automates the highest-ROI bottleneck identified in Dataset B (Rank #1: supplier_communication),
eliminating redundant cross-application copy-pasting between ERP portal, Word contract files,
and procurement reference sheets.

Architecture:
  - Deterministic Python backend service (REST/CLI compatible).
  - Validates PO items against vendor contract rules and price deviation thresholds.
  - Generates standardized Japanese business communication payloads.
  - Automatically handles routine cases (80% volume) and flags non-standard exceptions
    for human-in-the-loop managerial sign-off.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class SupplierRequest:
    """Incoming purchase order or vendor communication request."""

    po_id: str
    vendor_id: str
    vendor_name: str
    request_type: str  # e.g., 'quantity_change', 'price_revision', 'spec_change', 'cert_request'
    item_code: str
    original_qty: int
    requested_qty: int
    unit_price: float
    price_change_pct: float = 0.0
    delivery_date_shift_days: int = 0
    memo: str = ""


@dataclass
class AutomationResult:
    """Result of automated processing and exception routing."""

    po_id: str
    status: str  # 'AUTO_APPROVED', 'ESCALATED_TO_MANAGER', 'REJECTED'
    action_taken: str
    generated_comment_ja: str
    escalation_reason: Optional[str] = None
    processed_at_iso: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class SupplierWorkflowEngine:
    """Modular automation engine for supplier communications and PO adjustments."""

    # Operational policy thresholds (derived from back-office contract guidelines)
    MAX_AUTO_QTY_VARIANCE_PCT = 25.0  # > 25% requires procurement manager approval
    MAX_AUTO_PRICE_CHANGE_PCT = 5.0   # > 5% price increase requires financial sign-off
    MAX_AUTO_DELIVERY_SHIFT_DAYS = 5  # > 5 days shift requires production scheduling review

    def __init__(self, dry_run: bool = False) -> None:
        self.dry_run = dry_run
        self.audit_log: List[AutomationResult] = []

    def process_request(self, req: SupplierRequest) -> AutomationResult:
        """Process a single supplier communication request against business rules."""
        # 1. Validation & Policy Exception Checks
        qty_diff_pct = (
            abs(req.requested_qty - req.original_qty) / req.original_qty * 100.0
            if req.original_qty > 0
            else 0.0
        )

        escalations = []
        if qty_diff_pct > self.MAX_AUTO_QTY_VARIANCE_PCT:
            escalations.append(
                f"Quantity variance ({qty_diff_pct:.1f}%) exceeds auto-approval threshold ({self.MAX_AUTO_QTY_VARIANCE_PCT}%)"
            )

        if req.price_change_pct > self.MAX_AUTO_PRICE_CHANGE_PCT:
            escalations.append(
                f"Price increase ({req.price_change_pct:.1f}%) exceeds standard limit ({self.MAX_AUTO_PRICE_CHANGE_PCT}%)"
            )

        if req.delivery_date_shift_days > self.MAX_AUTO_DELIVERY_SHIFT_DAYS:
            escalations.append(
                f"Delivery delay ({req.delivery_date_shift_days} days) exceeds auto-tolerance ({self.MAX_AUTO_DELIVERY_SHIFT_DAYS} days)"
            )

        # 2. Routing Decision
        if escalations:
            status = "ESCALATED_TO_MANAGER"
            action = "Escalated for human procurement review"
            comment = (
                f"【自動保留・要承認】{req.vendor_name}宛 発注番号:{req.po_id}。 "
                f"理由: {'; '.join(escalations)}。担当マネージャーの確認が必要です。"
            )
            reason = "; ".join(escalations)
        else:
            status = "AUTO_APPROVED"
            action = "Auto-dispatched vendor confirmation"
            if req.request_type == "quantity_change":
                comment = (
                    f"【自動処理完了】{req.vendor_name}御中 発注番号:{req.po_id}の数量変更依頼を承認しました。"
                    f"（変更前:{req.original_qty} → 変更後:{req.requested_qty}）"
                )
            elif req.request_type == "spec_change":
                comment = (
                    f"【自動処理完了】{req.vendor_name}御中 発注番号:{req.po_id}の仕様変更確認を登録しました。"
                )
            elif req.request_type == "cert_request":
                comment = (
                    f"【自動処理完了】{req.vendor_name}御中 発注番号:{req.po_id}に関する品質証明書の送付依頼を発行しました。"
                )
            else:
                comment = (
                    f"【自動処理完了】{req.vendor_name}御中 発注番号:{req.po_id}の取引先連絡を正常に処理しました。"
                )
            reason = None

        result = AutomationResult(
            po_id=req.po_id,
            status=status,
            action_taken=action,
            generated_comment_ja=comment,
            escalation_reason=reason,
        )
        self.audit_log.append(result)
        return result

    def batch_process(self, requests: List[SupplierRequest]) -> List[AutomationResult]:
        """Process a batch of supplier communication requests."""
        return [self.process_request(r) for r in requests]


def run_sample_automation() -> Dict[str, Any]:
    """Execute sample simulation demonstrating straight-through processing and exception handling."""
    engine = SupplierWorkflowEngine(dry_run=True)

    sample_cases = [
        SupplierRequest(
            po_id="PO-2026-469",
            vendor_id="SUP-175001",
            vendor_name="千葉金属工業",
            request_type="quantity_change",
            item_code="PN-8201",
            original_qty=100,
            requested_qty=110,  # 10% variance (Auto-approved)
            unit_price=4500.0,
            price_change_pct=0.0,
            delivery_date_shift_days=2,
        ),
        SupplierRequest(
            po_id="PO-2026-512",
            vendor_id="SUP-175002",
            vendor_name="三菱電機株式会社",
            request_type="price_revision",
            item_code="INV-401",
            original_qty=50,
            requested_qty=50,
            unit_price=82000.0,
            price_change_pct=12.5,  # 12.5% increase (Escalated to manager)
            delivery_date_shift_days=0,
        ),
        SupplierRequest(
            po_id="PO-2026-681",
            vendor_id="SUP-175003",
            vendor_name="シャープ株式会社",
            request_type="cert_request",
            item_code="DSP-109",
            original_qty=200,
            requested_qty=200,
            unit_price=12000.0,
            price_change_pct=0.0,
            delivery_date_shift_days=0,
        ),
    ]

    results = engine.batch_process(sample_cases)
    return {
        "processed_count": len(results),
        "auto_approved_count": sum(1 for r in results if r.status == "AUTO_APPROVED"),
        "escalated_count": sum(1 for r in results if r.status == "ESCALATED_TO_MANAGER"),
        "results": [r.__dict__ for r in results],
    }


if __name__ == "__main__":
    output = run_sample_automation()
    print(json.dumps(output, indent=2, ensure_ascii=False))
