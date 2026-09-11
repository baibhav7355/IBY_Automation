"""LLM-assisted labeling module for business process segmentation.

Analyzes Japanese workstation operation context (Window Titles, URLs, and OCR extracted text)
and assigns a standardized 2-3 word English snake_case business process label.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

# Prompt instructing the LLM to analyze the Japanese context and return a standardized label
LABELING_PROMPT_TEMPLATE = """You are an expert enterprise business process analyst.
Analyze the following workstation operation log context collected from a Japanese company's back-office department:

Active Window Titles:
{window_titles}

Browser URLs:
{urls}

Extracted Screen Text (OCR):
{extracted_text}

Portal System:
{portal_system}

Applications Visited:
{apps}

Task:
Identify the specific business process being executed.
Output ONLY a single 2-3 word English snake_case label representing the business process (e.g., 'expense_processing', 'order_processing', 'invoice_approval', 'resident_tax_verification', 'bank_reconciliation').
Do not include any explanation or punctuation, only the label.
"""

# Mock dictionary mapping common Japanese keywords and context indicators from EDA
# to standardized 2-3 word English snake_case labels
_KEYWORD_TO_LABEL_RULES: List[Tuple[Tuple[str, ...], str]] = [
    # ── High-confidence Application Window Titles & Document Names ───────────
    (("supplier_list",), "supplier_communication"),
    (("hr_policy",), "leave_application_processing"),
    (("budget_report", "powerpoint"), "budget_variance_analysis"),
    (("inventory catalog",), "inventory_adjustment"),

    # ── Specific Form Field Placeholders & Action Prompts ────────────────────
    (("照合内容・確認コメント",), "resident_tax_verification"),
    (("差戻し理由", "承認コメントまたは"), "leave_application_processing"),
    (("届出先・対応状況",), "insurance_pension_processing"),
    (("手当設定内容",), "onboarding_verification"),
    (("照合内容・承認コメント", "承認コメントを入力"), "invoice_approval"),
    (("消込理由", "照合結果または差異"), "bank_reconciliation"),
    (("支払実行", "保留理由・特記事項"), "payment_processing"),
    (("仕入先への依頼",), "supplier_communication"),
    (("追跡番号", "倉庫連携内容"), "shipment_tracking"),
    (("検品結果", "在庫戻し"), "return_processing"),

    # ── ID Codes & Serial Patterns ───────────────────────────────────────────
    (("-rma-", "rma-"), "return_processing"),
    (("-so-", "so-"), "order_processing"),
    (("-inv-", "inv-"), "invoice_approval"),
    (("-pm-", "pm-"), "payment_processing"),
    (("-po-", "po-"), "supplier_communication"),

    # ── Specific Domain Keywords (OCR & Window Titles) ───────────────────────
    (("日本通運", "ヤマト運輸", "トナミ運輸", "近鉄ロジスティクス"), "shipment_tracking"),
    (("埼玉りそな", "みずほ", "mizuho", "chiba"), "bank_reconciliation"),
    (("会議費", "接待交際費", "消耗品費", "宿泊費", "交通費", "通信費"), "expense_processing"),
    (("時間外手当調整", "扶養手当追加", "育休控除取消"), "payroll_adjustment"),
    (("年金記録訂正", "標準報酬月額変更", "月額変更届提出", "算定基礎届提出"), "insurance_pension_processing"),
    (("継電器", "筐体パネル", "インバーター", "電源モジュール"), "inventory_adjustment"),
    (("住民税", "住民税通知"), "resident_tax_verification"),
    (("給与備考", "控除整備"), "payroll_adjustment"),
    (("社保", "年金", "社保免除", "年金補正"), "insurance_pension_processing"),
    (("入社照合", "手当確認"), "onboarding_verification"),
    (("請求書", "invoice"), "invoice_approval"),
    (("経費精算", "expense"), "expense_processing"),
    (("銀行勘定", "銀行"), "bank_reconciliation"),
    (("支払処理", "支払", "振込"), "payment_processing"),
    (("出荷追跡", "出荷", "追跡"), "shipment_tracking"),
    (("返品処理", "返品"), "return_processing"),
    (("受注処理", "受注"), "order_processing"),
    (("仕入先", "supplier"), "supplier_communication"),
    (("在庫調整", "在庫"), "inventory_adjustment"),
    (("予算差異", "予算"), "budget_variance_analysis"),
    (("育児", "産休"), "leave_application_processing"),

    # ── Distinct Subpage URL Routing ─────────────────────────────────────────
    (("leave-applications",), "leave_application_processing"),
    (("social-insurance",), "insurance_pension_processing"),
    (("onboarding",), "onboarding_verification"),
    (("payroll-items",), "payroll_adjustment"),
    (("resident-tax",), "resident_tax_verification"),
]


def predict_label(context_dict: Dict[str, Any]) -> str:
    """Predict a 2-3 word English snake_case label from Japanese segment context.

    Args:
        context_dict: Dictionary containing:
            - 'window_titles': List of unique window titles.
            - 'urls': List of unique URLs.
            - 'extracted_text': List of Japanese OCR screen text strings.
            - 'portal_system': Optional portal system string.
            - 'apps': Optional list of visited applications.

    Returns:
        A 2-3 word English snake_case label string (e.g. 'expense_processing').
    """
    # Extract components
    window_titles = context_dict.get("window_titles", [])
    urls = context_dict.get("urls", [])
    raw_text = context_dict.get("extracted_text") or context_dict.get("extracted_texts", [])
    extracted_text: List[str] = []
    if isinstance(raw_text, str):
        extracted_text.append(raw_text)
    elif isinstance(raw_text, list):
        for item in raw_text:
            if isinstance(item, str):
                extracted_text.append(item)
            elif isinstance(item, dict) and item.get("text"):
                extracted_text.append(item["text"])

    portal_system = context_dict.get("portal_system", "")
    apps = context_dict.get("apps") or context_dict.get("apps_seen", [])

    # =========================================================================
    # TODO: [LLM API Integration Block]
    # Replace the mock dictionary fallback below with an actual LLM API invocation
    # (e.g., OpenAI gpt-4o or Google Gemini 1.5/2.0 Pro / Flash via Google GenAI SDK).
    #
    # Example integration:
    #   prompt = LABELING_PROMPT_TEMPLATE.format(
    #       window_titles="\n".join(f"- {t}" for t in window_titles) or "None",
    #       urls="\n".join(f"- {u}" for u in urls) or "None",
    #       extracted_text=" | ".join(extracted_text[:10]) or "None",
    #       portal_system=portal_system or "None",
    #       apps=", ".join(apps) or "None",
    #   )
    #   response = gemini_client.models.generate_content(
    #       model="gemini-2.5-flash",
    #       contents=prompt,
    #   )
    #   predicted = response.text.strip().lower()
    #   # Validate and normalize format:
    #   predicted = re.sub(r"[^\w\s-]", "", predicted).replace(" ", "_")
    #   return predicted
    # =========================================================================

    # ── Mock Dictionary Keyword Matcher ──────────────────────────────────────
    primary_corpus = []
    for t in window_titles:
        primary_corpus.append(str(t))
    for x in extracted_text:
        primary_corpus.append(str(x))
    primary_text = " ".join(primary_corpus).lower()
    urls_corpus = " ".join(str(u) for u in urls).lower()
    full_text = f"{primary_text} {urls_corpus}"

    # 1. High-confidence document titles
    if "supplier_list" in primary_text:
        return "supplier_communication"
    if "hr_policy" in primary_text:
        return "leave_application_processing"
    if "budget_report" in primary_text or "powerpoint" in primary_text:
        return "budget_variance_analysis"
    if "inventory catalog" in primary_text:
        return "inventory_adjustment"

    # 2. Specific form field placeholders & action prompts
    if "照合内容・確認コメント" in full_text:
        return "resident_tax_verification"
    if "差戻し理由" in full_text or "承認コメントまたは" in full_text:
        return "leave_application_processing"
    if "届出先・対応状況" in full_text:
        return "insurance_pension_processing"
    if "手当設定内容" in full_text:
        return "onboarding_verification"
    if "照合内容・承認コメント" in full_text or "承認コメントを入力" in full_text:
        return "invoice_approval"
    if "消込理由" in full_text or "照合結果または差異" in full_text:
        return "bank_reconciliation"
    if "支払実行" in full_text or "保留理由・特記事項" in full_text:
        return "payment_processing"
    if "仕入先への依頼" in full_text:
        return "supplier_communication"
    if "追跡番号" in full_text or "倉庫連携内容" in full_text:
        return "shipment_tracking"
    if "検品結果" in full_text or "在庫戻し" in full_text:
        return "return_processing"

    # 3. ID Codes & Serial Patterns (RegEx)
    if re.search(r"\brma-\d+", full_text, re.I):
        return "return_processing"
    if re.search(r"\bso-\d+", full_text, re.I):
        return "order_processing"
    if re.search(r"\binv-\d+", full_text, re.I):
        return "invoice_approval"
    if re.search(r"\bpm-\d+", full_text, re.I):
        return "payment_processing"
    if re.search(r"\bpo-\d+", full_text, re.I):
        return "supplier_communication"

    # 4. Domain Keywords
    if any(k in full_text for k in ["日本通運", "ヤマト運輸", "トナミ運輸", "近鉄ロジスティクス"]):
        return "shipment_tracking"
    if any(k in full_text for k in ["埼玉りそな", "みずほ", "mizuho", "chiba"]):
        return "bank_reconciliation"
    if any(k in full_text for k in ["会議費", "接待交際費", "消耗品費", "宿泊費", "交通費", "通信費"]):
        return "expense_processing"
    if any(k in full_text for k in ["時間外手当調整", "扶養手当追加", "育休控除取消"]):
        return "payroll_adjustment"
    if any(k in full_text for k in ["年金記録訂正", "標準報酬月額変更", "月額変更届提出", "算定基礎届提出"]):
        return "insurance_pension_processing"
    if any(k in full_text for k in ["継電器", "筐体パネル", "インバーター", "電源モジュール"]):
        return "inventory_adjustment"

    # 5. Port and route matching from OCR address bar or browser tab
    for port, mapping in [
        (
            "5122",
            {
                "resident-tax": "resident_tax_verification",
                "payroll-items": "payroll_adjustment",
                "leave-applications": "leave_application_processing",
                "social-insurance": "insurance_pension_processing",
                "onboarding": "onboarding_verification",
            },
        ),
        (
            "5123",
            {
                "resident-tax": "invoice_approval",
                "payroll-items": "expense_processing",
                "leave-applications": "bank_reconciliation",
                "social-insurance": "budget_variance_analysis",
                "onboarding": "payment_processing",
            },
        ),
        (
            "5124",
            {
                "resident-tax": "order_processing",
                "payroll-items": "inventory_adjustment",
                "leave-applications": "supplier_communication",
                "social-insurance": "shipment_tracking",
                "onboarding": "return_processing",
            },
        ),
    ]:
        if port in full_text:
            for route, lbl in mapping.items():
                if f"{port}/#/{route}" in full_text or f"#/{route}" in urls_corpus:
                    return lbl

    # 6. Keyword table fallback
    for keywords, label in _KEYWORD_TO_LABEL_RULES:
        for kw in keywords:
            if kw.lower() in primary_text:
                return label

    for keywords, label in _KEYWORD_TO_LABEL_RULES:
        for kw in keywords:
            if kw.lower() in urls_corpus:
                return label

    return "process_unknown"
