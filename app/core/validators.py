"""공통 입력 유효성 — 사업자번호 / 전화 / 이메일 / URL.

사업자등록번호는 항상 `000-00-00000` (3-2-5) 형식으로 정규화한다.
"""
from __future__ import annotations

import re
from typing import Optional

from fastapi import HTTPException

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
_URL_RE = re.compile(r"^(https?://)?([A-Za-z0-9\-]+\.)+[A-Za-z]{2,}(/.*)?$", re.IGNORECASE)
_BIZ_WEIGHTS = (1, 3, 7, 1, 3, 7, 1, 3, 7)


def digits_only(value: Optional[str]) -> str:
    return "".join(ch for ch in str(value or "") if ch.isdigit())


def format_biz_no(value: Optional[str]) -> Optional[str]:
    """숫자만 추출 후 `000-00-00000`로 포맷. 빈 값은 None."""
    d = digits_only(value)
    if not d:
        return None
    if len(d) > 10:
        d = d[:10]
    if len(d) != 10:
        # 부분 입력은 하이픈만 맞춰 반환(저장 전 검증에서 거부)
        if len(d) <= 3:
            return d
        if len(d) <= 5:
            return f"{d[:3]}-{d[3:]}"
        return f"{d[:3]}-{d[3:5]}-{d[5:]}"
    return f"{d[:3]}-{d[3:5]}-{d[5:]}"


def is_valid_biz_no_checksum(digits10: str) -> bool:
    """국세청 사업자등록번호 체크섬."""
    if len(digits10) != 10 or not digits10.isdigit():
        return False
    nums = [int(c) for c in digits10]
    total = sum(n * w for n, w in zip(nums[:9], _BIZ_WEIGHTS))
    # 8번째(0-based index 7) 자리의 가중치 결과에 대해 추가 보정
    mid = nums[7] * 3
    total += mid // 10
    check = (10 - (total % 10)) % 10
    return check == nums[9]


def normalize_biz_no(value: Optional[str], *, required: bool = False) -> Optional[str]:
    """검증 + `000-00-00000` 정규화. 실패 시 HTTP 400."""
    raw = (value or "").strip()
    if not raw:
        if required:
            raise HTTPException(status_code=400, detail="사업자번호는 필수입니다.")
        return None
    d = digits_only(raw)
    if len(d) != 10:
        raise HTTPException(
            status_code=400,
            detail="사업자번호는 10자리 숫자여야 합니다. (형식: 000-00-00000)",
        )
    if not is_valid_biz_no_checksum(d):
        raise HTTPException(
            status_code=400,
            detail="유효하지 않은 사업자번호입니다. 확인 후 다시 입력하세요.",
        )
    return f"{d[:3]}-{d[3:5]}-{d[5:]}"


def format_phone(value: Optional[str]) -> Optional[str]:
    """한국 전화번호를 하이픈 형식으로 정규화."""
    d = digits_only(value)
    if not d:
        return None
    if d.startswith("02"):
        rest = d[2:]
        if len(rest) <= 3:
            return f"02-{rest}" if rest else "02"
        if len(rest) <= 6:
            return f"02-{rest[:3]}-{rest[3:]}"
        return f"02-{rest[:4]}-{rest[4:8]}" if len(rest) >= 8 else f"02-{rest[:3]}-{rest[3:]}"
    if d.startswith(("010", "011", "016", "017", "018", "019")):
        if len(d) <= 3:
            return d
        if len(d) <= 7:
            return f"{d[:3]}-{d[3:]}"
        return f"{d[:3]}-{d[3:7]}-{d[7:11]}"
    # 지역번호 0XX
    if d.startswith("0") and len(d) >= 9:
        if len(d) == 10:
            return f"{d[:3]}-{d[3:6]}-{d[6:]}"
        if len(d) >= 11:
            return f"{d[:3]}-{d[3:7]}-{d[7:11]}"
    if len(d) <= 4:
        return d
    if len(d) <= 8:
        return f"{d[:4]}-{d[4:]}"
    return f"{d[:4]}-{d[4:8]}-{d[8:]}"


def normalize_phone(value: Optional[str], *, required: bool = False) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        if required:
            raise HTTPException(status_code=400, detail="전화번호는 필수입니다.")
        return None
    d = digits_only(raw)
    if not (9 <= len(d) <= 11):
        raise HTTPException(
            status_code=400,
            detail="전화번호는 9~11자리 숫자여야 합니다. (예: 02-1234-5678, 010-1234-5678)",
        )
    if not d.startswith("0"):
        raise HTTPException(status_code=400, detail="전화번호는 0으로 시작해야 합니다.")
    # 휴대폰
    if d.startswith(("010", "011", "016", "017", "018", "019")):
        if len(d) != 10 and len(d) != 11:
            raise HTTPException(status_code=400, detail="휴대폰 번호 형식이 올바르지 않습니다.")
        return format_phone(d)
    # 서울 02
    if d.startswith("02"):
        if len(d) not in (9, 10):
            raise HTTPException(status_code=400, detail="서울(02) 전화번호 형식이 올바르지 않습니다.")
        return format_phone(d)
    # 기타 지역 0XX
    if len(d) not in (10, 11):
        raise HTTPException(status_code=400, detail="전화번호 형식이 올바르지 않습니다.")
    return format_phone(d)


def normalize_email(value: Optional[str], *, required: bool = False) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        if required:
            raise HTTPException(status_code=400, detail="이메일은 필수입니다.")
        return None
    email = raw.lower()
    if len(email) > 200 or not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="이메일 형식이 올바르지 않습니다.")
    return email


def normalize_website(value: Optional[str]) -> Optional[str]:
    raw = (value or "").strip()
    if not raw:
        return None
    if not _URL_RE.match(raw):
        raise HTTPException(
            status_code=400,
            detail="웹사이트 URL 형식이 올바르지 않습니다. (예: https://example.com)",
        )
    return raw


def sanitize_contact_fields(
    *,
    biz_no: Optional[str] = None,
    biz_reg_no: Optional[str] = None,
    tel: Optional[str] = None,
    phone: Optional[str] = None,
    email: Optional[str] = None,
    tax_email: Optional[str] = None,
    website: Optional[str] = None,
    require_biz: bool = False,
    require_email: bool = False,
    require_phone: bool = False,
) -> dict:
    """여러 연락처 필드를 한 번에 정규화. 키는 전달된 것만 반환."""
    out: dict = {}
    if biz_no is not None or require_biz:
        out["biz_no"] = normalize_biz_no(biz_no, required=require_biz)
    if biz_reg_no is not None:
        out["biz_reg_no"] = normalize_biz_no(biz_reg_no, required=False)
    if tel is not None:
        out["tel"] = normalize_phone(tel, required=False)
    if phone is not None:
        out["phone"] = normalize_phone(phone, required=require_phone)
    if email is not None or require_email:
        out["email"] = normalize_email(email, required=require_email)
    if tax_email is not None:
        out["tax_email"] = normalize_email(tax_email, required=False)
    if website is not None:
        out["website"] = normalize_website(website)
    return out
