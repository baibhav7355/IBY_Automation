"""Unit tests for the Expense Workflow Automation Prototype (Rank #2)."""

from src.automation.expense_automation import (
    ExpenseClaimRequest,
    ExpenseWorkflowEngine,
    run_sample_expense_batch,
)


def test_expense_workflow_auto_approval():
    engine = ExpenseWorkflowEngine(dry_run=True)
    req = ExpenseClaimRequest(
        claim_id="EXP-TEST-001",
        employee_id="EMP-01",
        employee_name="Test User",
        department="Sales",
        expense_category="entertainment",
        amount=18000.0,
        attendee_count=2,  # ¥9,000/head <= ¥10,000 limit
        has_receipt=True,
    )
    res = engine.process_claim(req)
    assert res.status == "AUTO_APPROVED"
    assert res.escalation_reason is None
    assert "ACCOUNTING APPROVED" in res.generated_comment_ja


def test_expense_workflow_entertainment_escalation():
    engine = ExpenseWorkflowEngine(dry_run=True)
    req = ExpenseClaimRequest(
        claim_id="EXP-TEST-002",
        employee_id="EMP-02",
        employee_name="Test User 2",
        department="Exec",
        expense_category="entertainment",
        amount=25000.0,
        attendee_count=2,  # ¥12,500/head > ¥10,000 limit -> Escalation
        has_receipt=True,
    )
    res = engine.process_claim(req)
    assert res.status == "ESCALATED_TO_MANAGER"
    assert res.escalation_reason is not None
    assert "exceeds corporate policy limit" in res.escalation_reason
    assert "FINANCIAL HOLD / APPROVAL REQUIRED" in res.generated_comment_ja


def test_expense_workflow_missing_receipt_escalation():
    engine = ExpenseWorkflowEngine(dry_run=True)
    req = ExpenseClaimRequest(
        claim_id="EXP-TEST-003",
        employee_id="EMP-03",
        employee_name="Test User 3",
        department="Operations",
        expense_category="travel_transit",
        amount=5000.0,
        attendee_count=1,
        has_receipt=False,  # Missing receipt
    )
    res = engine.process_claim(req)
    assert res.status == "ESCALATED_TO_MANAGER"
    assert "Official receipt is missing" in res.escalation_reason


def test_expense_workflow_travel_limit_escalation():
    engine = ExpenseWorkflowEngine(dry_run=True)
    req = ExpenseClaimRequest(
        claim_id="EXP-TEST-004",
        employee_id="EMP-04",
        employee_name="Test User 4",
        department="Engineering",
        expense_category="travel_transit",
        amount=35000.0,  # Exceeds ¥30,000 limit
        attendee_count=1,
        has_receipt=True,
    )
    res = engine.process_claim(req)
    assert res.status == "ESCALATED_TO_MANAGER"
    assert "exceeds auto-approval threshold" in res.escalation_reason


def test_run_sample_expense_batch():
    results = run_sample_expense_batch()
    assert len(results) == 4
    assert any(r.status == "AUTO_APPROVED" for r in results)
    assert any(r.status == "ESCALATED_TO_MANAGER" for r in results)
