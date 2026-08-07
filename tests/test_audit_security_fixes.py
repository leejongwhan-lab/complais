"""Unit checks for Domain 3/4/5 audit fixes (no DB required for masking/expiry evaluate)."""
from datetime import date, timedelta

from app.services.name_masking import mask_auditor_name, mask_company_name
from app.services.scope_expiry import evaluate_expiry


def test_mask_company_korean_prefix():
    assert mask_company_name("주식회사 마린텍") == "주식회사 마***"
    assert mask_company_name("삼성전자").startswith("삼")
    assert "***" in mask_company_name("삼성전자")
    assert mask_company_name("") == ""


def test_mask_auditor_name():
    assert mask_auditor_name("홍길동") == "홍*동"
    assert mask_auditor_name("김철") == "김*철"
    assert mask_auditor_name("박") == "박*"


def test_scope_expiry_statuses():
    today = date(2026, 8, 7)
    locked = evaluate_expiry(today - timedelta(days=1), today=today)
    assert locked.status == "locked"
    warn = evaluate_expiry(today + timedelta(days=10), today=today)
    assert warn.status == "warn"
    assert warn.days_remaining == 10
    ok = evaluate_expiry(today + timedelta(days=60), today=today)
    assert ok.status == "ok"
    none = evaluate_expiry(None, today=today)
    assert none.status == "ok"
