#!/usr/bin/env python3
"""
scripts/verify_submission.py
----------------------------
Automated End-to-End Submission Verification Harness.
Validates all requirements from `information.md`:
  1. Deliverable 1: `segments.jsonl` (schema, ISO-8601 UTC timestamps, coverage)
  2. Deliverable 2: Repository state and full unit/integration test suite (pytest)
  3. Deliverable 3: `final_report.md` (mandatory sections & metrics)
  4. Deliverable 4: `work_log.md` (7-day chronological diary & GenAI disclosure)
  5. Step 3 Prototype: `src/automation/supplier_automation.py` execution & demo

Usage:
  python scripts/verify_submission.py
"""

import sys
import os
import json
import re
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
os.environ["PYTHONPATH"] = str(ROOT)


def print_header(title: str):
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)

def check_mark(success: bool) -> str:
    return "[PASS]" if success else "[FAIL]"

def verify_segments_jsonl() -> bool:
    print_header("CHECK 1: Deliverable 1 - segments.jsonl Schema & Quality")
    segments_path = ROOT / "segments.jsonl"
    if not segments_path.exists():
        print(f"  {check_mark(False)} segments.jsonl does not exist at repository root.")
        return False

    valid_lines = 0
    sessions = set()
    labels = set()
    iso_regex = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    with open(segments_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"  {check_mark(False)} Line {line_num}: Invalid JSON - {e}")
                return False

            # Check required keys
            for key in ("session_id", "start", "end", "label"):
                if key not in obj:
                    print(f"  {check_mark(False)} Line {line_num}: Missing key '{key}'")
                    return False

            # Validate ISO 8601 UTC
            if not iso_regex.match(obj["start"]):
                print(f"  {check_mark(False)} Line {line_num}: 'start' ({obj['start']}) is not ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ)")
                return False
            if not iso_regex.match(obj["end"]):
                print(f"  {check_mark(False)} Line {line_num}: 'end' ({obj['end']}) is not ISO 8601 UTC (YYYY-MM-DDTHH:MM:SSZ)")
                return False

            # Validate start <= end
            t_start = datetime.strptime(obj["start"], "%Y-%m-%dT%H:%M:%SZ")
            t_end = datetime.strptime(obj["end"], "%Y-%m-%dT%H:%M:%SZ")
            if t_start > t_end:
                print(f"  {check_mark(False)} Line {line_num}: start timestamp > end timestamp")
                return False

            sessions.add(obj["session_id"])
            labels.add(obj["label"])
            valid_lines += 1

    print(f"  {check_mark(True)} segments.jsonl parsed successfully.")
    print(f"    - Total Business Process Segments : {valid_lines}")
    print(f"    - Unique Sessions Covered         : {len(sessions)} (Target: 15)")
    print(f"    - Unique Semantic Process Labels   : {len(labels)}")
    print(f"    - Top Labels                      : {sorted(list(labels))[:6]}")
    
    return valid_lines > 0 and len(sessions) == 15

def verify_final_report() -> bool:
    print_header("CHECK 2: Deliverable 3 - final_report.md Executive Coverage")
    report_path = ROOT / "final_report.md"
    if not report_path.exists():
        print(f"  {check_mark(False)} final_report.md does not exist.")
        return False

    text = report_path.read_text(encoding="utf-8")
    size_kb = len(text.encode("utf-8")) / 1024

    required_keywords = [
        ("Step 2 Analysis / Prioritization", ["supplier_communication", "expense_processing", "ROI", "Friction", "Volume"]),
        ("Step 3 Justification & Architecture", ["SupplierWorkflowEngine", "Deterministic", "Express", "REST", "Alternative"]),
        ("Residual Manual Work (Human-in-the-Loop)", ["Manual", "Human", "Escalat", "Exception", "Residual"]),
        ("Implementation Risk Matrix & Evidence", ["Risk", "Mitigation", "Shift_JIS", "Evidence", "Severity"]),
        ("7-Day Resource Allocation & Judgment", ["Day 1", "Day 4", "Good enough", "Allocation", "F1"]),
    ]

    all_found = True
    for section_name, keywords in required_keywords:
        found_kw = [kw for kw in keywords if kw.lower() in text.lower()]
        passed = len(found_kw) >= 3
        print(f"  {check_mark(passed)} {section_name} (matched: {', '.join(found_kw)})")
        if not passed:
            all_found = False

    print(f"  {check_mark(all_found)} final_report.md verified ({size_kb:.1f} KB, {len(text.splitlines())} lines).")
    return all_found

def verify_work_log() -> bool:
    print_header("CHECK 3: Deliverable 4 - work_log.md Diary & GenAI Disclosure")
    log_path = ROOT / "work_log.md"
    if not log_path.exists():
        print(f"  {check_mark(False)} work_log.md does not exist.")
        return False

    text = log_path.read_text(encoding="utf-8")
    days_found = [f"Day {i}" for i in range(1, 8) if f"Day {i}" in text]
    has_all_days = len(days_found) == 7
    has_genai = "generative ai" in text.lower() or "llm" in text.lower()
    has_trials = "trial" in text.lower() or "dead end" in text.lower()

    print(f"  {check_mark(has_all_days)} All 7 days covered: {days_found}")
    print(f"  {check_mark(has_trials)} Records trials and dead ends across stages.")
    print(f"  {check_mark(has_genai)} Explicit Generative AI disclosure included.")

    return has_all_days and has_trials and has_genai

def verify_prototype() -> bool:
    print_header("CHECK 4: Step 3 Prototype - supplier_automation.py Execution")
    try:
        from src.automation.supplier_automation import SupplierWorkflowEngine, SupplierRequest
        engine = SupplierWorkflowEngine()

        # Test Standard Auto-Approval
        req_standard = SupplierRequest(
            po_id="PO-2026-TEST-OK",
            vendor_id="SUP-TEST-100",
            vendor_name="千葉金属工業",
            request_type="quantity_change",
            item_code="ITM-9912",
            original_qty=100,
            requested_qty=110,  # +10% variance (<= 25%)
            unit_price=500.0,
            price_change_pct=2.0,  # +2% variance (<= 5%)
            delivery_date_shift_days=2,  # +2 days (<= 5 days)
            memo="納期の微調整"
        )
        res_ok = engine.process_request(req_standard)
        passed_ok = res_ok.status == "AUTO_APPROVED"
        print(f"  {check_mark(passed_ok)} Standard Request -> {res_ok.status} (Expected: AUTO_APPROVED)")

        # Test Price Breach Escalation
        req_breach = SupplierRequest(
            po_id="PO-2026-TEST-BREACH",
            vendor_id="SUP-TEST-200",
            vendor_name="三菱電機株式会社",
            request_type="price_revision",
            item_code="ITM-4421",
            original_qty=100,
            requested_qty=100,
            unit_price=1000.0,
            price_change_pct=15.0,  # +15% variance (> 5%)
            delivery_date_shift_days=0,
            memo="原材料高騰に伴う単価改定"
        )
        res_breach = engine.process_request(req_breach)
        passed_breach = res_breach.status == "ESCALATED_TO_MANAGER"
        print(f"  {check_mark(passed_breach)} Price Breach Request -> {res_breach.status} (Expected: ESCALATED_TO_MANAGER)")

        # Test Expense Automation (Rank #2 Multi-Process Extension)
        from src.automation.expense_automation import ExpenseWorkflowEngine, ExpenseClaimRequest

        exp_engine = ExpenseWorkflowEngine()
        exp_ok = exp_engine.process_claim(ExpenseClaimRequest(
            claim_id="EXP-VERIFY-01",
            employee_id="EMP-01",
            employee_name="山田 太郎",
            department="営業部",
            expense_category="entertainment",
            amount=15000.0,
            attendee_count=2,  # ¥7,500 <= ¥10,000
            has_receipt=True
        ))
        passed_exp_ok = exp_ok.status == "AUTO_APPROVED"
        print(f"  {check_mark(passed_exp_ok)} Expense Standard Claim -> {exp_ok.status} (Expected: AUTO_APPROVED)")

        exp_breach = exp_engine.process_claim(ExpenseClaimRequest(
            claim_id="EXP-VERIFY-02",
            employee_id="EMP-02",
            employee_name="佐藤 一郎",
            department="企画部",
            expense_category="entertainment",
            amount=30000.0,
            attendee_count=2,  # ¥15,000 > ¥10,000 limit
            has_receipt=True
        ))
        passed_exp_breach = exp_breach.status == "ESCALATED_TO_MANAGER"
        print(f"  {check_mark(passed_exp_breach)} Expense Limit Breach -> {exp_breach.status} (Expected: ESCALATED_TO_MANAGER)")

        return passed_ok and passed_breach and passed_exp_ok and passed_exp_breach
    except Exception as e:

        print(f"  {check_mark(False)} Prototype verification exception: {e}")
        return False


def verify_test_suite() -> bool:
    print_header("CHECK 5: Deliverable 2 - Full Unit & Integration Test Suite")
    import pytest
    res_code = pytest.main(["-q", "tests/"])
    passed = (res_code == 0)
    print(f"\n  {check_mark(passed)} Pytest suite execution exited with code {res_code} (0 = all tests passed).")
    return passed

def main():
    print("\n" + "#" * 80)
    print("  IBY JAPAN / FDE SUBMISSION VERIFICATION HARNESS")
    print("  Evaluating project compliance against `information.md`")
    print("#" * 80)

    results = {
        "Deliverable 1 (segments.jsonl)": verify_segments_jsonl(),
        "Deliverable 3 (final_report.md)": verify_final_report(),
        "Deliverable 4 (work_log.md)": verify_work_log(),
        "Step 3 Working Prototype": verify_prototype(),
        "Deliverable 2 (Automated Test Suite)": verify_test_suite(),
    }

    print_header("FINAL VERIFICATION SCORECARD")
    all_passed = True
    for item, passed in results.items():
        print(f"  {check_mark(passed)}  {item}")
        if not passed:
            all_passed = False

    print("=" * 80)
    if all_passed:
        print("  >>> [SUBMISSION READY] All deliverables verified with 100% compliance! <<<")
        print("=" * 80 + "\n")
        return 0
    else:
        print("  >>> [ACTION REQUIRED] Some checks failed. Review log above. <<<")
        print("=" * 80 + "\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())
