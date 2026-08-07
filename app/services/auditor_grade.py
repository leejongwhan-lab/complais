"""심사원 등급 코드 정규화.

Live MySQL ENUM (auditor_qualifications / auditor_external_certs / apply_grade):
  trainee | auditor | senior | verifier

App/UI 표준 코드:
  trainee | auditor | lead_auditor | verified_auditor
  (+ aliases: provisional/보, reviewer/검토자)
"""
from __future__ import annotations

from typing import Optional

# UI / API → DB ENUM
_TO_DB = {
    "trainee": "trainee",
    "provisional": "trainee",
    "보": "trainee",
    "심사원보": "trainee",
    "auditor": "auditor",
    "심사원": "auditor",
    "lead_auditor": "senior",
    "senior": "senior",
    "선임": "senior",
    "선임심사원": "senior",
    "verified_auditor": "verifier",
    "verifier": "verifier",
    "reviewer": "verifier",
    "검토자": "verifier",
    "검증심사원": "verifier",
}

# DB ENUM → UI 표준
_TO_UI = {
    "trainee": "trainee",
    "auditor": "auditor",
    "senior": "lead_auditor",
    "verifier": "verified_auditor",
    "lead_auditor": "lead_auditor",
    "verified_auditor": "verified_auditor",
}


def to_db_grade(value: Optional[str], default: str = "auditor") -> str:
    key = (value or default).strip().lower()
    return _TO_DB.get(key) or _TO_DB.get(default) or "auditor"


def to_ui_grade(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    key = str(value).strip().lower()
    return _TO_UI.get(key, key)
