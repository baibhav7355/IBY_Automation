"""src/automation/__init__.py"""
from src.automation.supplier_automation import (
    AutomationResult,
    SupplierRequest,
    SupplierWorkflowEngine,
    run_sample_automation,
)
from src.automation.expense_automation import (
    ExpenseClaimRequest,
    ExpenseResult,
    ExpenseWorkflowEngine,
    run_sample_expense_batch,
)

__all__ = [
    "SupplierRequest",
    "AutomationResult",
    "SupplierWorkflowEngine",
    "run_sample_automation",
    "ExpenseClaimRequest",
    "ExpenseResult",
    "ExpenseWorkflowEngine",
    "run_sample_expense_batch",
]

