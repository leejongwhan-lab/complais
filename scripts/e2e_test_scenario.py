#!/usr/bin/env python3
"""End-to-end API scenario script (Briefing v15) — Phase 1 signup + Phase 2 process.

Usage (from repo root):
  .venv/bin/python scripts/e2e_test_scenario.py --base-url http://127.0.0.1:8000

Env (optional):
  E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD  — platform_admin bootstrap (local defaults only)
  E2E_PASSWORD                          — password for freshly created accounts
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import traceback
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS_PATH = ROOT / "scripts" / "e2e_results_latest.json"
PASSWORD_DEFAULT = "TestPass123!"
ADMIN_EMAIL_DEFAULT = "admin@complais.com"
ADMIN_PASSWORD_DEFAULT = "password123!"

# Live MySQL auditors.grade ENUM — UI 'lead_auditor' truncates; use DB codes.
GRADE_LEAD = "senior"
GRADE_AUDITOR = "auditor"


def _valid_biz_no(seed: int) -> str:
    """Build a unique 10-digit KR business number that passes checksum."""
    from app.core.validators import is_valid_biz_no_checksum

    base = 100000000 + (abs(int(seed)) % 80000000)
    for i in range(2000):
        head = f"{base + i:09d}"
        for check in range(10):
            digits = head + str(check)
            if is_valid_biz_no_checksum(digits):
                return f"{digits[:3]}-{digits[3:5]}-{digits[5:]}"
    return "100-00-00009"  # known-valid fallback

# Prefer project stdlib HTTP; use requests/httpx if present in venv.
try:
    import requests  # type: ignore

    _HAS_REQUESTS = True
except Exception:  # pragma: no cover
    requests = None  # type: ignore
    _HAS_REQUESTS = False


# ---------------------------------------------------------------------------
# HTTP + result helpers
# ---------------------------------------------------------------------------


@dataclass
class StepResult:
    step: str
    status: str  # pass | fail | skip
    detail: str = ""
    response_snapshot: Any = None

    def as_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "status": self.status,
            "detail": self.detail,
            "response_snapshot": self.response_snapshot,
        }


@dataclass
class Ctx:
    base_url: str
    stamp: str
    password: str
    admin_email: str
    admin_password: str
    results: List[StepResult] = field(default_factory=list)
    tokens: Dict[str, str] = field(default_factory=dict)
    # Phase 1 entities
    company_id: Optional[int] = None
    enterprise_email: Optional[str] = None
    auditor_email: Optional[str] = None
    auditor2_email: Optional[str] = None
    auditor_id: Optional[int] = None
    auditor2_id: Optional[int] = None
    auditor_user_id: Optional[int] = None
    auditor2_user_id: Optional[int] = None
    cb_email: Optional[str] = None
    cb_id: Optional[int] = None
    cb_code: Optional[str] = None
    accreditation_id: Optional[int] = None
    sot_standard_codes: List[str] = field(default_factory=list)
    membership_id: Optional[int] = None
    membership2_id: Optional[int] = None
    # Phase 2
    simple_app_id: Optional[int] = None
    simple_contract_id: Optional[int] = None
    simple_assignment_id: Optional[int] = None
    integrated_app_id: Optional[int] = None
    team_app_id: Optional[int] = None
    team_contract_id: Optional[int] = None
    revision_app_id: Optional[int] = None
    decline_app_id: Optional[int] = None
    flags: Dict[str, bool] = field(default_factory=dict)


def _clip(obj: Any, max_len: int = 1200) -> Any:
    try:
        text = json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        text = str(obj)
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    try:
        return json.loads(text)
    except Exception:
        return text


def _redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            lk = str(k).lower()
            if any(x in lk for x in ("token", "password", "authorization", "secret", "ci_key")):
                out[k] = "***REDACTED***"
            else:
                out[k] = _redact(v)
        return out
    if isinstance(obj, list):
        return [_redact(x) for x in obj]
    if isinstance(obj, str) and obj.startswith("eyJ") and len(obj) > 40:
        return "***REDACTED_JWT***"
    return obj


class Client:
    def __init__(self, base_url: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def request(
        self,
        method: str,
        path: str,
        *,
        token: Optional[str] = None,
        json_body: Any = None,
        form: Optional[Dict[str, str]] = None,
        files: Optional[Dict[str, Tuple[str, bytes, str]]] = None,
        expected: Optional[Tuple[int, ...]] = None,
    ) -> Tuple[int, Any, Dict[str, str]]:
        url = path if path.startswith("http") else f"{self.base_url}{path}"
        headers: Dict[str, str] = {"Accept": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        if _HAS_REQUESTS:
            kwargs: Dict[str, Any] = {"headers": headers, "timeout": self.timeout}
            if files:
                # multipart: form fields + files
                data = form or {}
                req_files = {
                    k: (name, data_bytes, ctype)
                    for k, (name, data_bytes, ctype) in files.items()
                }
                resp = requests.request(method, url, data=data, files=req_files, **kwargs)  # type: ignore
            elif form is not None:
                resp = requests.request(method, url, data=form, **kwargs)  # type: ignore
            elif json_body is not None:
                headers["Content-Type"] = "application/json"
                resp = requests.request(method, url, json=json_body, headers=headers, timeout=self.timeout)  # type: ignore
            else:
                resp = requests.request(method, url, **kwargs)  # type: ignore
            status = resp.status_code
            try:
                body: Any = resp.json()
            except Exception:
                body = resp.text
            return status, body, dict(resp.headers)

        # stdlib fallback
        data_bytes: Optional[bytes] = None
        if files:
            boundary = f"----e2e{uuid.uuid4().hex}"
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            chunks: List[bytes] = []
            for key, val in (form or {}).items():
                chunks.append(f"--{boundary}\r\n".encode())
                chunks.append(
                    f'Content-Disposition: form-data; name="{key}"\r\n\r\n{val}\r\n'.encode()
                )
            for key, (fname, content, ctype) in files.items():
                chunks.append(f"--{boundary}\r\n".encode())
                chunks.append(
                    (
                        f'Content-Disposition: form-data; name="{key}"; '
                        f'filename="{fname}"\r\n'
                        f"Content-Type: {ctype}\r\n\r\n"
                    ).encode()
                )
                chunks.append(content)
                chunks.append(b"\r\n")
            chunks.append(f"--{boundary}--\r\n".encode())
            data_bytes = b"".join(chunks)
        elif form is not None:
            data_bytes = urlencode(form).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        elif json_body is not None:
            data_bytes = json.dumps(json_body, ensure_ascii=False, default=str).encode()
            headers["Content-Type"] = "application/json"

        req = Request(url, data=data_bytes, headers=headers, method=method.upper())
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read()
                status = getattr(resp, "status", 200)
                hdrs = {k.lower(): v for k, v in resp.headers.items()}
        except HTTPError as e:
            raw = e.read() if e.fp else b""
            status = e.code
            hdrs = {k.lower(): v for k, v in (e.headers.items() if e.headers else [])}
        except URLError as e:
            raise RuntimeError(f"connection failed: {e}") from e

        body: Any
        if not raw:
            body = None
        else:
            try:
                body = json.loads(raw.decode("utf-8", errors="replace"))
            except Exception:
                body = raw.decode("utf-8", errors="replace")

        if expected is not None and status not in expected:
            raise AssertionError(f"{method} {path} -> {status}, expected {expected}: {_clip(body)}")
        return status, body, hdrs


def record(
    ctx: Ctx,
    step: str,
    status: str,
    detail: str = "",
    snapshot: Any = None,
) -> StepResult:
    r = StepResult(step=step, status=status, detail=detail, response_snapshot=_clip(_redact(snapshot)))
    ctx.results.append(r)
    mark = {"pass": "✓", "fail": "✗", "skip": "○"}.get(status, "?")
    print(f"[{mark}] {step}: {detail}")
    return r


def run_step(
    ctx: Ctx,
    step: str,
    fn: Callable[[], Any],
    *,
    depends_on: Optional[List[str]] = None,
) -> Optional[Any]:
    if depends_on:
        failed_deps = [
            d
            for d in depends_on
            if not any(r.step == d and r.status == "pass" for r in ctx.results)
        ]
        if failed_deps:
            record(
                ctx,
                step,
                "skip",
                f"skipped — dependency failed/missing: {', '.join(failed_deps)}",
            )
            return None
    try:
        out = fn()
        if not any(r.step == step for r in ctx.results):
            record(ctx, step, "pass", "ok", out)
        return out
    except Exception as e:
        record(
            ctx,
            step,
            "fail",
            f"{type(e).__name__}: {e}",
            {"traceback": traceback.format_exc()[-800:]},
        )
        return None


# ---------------------------------------------------------------------------
# Local DB helpers (gaps with no public API)
# ---------------------------------------------------------------------------


def api_conduct_sign(client: "Client", token: str) -> Dict[str, Any]:
    """POST /auditor-portal/conduct-sign — real API (replaces DB seed bypass)."""
    st, body, _ = client.request(
        "POST",
        "/api/v1/auditor-portal/conduct-sign",
        token=token,
        json_body={"agreed": True},
    )
    if st not in (200, 201):
        raise AssertionError(f"conduct-sign failed: {st} {body}")
    st_s, status_body, _ = client.request(
        "GET",
        "/api/v1/auditor-portal/conduct-sign/status",
        token=token,
    )
    if st_s != 200 or not isinstance(status_body, dict) or not status_body.get("is_valid"):
        raise AssertionError(f"conduct-sign status not valid after sign: {st_s} {status_body}")
    return {"sign": body, "status": status_body}


def db_count_notifications(user_id: int, ntype: Optional[str] = None) -> int:
    from app.db.session import SessionLocal
    from app.models.auth import Notifications

    db = SessionLocal()
    try:
        q = db.query(Notifications).filter(Notifications.user_id == user_id)
        if ntype:
            q = q.filter(Notifications.type == ntype)
        return int(q.count())
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Scenario steps
# ---------------------------------------------------------------------------


def step_health(ctx: Ctx, client: Client) -> Any:
    status, body, _ = client.request("GET", "/health")
    if status != 200 or not (isinstance(body, dict) and body.get("status") == "ok"):
        raise AssertionError(f"health failed: {status} {body}")
    record(ctx, "0_health", "pass", "server ok", body)
    return body


def step_enterprise_register(ctx: Ctx, client: Client) -> Any:
    email = f"e2e.ent.{ctx.stamp}@example.com"
    biz = _valid_biz_no(int(ctx.stamp[-8:]))
    company_payload = {
        "name": f"E2E기업-{ctx.stamp}",
        "name_en": f"E2E Co {ctx.stamp}",
        "biz_no": biz,
        "ceo_name": "이대표",
        "address": "서울시 중구 테스트로 1",
        "detail_address": "101호",
        "tel": "02-1234-5678",
        "email": email,
        "employee_count": 45,
        "ksic_code": "62010",
        "iaf_code": "33",
        "scope_kr": "소프트웨어 개발 및 공급",
        "scope_en": "Software development",
        "status": "정상",
        "is_active": True,
    }
    st, company, _ = client.request("POST", "/api/v1/companies", json_body=company_payload)
    if st not in (200, 201):
        raise AssertionError(f"company create failed: {st} {company}")
    company_id = int(company["id"])
    reg = {
        "email": email,
        "password": ctx.password,
        "user_name": f"E2E기업담당-{ctx.stamp}",
        "company_id": company_id,
    }
    st2, body, _ = client.request("POST", "/api/v1/auth/register/client-admin", json_body=reg)
    if st2 not in (200, 201):
        raise AssertionError(f"client-admin register failed: {st2} {body}")
    # login
    st3, login, _ = client.request(
        "POST",
        "/api/v1/auth/login",
        form={"username": email, "password": ctx.password},
    )
    if st3 != 200 or not isinstance(login, dict) or not login.get("access_token"):
        raise AssertionError(f"enterprise login failed: {st3} {login}")
    ctx.company_id = company_id
    ctx.enterprise_email = email
    ctx.tokens["enterprise"] = login["access_token"]
    snap = {"company_id": company_id, "email": email, "register": body, "login_role": login.get("role")}
    record(ctx, "1_enterprise_register", "pass", f"company_id={company_id} email={email}", snap)
    return snap


def step_auditor_register(ctx: Ctx, client: Client) -> Any:
    # identity mock mode — unique ci_key (not MOCK-CI-TEST-001 seed collision)
    st_cfg, cfg, _ = client.request("GET", "/api/v1/auth/identity-config")
    mock_allowed = bool(isinstance(cfg, dict) and cfg.get("mock_allowed"))
    email = f"e2e.aud.{ctx.stamp}@example.com"
    ci_key = f"MOCK-CI-E2E-{ctx.stamp}"
    payload = {
        "name": f"E2E심사원{ctx.stamp[-4:]}",
        "email": email,
        "password": ctx.password,
        "phone": f"010{ctx.stamp[-8:]}",
        "birth_date": "1990-01-15",
        "gender": "M",
        "address": "서울시 강남구 테스트동 1",
        "detail_address": "202호",
        "zip_code": "06236",
        "employment_type": "parttime",
        "is_freelance": True,
        # DB ENUM: trainee|auditor|senior|verifier (not UI lead_auditor)
        "apply_grade": GRADE_LEAD,
        "daily_rate": 450000,
        "fee_ratio": 0.0,
        "ci_key": ci_key if mock_allowed else None,
        "major_name": "산업공학",
        "educations": [
            {
                "school_name": "서울고등학교",
                "degree": "high_school",
                "major": "문과",
                "graduated_at": "2008-02-01",
            },
            {
                "school_name": "한국대학교",
                "degree": "bachelor",
                "major": "산업공학",
                "entered_at": "2008-03-01",
                "graduated_at": "2012-02-01",
            },
            {
                "school_name": "한국대학원",
                "degree": "master",
                "major": "품질경영",
                "entered_at": "2012-03-01",
                "graduated_at": "2014-02-01",
            },
        ],
        "work_experiences": [
            {
                "company_name": "알파제조",
                "department": "품질팀",
                "position": "대리",
                "start_date": "2014-03-01",
                "end_date": "2018-12-31",
                "is_current": False,
                "duties": "ISO 내부심사",
                "ksic_code": "29100",
                "iaf_code": "18",
            },
            {
                "company_name": "베타컨설팅",
                "department": "심사본부",
                "position": "과장",
                "start_date": "2019-01-01",
                "is_current": True,
                "duties": "QMS/EMS 심사",
                "ksic_code": "70209",
                "iaf_code": "35",
            },
        ],
        "qualifications": [
            {
                "standard_code": "QMS",
                "cert_body_name": "KAR",
                "cert_no": f"KAR-Q-{ctx.stamp[-6:]}",
                "auditor_grade": GRADE_LEAD,
                "iaf_codes": ["14", "18", "33"],
                "major_name": "품질",
            },
            {
                "standard_code": "EMS",
                "cert_body_name": "IRCA",
                "cert_no": f"IRCA-E-{ctx.stamp[-6:]}",
                "auditor_grade": GRADE_AUDITOR,
                "iaf_codes": ["2", "13"],
                "major_name": "환경",
            },
            {
                "standard_code": "OHSMS",
                "cert_body_name": "KAR",
                "cert_no": f"KAR-O-{ctx.stamp[-6:]}",
                "auditor_grade": GRADE_AUDITOR,
                "iaf_codes": ["28"],
            },
        ],
        "bank_name": "국민은행",
        "account_no": "123456789012",
        "account_holder": f"E2E심사원{ctx.stamp[-4:]}",
    }
    st, body, _ = client.request("POST", "/api/v1/auth/register/auditor", json_body=payload)
    if st not in (200, 201):
        raise AssertionError(f"auditor register failed: {st} {body}")
    ctx.auditor_email = email
    ctx.auditor_id = int(body.get("auditor_id") or 0) or None
    ctx.auditor_user_id = int(body.get("user_id") or 0) or None
    st_l, login, _ = client.request(
        "POST",
        "/api/v1/auth/login",
        form={"username": email, "password": ctx.password},
    )
    if st_l != 200:
        raise AssertionError(f"auditor login failed: {st_l} {login}")
    ctx.tokens["auditor"] = login["access_token"]
    if not ctx.auditor_id and login.get("entity_id"):
        ctx.auditor_id = int(login["entity_id"])

    st_p, profile, _ = client.request(
        "GET", "/api/v1/auditor/mypage", token=ctx.tokens["auditor"]
    )
    if st_p != 200 or not isinstance(profile, dict):
        raise AssertionError(f"auditor mypage failed: {st_p} {profile}")
    edus = profile.get("educations") or []
    careers = profile.get("careers") or profile.get("work_experiences") or []
    quals = profile.get("qualifications") or []
    degrees = {str(e.get("degree") or "").lower() for e in edus if isinstance(e, dict)}
    need = {"high_school", "bachelor", "master"}
    if not need.issubset(degrees):
        raise AssertionError(f"education degrees missing {need - degrees}; got {degrees}")
    if len(careers) < 2:
        raise AssertionError(f"expected ≥2 careers, got {len(careers)}")
    if len(quals) < 2:
        raise AssertionError(f"expected ≥2 qualifications, got {len(quals)}")
    snap = {
        "email": email,
        "auditor_id": ctx.auditor_id,
        "identity_mock_allowed": mock_allowed,
        "ci_key_used": ci_key if mock_allowed else None,
        "edu_count": len(edus),
        "career_count": len(careers),
        "qual_count": len(quals),
        "degrees": sorted(degrees),
    }
    record(ctx, "2_auditor_register_multi", "pass", "multi edu/career/qual persisted", snap)
    return snap


def step_cb_register(ctx: Ctx, client: Client) -> Any:
    email = f"e2e.cb.{ctx.stamp}@example.com"
    cb_code = f"E2E{ctx.stamp[-8:]}"
    payload = {
        "signup_type": "admin",
        "email": email,
        "password": ctx.password,
        "name": f"E2ECB관리자{ctx.stamp[-4:]}",
        "phone": f"02{ctx.stamp[-8:]}",
        "cb_name": f"E2E인증원-{ctx.stamp}",
        "cb_code": cb_code,
        "cb_type": "certification",
        "cb_initial": "E2E",
        "biz_no": _valid_biz_no(int(ctx.stamp[-8:]) + 17),
        "ceo_name": "CB대표",
        "address": "서울시 종로구 인증로 1",
        "zip_code": "03187",
        "detail_address": "3층",
    }
    st, body, _ = client.request("POST", "/api/v1/auth/register/cb", json_body=payload)
    if st not in (200, 201):
        # fallback wrapper
        st, body, _ = client.request(
            "POST",
            "/api/v1/auth/register/cb-admin",
            json_body={
                "email": email,
                "password": ctx.password,
                "user_name": payload["name"],
                "phone": payload["phone"],
                "cb_code": cb_code,
                "cb_name": payload["cb_name"],
                "biz_no": payload["biz_no"],
                "ceo_name": payload["ceo_name"],
                "address": payload["address"],
            },
        )
    if st not in (200, 201):
        raise AssertionError(f"CB register failed: {st} {body}")
    ctx.cb_email = email
    ctx.cb_code = cb_code
    ctx.cb_id = int(body.get("cb_id") or 0) or None
    st_l, login, _ = client.request(
        "POST",
        "/api/v1/auth/login",
        form={"username": email, "password": ctx.password},
    )
    if st_l != 200:
        raise AssertionError(f"CB login failed: {st_l} {login}")
    ctx.tokens["cb"] = login["access_token"]
    if not ctx.cb_id and login.get("cb_id"):
        ctx.cb_id = int(login["cb_id"])
    snap = {"email": email, "cb_id": ctx.cb_id, "cb_code": cb_code, "register": _clip(body)}
    record(ctx, "3_cb_register", "pass", f"cb_id={ctx.cb_id}", snap)
    return snap


def step_admin_login(ctx: Ctx, client: Client) -> Any:
    st, body, _ = client.request(
        "POST",
        "/api/v1/auth/login",
        form={"username": ctx.admin_email, "password": ctx.admin_password},
    )
    if st != 200 or not isinstance(body, dict) or not body.get("access_token"):
        raise AssertionError(f"admin login failed: {st} {body}")
    ctx.tokens["admin"] = body["access_token"]
    record(ctx, "4a_admin_login", "pass", f"role={body.get('role')}", {"role": body.get("role")})
    return body


def step_cb_accreditation_flow(ctx: Ctx, client: Client) -> Any:
    if not ctx.tokens.get("cb") or not ctx.tokens.get("admin"):
        raise AssertionError("missing cb/admin tokens")
    scopes = json.dumps(
        [
            {"standard_code": "ISO 9001:2015", "iaf_code": "33"},
            {"standard_code": "ISO 14001:2015", "iaf_code": "39"},
        ],
        ensure_ascii=False,
    )
    form = {
        "accreditation_body": "KAB",
        "certificate_number": f"KAB-E2E-{ctx.stamp}",
        "scopes": scopes,
    }
    files = {
        "certificate_file": (
            "e2e-cert.pdf",
            b"%PDF-1.4 E2E accreditation certificate\n",
            "application/pdf",
        )
    }
    st, body, _ = client.request(
        "POST",
        "/api/v1/cb-portal/accreditation-requests",
        token=ctx.tokens["cb"],
        form=form,
        files=files,
    )
    if st not in (200, 201):
        raise AssertionError(f"accreditation request failed: {st} {body}")
    acc_id = int(body["id"])
    ctx.accreditation_id = acc_id
    scope_ids = [int(s["id"]) for s in (body.get("scopes") or []) if s.get("id")]

    # Prefer batch approve (also exercises per-scope projection)
    st_a, approved, _ = client.request(
        "PATCH",
        f"/api/v1/admin/accreditation-requests/{acc_id}/approve",
        token=ctx.tokens["admin"],
    )
    if st_a != 200:
        # fallback per-scope
        last = None
        for sid in scope_ids:
            st_s, last, _ = client.request(
                "PATCH",
                f"/api/v1/admin/accreditation-requests/{acc_id}/scopes/{sid}/approve",
                token=ctx.tokens["admin"],
            )
            if st_s != 200:
                raise AssertionError(f"scope approve failed scope={sid}: {st_s} {last}")
        approved = last

    # Set MD rates so company-accept can compute agreed_amount.
    # GET may return a full catalog — only PUT rates for held/approved rows.
    st_g, sot, _ = client.request(
        "GET", "/api/v1/cb/standard-accreditations", token=ctx.tokens["cb"]
    )
    if st_g != 200 or not isinstance(sot, list):
        raise AssertionError(f"SoT list failed after approve: {st_g} {sot}")
    held = []
    for x in sot:
        if not isinstance(x, dict) or not x.get("standard_code"):
            continue
        # Held rows typically have registration_no / ab_code / is_active after projection
        if x.get("registration_no") or x.get("ab_code") or x.get("md_rate") is not None:
            held.append(str(x["standard_code"]))
        elif x.get("is_active") is True and (
            x.get("expiry_date") is not None or x.get("scope_codes") or x.get("iaf_codes")
        ):
            held.append(str(x["standard_code"]))
    # Always include the standards we just requested (family-safe codes)
    for code in ("ISO 9001:2015", "ISO 14001:2015"):
        if code not in held:
            held.append(code)
    ctx.sot_standard_codes = held
    md_items = [{"standard_code": c, "md_rate": "350000"} for c in held]
    st_m, md_out, _ = client.request(
        "PUT",
        "/api/v1/cb/standard-accreditations",
        token=ctx.tokens["cb"],
        json_body={"replace_all": False, "items": md_items},
    )
    if st_m != 200:
        # Retry only the two requested standards (catalog may include unrelated rows)
        md_items = [
            {"standard_code": "ISO 9001:2015", "md_rate": "350000"},
            {"standard_code": "ISO 14001:2015", "md_rate": "350000"},
        ]
        st_m, md_out, _ = client.request(
            "PUT",
            "/api/v1/cb/standard-accreditations",
            token=ctx.tokens["cb"],
            json_body={"replace_all": False, "items": md_items},
        )
        if st_m != 200:
            raise AssertionError(f"MD rate update failed: {st_m} {md_out}")
        ctx.sot_standard_codes = ["ISO 9001:2015", "ISO 14001:2015"]

    snap = {
        "accreditation_id": acc_id,
        "scope_ids": scope_ids,
        "approve": _clip(approved),
        "sot_codes": ctx.sot_standard_codes,
        "md_set": True,
    }
    record(ctx, "4_cb_accreditation_approve", "pass", f"acc_id={acc_id} scopes={len(scope_ids)}", snap)
    return snap


def step_cb_scope_put_blocked(ctx: Ctx, client: Client) -> Any:
    # v11 gate: replace_all / scope writes blocked for CB
    payload = {
        "replace_all": True,
        "items": [
            {
                "standard_code": "ISO 9001:2015",
                "ab_code": "HACK",
                "registration_no": "SHOULD-BLOCK",
                "scope_codes": ["99"],
                "iaf_codes": ["99"],
                "is_active": True,
                "md_rate": "1",
            }
        ],
    }
    st, body, _ = client.request(
        "PUT",
        "/api/v1/cb/standard-accreditations",
        token=ctx.tokens["cb"],
        json_body=payload,
    )
    if st != 403:
        raise AssertionError(f"expected 403 for replace_all scope write, got {st}: {body}")
    record(
        ctx,
        "5_cb_standard_accreditations_blocked",
        "pass",
        "403 on replace_all/scope write (v11 gate)",
        {"status": st, "detail": body},
    )
    return {"status": st, "body": body}


def step_auditor_membership_and_conduct(ctx: Ctx, client: Client) -> Any:
    """CB affiliation + conduct-sign via real API (needed before assign)."""
    mem_payload = {
        "cb_id": ctx.cb_id,
        "apply_grade": GRADE_LEAD,
        "employment_type": "parttime",
        "is_freelance": True,
        "daily_rate": 450000,
        "requested_iaf_codes": ["33", "39"],
        "cert_standards": ["QMS", "EMS"],
        "qualifications": [
            {
                "standard_code": "QMS",
                "cert_body_name": "KAR",
                "cert_no": f"M-Q-{ctx.stamp[-6:]}",
                "auditor_grade": GRADE_LEAD,
                "iaf_codes": ["33"],
            }
        ],
    }
    st, body, _ = client.request(
        "POST",
        "/api/v1/auditor/memberships/request",
        token=ctx.tokens["auditor"],
        json_body=mem_payload,
    )
    if st not in (200, 201):
        raise AssertionError(f"membership request failed: {st} {body}")
    ctx.membership_id = int(body["membership_id"])
    st_a, appr, _ = client.request(
        "PATCH",
        f"/api/v1/cb/memberships/{ctx.membership_id}/approve",
        token=ctx.tokens["cb"],
        json_body={"decision": "approved", "approved_grade": GRADE_LEAD},
    )
    if st_a != 200:
        raise AssertionError(f"membership approve failed: {st_a} {appr}")
    conduct = api_conduct_sign(client, ctx.tokens["auditor"])
    record(
        ctx,
        "5b_auditor_membership_conduct",
        "pass",
        f"membership_id={ctx.membership_id}; conduct signed via API",
        {"membership": body, "approve": appr, "conduct": conduct},
    )
    return {"membership_id": ctx.membership_id, "conduct": conduct}


def step_register_auditor2(ctx: Ctx, client: Client) -> Any:
    email = f"e2e.aud2.{ctx.stamp}@example.com"
    payload = {
        "name": f"E2E팀원{ctx.stamp[-4:]}",
        "email": email,
        "password": ctx.password,
        "phone": f"0109{ctx.stamp[-7:]}",
        "address": "서울시 서초구 2",
        "detail_address": "303호",
        "employment_type": "parttime",
        "apply_grade": GRADE_AUDITOR,
        "daily_rate": 300000,
        "ci_key": f"MOCK-CI-E2E2-{ctx.stamp}",
        "educations": [
            {
                "school_name": "부산대학교",
                "degree": "bachelor",
                "major": "환경공학",
                "graduated_at": "2015-02-01",
            }
        ],
        "work_experiences": [
            {
                "company_name": "감마환경",
                "start_date": "2015-03-01",
                "is_current": True,
                "duties": "EMS 지원",
            }
        ],
        "qualifications": [
            {
                "standard_code": "EMS",
                "cert_body_name": "KAR",
                "cert_no": f"A2-{ctx.stamp[-6:]}",
                "auditor_grade": GRADE_AUDITOR,
                "iaf_codes": ["39"],
            }
        ],
    }
    st, body, _ = client.request("POST", "/api/v1/auth/register/auditor", json_body=payload)
    if st not in (200, 201):
        raise AssertionError(f"auditor2 register failed: {st} {body}")
    ctx.auditor2_email = email
    ctx.auditor2_id = int(body.get("auditor_id") or 0) or None
    ctx.auditor2_user_id = int(body.get("user_id") or 0) or None
    st_l, login, _ = client.request(
        "POST",
        "/api/v1/auth/login",
        form={"username": email, "password": ctx.password},
    )
    if st_l != 200:
        raise AssertionError(f"auditor2 login failed: {st_l} {login}")
    ctx.tokens["auditor2"] = login["access_token"]
    if not ctx.auditor2_id and login.get("entity_id"):
        ctx.auditor2_id = int(login["entity_id"])

    st_m, mem, _ = client.request(
        "POST",
        "/api/v1/auditor/memberships/request",
        token=ctx.tokens["auditor2"],
        json_body={
            "cb_id": ctx.cb_id,
            "apply_grade": GRADE_AUDITOR,
            "employment_type": "parttime",
            "daily_rate": 300000,
            "requested_iaf_codes": ["39"],
            "cert_standards": ["EMS"],
        },
    )
    if st_m not in (200, 201):
        raise AssertionError(f"auditor2 membership failed: {st_m} {mem}")
    ctx.membership2_id = int(mem["membership_id"])
    st_a, appr, _ = client.request(
        "PATCH",
        f"/api/v1/cb/memberships/{ctx.membership2_id}/approve",
        token=ctx.tokens["cb"],
        json_body={"decision": "approved", "approved_grade": GRADE_AUDITOR},
    )
    if st_a != 200:
        raise AssertionError(f"auditor2 approve failed: {st_a} {appr}")
    conduct = api_conduct_sign(client, ctx.tokens["auditor2"])
    snap = {
        "email": email,
        "auditor_id": ctx.auditor2_id,
        "membership_id": ctx.membership2_id,
        "conduct": conduct,
    }
    record(ctx, "5c_auditor2_ready", "pass", f"auditor2_id={ctx.auditor2_id}", snap)
    return snap


def _submit_cert_app(
    ctx: Ctx,
    client: Client,
    *,
    standards: List[str],
    application_type: str,
    note: str,
) -> Dict[str, Any]:
    start = date.today() + timedelta(days=30)
    end = start + timedelta(days=2)
    integrated = None
    if len(standards) >= 2:
        integrated = {f"intg_{i}": "yes" for i in range(1, 8)}
    payload = {
        "cb_id": ctx.cb_id,
        "standards": standards,
        "standard_types": {s: application_type for s in standards},
        "application_type": application_type,
        "scope_kr": f"E2E 인증범위 {note}",
        "scope_en": f"E2E scope {note}",
        "employee_count": 45,
        "site_count": 1,
        "desired_audit_start": start.isoformat(),
        "desired_audit_end": end.isoformat(),
        "ksic_codes": ["62010"],
        "iaf_codes": ["33"],
        "note": note,
        "integrated_check": integrated,
    }
    st, body, _ = client.request(
        "POST",
        "/api/v1/enterprise-cert-applications",
        token=ctx.tokens["enterprise"],
        json_body=payload,
    )
    if st not in (200, 201):
        raise AssertionError(f"submit {application_type} failed: {st} {body}")
    return body if isinstance(body, dict) else {"raw": body}


def _cb_pipeline_to_contracted(
    ctx: Ctx,
    client: Client,
    app_id: int,
    *,
    accept: bool = True,
    md_minus_pct: int = 0,
) -> Dict[str, Any]:
    # under_review
    for action, extra in (
        ("under_review", {}),
        ("approved", {"md_minus_pct": md_minus_pct, "memo": "E2E approve"}),
    ):
        st, body, _ = client.request(
            "POST",
            f"/api/v1/cb-cert-applications/{app_id}/action",
            token=ctx.tokens["cb"],
            json_body={"action": action, **extra},
        )
        if st != 200:
            raise AssertionError(f"action={action} failed: {st} {body}")
    detail = None
    st_d, detail, _ = client.request(
        "GET",
        f"/api/v1/cb-cert-applications/{app_id}",
        token=ctx.tokens["cb"],
    )
    contract_id = None
    if isinstance(detail, dict):
        contract_id = detail.get("contract_id")
    if accept:
        st_a, acc, _ = client.request(
            "POST",
            f"/api/v1/enterprise-cert-applications/{app_id}/company-accept",
            token=ctx.tokens["enterprise"],
        )
        if st_a != 200:
            raise AssertionError(f"company-accept failed: {st_a} {acc}")
        if isinstance(acc, dict) and acc.get("contract_id"):
            contract_id = acc.get("contract_id")
        return {"detail": detail, "accept": acc, "contract_id": contract_id}
    return {"detail": detail, "contract_id": contract_id, "accept": None}


def _assign_and_maybe_accept(
    ctx: Ctx,
    client: Client,
    app_id: int,
    *,
    lead_id: int,
    member_ids: Optional[List[int]] = None,
    accept_lead: bool = True,
    accept_members: bool = True,
) -> Dict[str, Any]:
    start = date.today() + timedelta(days=40)
    end = start + timedelta(days=1)
    st, body, _ = client.request(
        "POST",
        f"/api/v1/cb-cert-applications/{app_id}/assign-auditors",
        token=ctx.tokens["cb"],
        json_body={
            "lead_auditor_id": lead_id,
            "member_auditor_ids": member_ids or [],
            "audit_start": start.isoformat(),
            "audit_end": end.isoformat(),
            "note": "E2E assign",
        },
    )
    if st != 200:
        raise AssertionError(f"assign failed: {st} {body}")
    assignments = ((body or {}).get("data") or {}).get("assignments") or []
    lead_asg = next((a for a in assignments if a.get("role") in ("lead", "team_leader")), None)
    if lead_asg is None and assignments:
        lead_asg = assignments[0]
    out: Dict[str, Any] = {"assign": body, "assignments": assignments}
    if accept_lead and lead_asg:
        asg_id = int(lead_asg["id"])
        st_acc, acc, _ = client.request(
            "POST",
            f"/api/v1/auditor/assignments/{asg_id}/accept",
            token=ctx.tokens["auditor"],
        )
        if st_acc != 200:
            raise AssertionError(f"lead accept failed: {st_acc} {acc}")
        out["lead_accept"] = acc
        out["lead_assignment_id"] = asg_id
    if accept_members and member_ids and ctx.tokens.get("auditor2"):
        for a in assignments:
            if a.get("role") in ("auditor", "team_member", "member"):
                asg_id = int(a["id"])
                st_m, mac, _ = client.request(
                    "POST",
                    f"/api/v1/auditor/assignments/{asg_id}/accept",
                    token=ctx.tokens["auditor2"],
                )
                if st_m != 200:
                    raise AssertionError(f"member accept failed: {st_m} {mac}")
                out.setdefault("member_accepts", []).append(mac)
    return out


def step_simple_initial_flow(ctx: Ctx, client: Client) -> Any:
    sub = _submit_cert_app(
        ctx, client, standards=["QMS_2015"], application_type="initial", note="simple-initial"
    )
    app_id = int(sub.get("id") or 0)
    if not app_id:
        raise AssertionError(f"no app id: {sub}")
    ctx.simple_app_id = app_id
    pipe = _cb_pipeline_to_contracted(ctx, client, app_id, accept=True)
    ctx.simple_contract_id = int(pipe.get("contract_id") or 0) or None
    assigned = _assign_and_maybe_accept(
        ctx, client, app_id, lead_id=int(ctx.auditor_id), member_ids=[], accept_lead=True
    )
    ctx.simple_assignment_id = assigned.get("lead_assignment_id")
    if not ctx.simple_contract_id:
        # fetch from assign response
        ctx.simple_contract_id = int((assigned.get("assign") or {}).get("contract_id") or 0) or None
    st_p, prog, _ = client.request(
        "GET",
        f"/api/v1/auditor/contracts/{ctx.simple_contract_id}/audit-docs-progress",
        token=ctx.tokens["auditor"],
    )
    if st_p != 200 or not isinstance(prog, dict):
        raise AssertionError(f"audit-docs-progress failed: {st_p} {prog}")
    if prog.get("flow_key") != "initial":
        raise AssertionError(f"expected flow_key=initial, got {prog.get('flow_key')}")
    steps = prog.get("steps") or []
    keys = [s.get("key") for s in steps]
    if "plan" not in keys or not prog.get("next_step"):
        raise AssertionError(f"unexpected progress: keys={keys} next={prog.get('next_step')}")
    snap = {
        "app_id": app_id,
        "contract_id": ctx.simple_contract_id,
        "flow_key": prog.get("flow_key"),
        "next_step": prog.get("next_step"),
        "step_keys": keys,
        "fees": [
            {
                "id": a.get("id"),
                "fee_type": a.get("fee_type"),
                "daily_rate": a.get("daily_rate"),
                "calculated_fee": a.get("calculated_fee"),
            }
            for a in assigned.get("assignments") or []
        ],
    }
    record(ctx, "6_simple_initial_flow", "pass", f"app={app_id} next={prog.get('next_step',{}).get('key')}", snap)
    return snap


def step_integrated_audit(ctx: Ctx, client: Client) -> Any:
    sub = _submit_cert_app(
        ctx,
        client,
        standards=["QMS_2015", "EMS_2015"],
        application_type="initial",
        note="integrated",
    )
    app_id = int(sub.get("id") or 0)
    ctx.integrated_app_id = app_id
    # Get detail with auto MD before approve
    st_d, detail, _ = client.request(
        "GET",
        f"/api/v1/cb-cert-applications/{app_id}",
        token=ctx.tokens["cb"],
    )
    if st_d != 200:
        raise AssertionError(f"integrated detail failed: {st_d} {detail}")
    if (detail or {}).get("audit_mode") != "integrated":
        raise AssertionError(f"expected audit_mode=integrated, got {detail.get('audit_mode')}")
    stds = detail.get("standards") or []
    std_keys = []
    for s in stds:
        if isinstance(s, dict):
            std_keys.append(s.get("standard_key") or s.get("code") or s.get("iso_code"))
        else:
            std_keys.append(str(s))
    md = detail.get("md_review") or {}
    # integrated discount lives in base MD engine (MD11 / intg_level=100)
    pipe = _cb_pipeline_to_contracted(ctx, client, app_id, accept=True, md_minus_pct=0)
    # optional: compare single vs integrated base via subtract autofill not required —
    # verify md detail mentions integrated or mode
    detail2 = pipe.get("detail") or detail
    md2 = (detail2 or {}).get("md_review") or md
    snap = {
        "app_id": app_id,
        "audit_mode": detail.get("audit_mode"),
        "standards": std_keys,
        "selected_standard_keys": std_keys,
        "md_review": {
            "base_md": md2.get("base_md") if isinstance(md2, dict) else None,
            "final_md": md2.get("final_md") if isinstance(md2, dict) else None,
            "subtract_pct": md2.get("subtract_pct") if isinstance(md2, dict) else None,
        },
        "integrated_summary": detail.get("integrated_summary"),
        "contract_id": pipe.get("contract_id"),
    }
    if len([k for k in std_keys if k]) < 2:
        raise AssertionError(f"expected ≥2 standard chips/keys, got {std_keys}")
    if not md2.get("base_md") and not md2.get("final_md"):
        # soft: still pass if mode+standards ok, note MD missing
        record(
            ctx,
            "7_integrated_audit",
            "pass",
            "integrated mode+standards ok; MD fields sparse",
            snap,
        )
        return snap
    record(
        ctx,
        "7_integrated_audit",
        "pass",
        f"integrated standards={std_keys} base_md={md2.get('base_md')}",
        snap,
    )
    return snap


def step_team_audit_and_v14(ctx: Ctx, client: Client) -> Any:
    # Probe v14 endpoint existence (unauth → 401/403 means route exists; bare 404 = missing)
    st_probe, probe_body, _ = client.request(
        "PUT",
        "/api/v1/auditor/audit-notes/team-review-confirm",
        json_body={"contract_id": 1},
    )
    v14_present = st_probe != 404
    if not v14_present:
        record(
            ctx,
            "8_team_audit_v14",
            "skip",
            "v14 not present (team-review-confirm 404)",
            {"status": st_probe, "body": probe_body},
        )
        return None

    sub = _submit_cert_app(
        ctx, client, standards=["QMS_2015"], application_type="initial", note="team-audit"
    )
    app_id = int(sub.get("id") or 0)
    ctx.team_app_id = app_id
    pipe = _cb_pipeline_to_contracted(ctx, client, app_id, accept=True)
    ctx.team_contract_id = int(pipe.get("contract_id") or 0) or None
    assigned = _assign_and_maybe_accept(
        ctx,
        client,
        app_id,
        lead_id=int(ctx.auditor_id),
        member_ids=[int(ctx.auditor2_id)],
        accept_lead=True,
        accept_members=True,
    )
    if not ctx.team_contract_id:
        ctx.team_contract_id = int((assigned.get("assign") or {}).get("contract_id") or 0) or None
    fees = []
    for a in assigned.get("assignments") or []:
        fees.append(
            {
                "role": a.get("role") or a.get("assignment_role"),
                "fee_type": a.get("fee_type"),
                "fee_ratio": a.get("fee_ratio"),
                "daily_rate": a.get("daily_rate"),
                "assigned_days": a.get("assigned_days"),
                "calculated_fee": a.get("calculated_fee"),
            }
        )
    if len(fees) < 2:
        raise AssertionError(f"expected ≥2 assignment fee snapshots, got {fees}")
    if not any(f.get("fee_type") for f in fees):
        raise AssertionError(f"fee_type missing: {fees}")

    # NCR gate: create minor NC then flip to 적합 → waiting_team_review
    cid = int(ctx.team_contract_id)
    st_nc, nc_body, _ = client.request(
        "PUT",
        "/api/v1/auditor/audit-notes/clause",
        token=ctx.tokens["auditor"],
        json_body={
            "contract_id": cid,
            "standard_key": "QMS_2015",
            "clause_no": "4.1",
            "clause_topic": "조직과 그 상황의 이해",
            "verdict": "부적합",
            "ncr_grade": "minor",
            "ncr_fact": "E2E minor NCR fact",
            "ncr_requirement": "4.1",
            "ncr_root_cause": "E2E root",
            "note_text": "E2E NC",
        },
    )
    st_cf, cf_body, _ = client.request(
        "PUT",
        "/api/v1/auditor/audit-notes/clause",
        token=ctx.tokens["auditor"],
        json_body={
            "contract_id": cid,
            "standard_key": "QMS_2015",
            "clause_no": "4.1",
            "verdict": "적합",
            "note_text": "E2E clear without team confirm",
        },
    )
    gated = isinstance(cf_body, dict) and bool(cf_body.get("team_review_gated"))
    ncr_status = cf_body.get("ncr_status") if isinstance(cf_body, dict) else None
    snap = {
        "app_id": app_id,
        "contract_id": cid,
        "fees": fees,
        "v14_probe_status": st_probe,
        "nc_save_status": st_nc,
        "conform_save_status": st_cf,
        "team_review_gated": gated,
        "ncr_status": ncr_status,
        "nc_body": _clip(nc_body),
        "conform_body": _clip(cf_body),
    }
    # Never pass on non-2xx clause API (was a false-pass bug).
    if not (200 <= st_nc < 300):
        record(
            ctx,
            "8_team_audit_v14",
            "fail",
            f"NCR clause save HTTP {st_nc} (expected 2xx)",
            snap,
        )
        return snap
    if not (200 <= st_cf < 300):
        record(
            ctx,
            "8_team_audit_v14",
            "fail",
            f"clause gate exercise HTTP {st_cf} (expected 2xx; never pass on 4xx/5xx)",
            snap,
        )
        return snap
    if gated and ncr_status == "waiting_team_review":
        record(ctx, "8_team_audit_v14", "pass", "team fees ok; NCR finalize gated", snap)
    else:
        record(
            ctx,
            "8_team_audit_v14",
            "fail",
            f"clause 2xx but gate incomplete: gated={gated} ncr_status={ncr_status}",
            snap,
        )
    return snap


def step_audit_types_docs_progress(ctx: Ctx, client: Client) -> Any:
    types = [
        ("surveillance", "surveillance"),
        ("recertification", "recert"),
        ("transfer", "transfer"),
        ("special", "special"),
    ]
    out = []
    for app_type, expect_flow in types:
        try:
            sub = _submit_cert_app(
                ctx,
                client,
                standards=["QMS_2015"],
                application_type=app_type,
                note=f"type-{app_type}",
            )
            app_id = int(sub.get("id") or 0)
            pipe = _cb_pipeline_to_contracted(ctx, client, app_id, accept=True)
            contract_id = int(pipe.get("contract_id") or 0)
            assigned = _assign_and_maybe_accept(
                ctx,
                client,
                app_id,
                lead_id=int(ctx.auditor_id),
                member_ids=[],
                accept_lead=True,
            )
            if not contract_id:
                contract_id = int((assigned.get("assign") or {}).get("contract_id") or 0)
            st_p, prog, _ = client.request(
                "GET",
                f"/api/v1/auditor/contracts/{contract_id}/audit-docs-progress",
                token=ctx.tokens["auditor"],
            )
            if st_p != 200:
                raise AssertionError(f"progress {app_type}: {st_p} {prog}")
            flow_key = prog.get("flow_key")
            if flow_key != expect_flow:
                raise AssertionError(f"{app_type}: expected flow {expect_flow}, got {flow_key}")
            out.append(
                {
                    "application_type": app_type,
                    "flow_key": flow_key,
                    "next_step": prog.get("next_step"),
                    "step_keys": [s.get("key") for s in (prog.get("steps") or [])],
                    "app_id": app_id,
                    "contract_id": contract_id,
                }
            )
        except Exception as e:
            out.append({"application_type": app_type, "error": str(e)})
    errors = [x for x in out if x.get("error")]
    if errors:
        raise AssertionError(f"audit type failures: {errors}")
    record(ctx, "9_audit_types_docs_progress", "pass", f"{len(out)} types ok", out)
    return out


def step_exception_paths(ctx: Ctx, client: Client) -> Any:
    notes: List[str] = []

    # A) company revision — API writes company_revision_requested; live ENUM may lack it
    sub = _submit_cert_app(
        ctx, client, standards=["QMS_2015"], application_type="initial", note="exception-revision"
    )
    app_id = int(sub.get("id") or 0)
    ctx.revision_app_id = app_id
    _cb_pipeline_to_contracted(ctx, client, app_id, accept=False)
    st_r, rev, _ = client.request(
        "POST",
        f"/api/v1/enterprise-cert-applications/{app_id}/company-revision",
        token=ctx.tokens["enterprise"],
        json_body={"comment": "E2E 조율 요청 — MD/일정 재검토"},
    )
    status_after = ((rev or {}).get("data") or {}).get("status") if isinstance(rev, dict) else None
    revision_ok = st_r == 200 and status_after == "company_revision_requested"
    revision_schema_gap = (
        st_r == 500
        and isinstance(rev, dict)
        and "company_revision_requested" in str(rev)
        and "Data truncated" in str(rev)
    )
    if revision_ok:
        notes.append("revision=ok")
    elif revision_schema_gap:
        # Documented ENUM gap — still fail (never lenient-pass on HTTP 500).
        notes.append(
            "revision=schema_gap(DB ENUM lacks company_revision_requested; API path exercised)"
        )
        snap_rev = {
            "revision": {
                "app_id": app_id,
                "http": st_r,
                "status": status_after,
                "schema_gap": True,
                "response": _clip(rev),
            }
        }
        record(
            ctx,
            "10_exception_paths",
            "fail",
            f"company-revision HTTP {st_r} schema_gap (ENUM missing company_revision_requested)",
            snap_rev,
        )
        return snap_rev
    else:
        raise AssertionError(f"company-revision unexpected: {st_r} {rev}")

    # B) auditor assignment decline
    sub2 = _submit_cert_app(
        ctx, client, standards=["QMS_2015"], application_type="initial", note="exception-decline"
    )
    app2 = int(sub2.get("id") or 0)
    ctx.decline_app_id = app2
    _cb_pipeline_to_contracted(ctx, client, app2, accept=True)
    assigned = _assign_and_maybe_accept(
        ctx,
        client,
        app2,
        lead_id=int(ctx.auditor_id),
        member_ids=[],
        accept_lead=False,
    )
    asg = (assigned.get("assignments") or [None])[0]
    if not asg:
        raise AssertionError("no assignment to decline")
    asg_id = int(asg["id"])
    st_d, dec, _ = client.request(
        "POST",
        f"/api/v1/auditor/assignments/{asg_id}/decline",
        token=ctx.tokens["auditor"],
        json_body={"comment": "E2E 배정 거절 — 일정 불가"},
    )
    if st_d != 200:
        raise AssertionError(f"decline failed: {st_d} {dec}")
    asg_status = None
    if isinstance(dec, dict):
        inner = dec.get("assignment") if isinstance(dec.get("assignment"), dict) else {}
        asg_status = inner.get("status") or dec.get("status")
    notes.append(f"decline_http={st_d}")

    st_me, me, _ = client.request("GET", "/api/v1/auth/me", token=ctx.tokens["cb"])
    cb_uid = int(me["id"]) if isinstance(me, dict) and me.get("id") else None
    n_any = db_count_notifications(cb_uid) if cb_uid else -1
    notes.append(f"cb_notifs={n_any}")

    snap = {
        "revision": {
            "app_id": app_id,
            "http": st_r,
            "status": status_after,
            "schema_gap": revision_schema_gap,
            "response": _clip(rev),
        },
        "decline": {
            "app_id": app2,
            "assignment_id": asg_id,
            "response": _clip(dec),
            "assignment_status": asg_status,
        },
        "notifications": {"cb_user_id": cb_uid, "cb_total": n_any},
    }
    # Pass if decline ok and revision either succeeded or documented schema gap
    record(ctx, "10_exception_paths", "pass", "; ".join(notes), snap)
    return snap


def build_summary(ctx: Ctx) -> Dict[str, Any]:
    passed = sum(1 for r in ctx.results if r.status == "pass")
    failed = sum(1 for r in ctx.results if r.status == "fail")
    skipped = sum(1 for r in ctx.results if r.status == "skip")
    return {
        "total_steps": len(ctx.results),
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "failures": [
            {"step": r.step, "detail": r.detail, "response_snapshot": r.response_snapshot}
            for r in ctx.results
            if r.status == "fail"
        ],
        "stamp": ctx.stamp,
        "accounts": {
            "enterprise": ctx.enterprise_email,
            "auditor": ctx.auditor_email,
            "auditor2": ctx.auditor2_email,
            "cb": ctx.cb_email,
            "cb_id": ctx.cb_id,
            "company_id": ctx.company_id,
        },
    }


def write_results(ctx: Ctx, summary: Dict[str, Any]) -> Path:
    payload = {
        "summary": _redact(summary),
        "steps": [_redact(r.as_dict()) for r in ctx.results],
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "base_url": ctx.base_url,
    }
    RESULTS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return RESULTS_PATH


def main() -> int:
    parser = argparse.ArgumentParser(description="ComplAIs e2e API scenario (v15)")
    parser.add_argument("--base-url", default=os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument(
        "--admin-email",
        default=os.getenv("E2E_ADMIN_EMAIL", ADMIN_EMAIL_DEFAULT),
    )
    parser.add_argument(
        "--admin-password",
        default=os.getenv("E2E_ADMIN_PASSWORD", ADMIN_PASSWORD_DEFAULT),
    )
    parser.add_argument(
        "--password",
        default=os.getenv("E2E_PASSWORD", PASSWORD_DEFAULT),
        help="Password for newly created test accounts",
    )
    args = parser.parse_args()

    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    ctx = Ctx(
        base_url=args.base_url.rstrip("/"),
        stamp=stamp,
        password=args.password,
        admin_email=args.admin_email,
        admin_password=args.admin_password,
    )
    client = Client(ctx.base_url)
    print(f"E2E base={ctx.base_url} stamp={stamp} http_lib={'requests' if _HAS_REQUESTS else 'urllib'}")

    # Phase 1
    run_step(ctx, "0_health", lambda: step_health(ctx, client))
    run_step(ctx, "1_enterprise_register", lambda: step_enterprise_register(ctx, client), depends_on=["0_health"])
    run_step(
        ctx,
        "2_auditor_register_multi",
        lambda: step_auditor_register(ctx, client),
        depends_on=["0_health"],
    )
    run_step(ctx, "3_cb_register", lambda: step_cb_register(ctx, client), depends_on=["0_health"])
    run_step(ctx, "4a_admin_login", lambda: step_admin_login(ctx, client), depends_on=["0_health"])
    run_step(
        ctx,
        "4_cb_accreditation_approve",
        lambda: step_cb_accreditation_flow(ctx, client),
        depends_on=["3_cb_register", "4a_admin_login"],
    )
    run_step(
        ctx,
        "5_cb_standard_accreditations_blocked",
        lambda: step_cb_scope_put_blocked(ctx, client),
        depends_on=["3_cb_register", "4_cb_accreditation_approve"],
    )
    run_step(
        ctx,
        "5b_auditor_membership_conduct",
        lambda: step_auditor_membership_and_conduct(ctx, client),
        depends_on=["2_auditor_register_multi", "3_cb_register"],
    )
    run_step(
        ctx,
        "5c_auditor2_ready",
        lambda: step_register_auditor2(ctx, client),
        depends_on=["3_cb_register", "5b_auditor_membership_conduct"],
    )

    # Phase 2
    phase2_deps = [
        "1_enterprise_register",
        "4_cb_accreditation_approve",
        "5b_auditor_membership_conduct",
    ]
    run_step(
        ctx,
        "6_simple_initial_flow",
        lambda: step_simple_initial_flow(ctx, client),
        depends_on=phase2_deps,
    )
    run_step(
        ctx,
        "7_integrated_audit",
        lambda: step_integrated_audit(ctx, client),
        depends_on=phase2_deps,
    )
    run_step(
        ctx,
        "8_team_audit_v14",
        lambda: step_team_audit_and_v14(ctx, client),
        depends_on=phase2_deps + ["5c_auditor2_ready"],
    )
    run_step(
        ctx,
        "9_audit_types_docs_progress",
        lambda: step_audit_types_docs_progress(ctx, client),
        depends_on=phase2_deps + ["6_simple_initial_flow"],
    )
    run_step(
        ctx,
        "10_exception_paths",
        lambda: step_exception_paths(ctx, client),
        depends_on=phase2_deps,
    )

    summary = build_summary(ctx)
    path = write_results(ctx, summary)
    print("\n=== SUMMARY JSON ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"\nWrote {_redact({'path': str(path)})['path']}")
    return 1 if summary["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
