"""Unit tests for the Step 3 Automation Prototype."""

from src.automation.supplier_automation import (
    SupplierRequest,
    SupplierWorkflowEngine,
    run_sample_automation,
)


def test_supplier_workflow_engine_auto_approval():
    engine = SupplierWorkflowEngine(dry_run=True)
    req = SupplierRequest(
        po_id="PO-TEST-001",
        vendor_id="V-100",
        vendor_name="Test Vendor",
        request_type="quantity_change",
        item_code="ITM-1",
        original_qty=100,
        requested_qty=110,  # 10% change within 25% limit
        unit_price=1000.0,
        price_change_pct=0.0,
        delivery_date_shift_days=1,
    )
    res = engine.process_request(req)
    assert res.status == "AUTO_APPROVED"
    assert res.escalation_reason is None
    assert "自動処理完了" in res.generated_comment_ja


def test_supplier_workflow_engine_escalation():
    engine = SupplierWorkflowEngine(dry_run=True)
    req = SupplierRequest(
        po_id="PO-TEST-002",
        vendor_id="V-200",
        vendor_name="Test Vendor 2",
        request_type="price_revision",
        item_code="ITM-2",
        original_qty=100,
        requested_qty=100,
        unit_price=5000.0,
        price_change_pct=15.0,  # 15% > 5% limit
        delivery_date_shift_days=0,
    )
    res = engine.process_request(req)
    assert res.status == "ESCALATED_TO_MANAGER"
    assert res.escalation_reason is not None
    assert "自動保留・要承認" in res.generated_comment_ja


def test_supplier_workflow_engine_escalations_all_rules():
    engine = SupplierWorkflowEngine(dry_run=True)
    # 1. Delivery delay > 5 days
    req_delay = SupplierRequest(
        po_id="PO-DELAY-01",
        vendor_id="V-300",
        vendor_name="Vendor Delay",
        request_type="delivery_shift",
        item_code="ITM-3",
        original_qty=50,
        requested_qty=50,
        unit_price=1000.0,
        price_change_pct=0.0,
        delivery_date_shift_days=8,
    )
    res_delay = engine.process_request(req_delay)
    assert res_delay.status == "ESCALATED_TO_MANAGER"
    assert "Delivery delay" in res_delay.escalation_reason

    # 2. Qty variance > 25%
    req_qty = SupplierRequest(
        po_id="PO-QTY-01",
        vendor_id="V-400",
        vendor_name="Vendor Qty",
        request_type="quantity_change",
        item_code="ITM-4",
        original_qty=100,
        requested_qty=150,  # 50% change > 25%
        unit_price=1000.0,
        price_change_pct=0.0,
        delivery_date_shift_days=0,
    )
    res_qty = engine.process_request(req_qty)
    assert res_qty.status == "ESCALATED_TO_MANAGER"
    assert "Quantity variance" in res_qty.escalation_reason


def test_run_sample_automation_batch():
    output = run_sample_automation()
    assert output["processed_count"] == 3
    assert output["auto_approved_count"] == 2
    assert output["escalated_count"] == 1


def test_main_cli_demo(monkeypatch, capsys):
    import sys
    from src.automation.supplier_automation import main

    monkeypatch.setattr(sys, "argv", ["supplier_automation.py", "--demo"])
    main()
    captured = capsys.readouterr()
    assert "IBY JAPAN ENTERPRISE AUTOMATION ENGINE" in captured.out
    assert "[PROTOTYPE EXECUTION SCORECARD]" in captured.out

