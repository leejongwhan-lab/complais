"""인증기관(CB) 통합 모델 헬퍼 + 인정범위 행렬.

기존 운영 테이블 `certification_bodies`(app.models.cb.CertificationBodies)를 유지하고,
명세 필드명(cb_code, cb_name, biz_reg_no …)은 헬퍼로 매핑한다.

인정범위는 1행 = 1개 표준 + 1개 수행범위 코드 테이블 `cb_scope_matrix`.
IAF 01–39는 9001/14001/45001만; 그 외는 MDQMS/FSMS/NQMS/BCMS 코드(컬럼 iaf_code에 저장).
"""
from datetime import date, datetime
from typing import Any, Optional

from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.models.cb import CertificationBodies


# 명세 호환 별칭 (import 편의)
CertificationBody = CertificationBodies


class CbAccreditationScope(Base):
    """CB × ISO 표준 × 수행범위 코드 (1:1:1).

    iaf_code 컬럼은 범용 scope_code 저장소:
    - iaf39: 01–39
    - mdqms/fsms/nqms/bcms: 각 택소노미 코드
    """

    __tablename__ = "cb_scope_matrix"
    __table_args__ = (
        UniqueConstraint("cb_id", "standard_code", "iaf_code", name="uk_cb_scope_matrix"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("certification_bodies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    standard_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="ISO 9001 등")
    iaf_code: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="수행범위 코드(IAF 01~39 또는 표준별 코드)"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    granted_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class CbStandardAccreditation(Base):
    """CB × ISO 표준별 인정기관(AB) + 인정번호 + 인정만료일 + MD단가.

    Scope 행렬과 독립 DB 관리.
    MD 단가 조회 fallback:
      1) cb_standard_accreditations.md_rate (표준별, source of truth when set)
      2) cb_contracts.price_per_md (CB-level, backward compat)
      3) 0
    """

    __tablename__ = "cb_standard_accreditations"
    __table_args__ = (
        UniqueConstraint("cb_id", "standard_code", name="uq_cb_standard_acc"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    cb_id: Mapped[int] = mapped_column(
        MySQLInteger(unsigned=True),
        ForeignKey("certification_bodies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    standard_code: Mapped[str] = mapped_column(String(50), nullable=False, comment="ISO 9001:2015 등")
    ab_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True, comment="인정기관 이니셜")
    registration_no: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, comment="표준별 인정번호")
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, comment="표준별 인정만료일")
    md_rate: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 0), nullable=True, comment="표준별 MD 단가(KRW)"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


def normalize_cb_status(status: Optional[str], is_active: bool = True) -> str:
    if status in {"active", "suspended", "inactive"}:
        return status  # type: ignore[return-value]
    if status in {"정상", "운영"}:
        return "active"
    if status in {"정지", "중단"}:
        return "suspended"
    if status in {"취소", "폐업"}:
        return "inactive"
    return "active" if is_active else "inactive"


def cb_to_spec_dict(cb: CertificationBodies) -> dict[str, Any]:
    return {
        "id": cb.id,
        "cb_code": cb.code,
        "cb_name": cb.name,
        "cb_name_en": cb.name_en,
        "cb_initial": cb.cb_initial,
        "reg_no": cb.reg_no or cb.accreditation_no,
        "accreditation_body": cb.accreditation_body or cb.accreditation or "KAB",
        "biz_reg_no": cb.biz_no,
        "ceo_name": cb.ceo_name,
        "address": cb.address,
        "tel": cb.tel or cb.phone,
        "email": cb.email,
        "website": cb.website,
        "logo_path": cb.logo_path or cb.stamp_url,
        "status": normalize_cb_status(cb.status, bool(cb.is_active)),
        "created_at": cb.created_at,
        "updated_at": cb.updated_at,
    }


def apply_spec_fields(cb: CertificationBodies, data: dict) -> None:
    """명세 필드명을 기존 certification_bodies 컬럼에 반영."""
    if "cb_code" in data and data["cb_code"] is not None:
        cb.code = str(data["cb_code"]).strip()
    if "cb_name" in data and data["cb_name"] is not None:
        cb.name = str(data["cb_name"]).strip()
    if "cb_name_en" in data:
        cb.name_en = data["cb_name_en"]
    if "cb_initial" in data:
        cb.cb_initial = data["cb_initial"]
    if "reg_no" in data:
        cb.reg_no = data["reg_no"]
        cb.accreditation_no = data["reg_no"]
    if "accreditation_body" in data:
        cb.accreditation_body = data["accreditation_body"]
        cb.accreditation = data["accreditation_body"]
    if "biz_reg_no" in data:
        cb.biz_no = data["biz_reg_no"]
    if "ceo_name" in data:
        cb.ceo_name = data["ceo_name"]
    if "address" in data:
        cb.address = data["address"]
    if "tel" in data:
        cb.tel = data["tel"]
        cb.phone = data["tel"]
    if "email" in data:
        cb.email = data["email"]
    if "website" in data:
        cb.website = data["website"]
    if "logo_path" in data:
        cb.logo_path = data["logo_path"]
        cb.stamp_url = data["logo_path"]
    if "fax" in data:
        cb.fax = data["fax"]
    if "tax_email" in data:
        cb.tax_email = data["tax_email"]
    if "corp_no" in data:
        cb.corp_no = data["corp_no"]
    if "personal_no" in data:
        cb.personal_no = data["personal_no"]
    if "bank_name" in data:
        cb.bank_name = data["bank_name"]
    if "account_no" in data:
        cb.account_no = data["account_no"]
    if "account_holder" in data:
        cb.account_holder = data["account_holder"]
    if "intro" in data:
        cb.intro = data["intro"]
    if "expire_date" in data:
        cb.expire_date = data["expire_date"]
    if "accreditation_region" in data:
        cb.accreditation_region = data["accreditation_region"]
    if "accreditation_country" in data:
        cb.accreditation_country = data["accreditation_country"]
    if "status" in data and data["status"] is not None:
        st = str(data["status"]).strip().lower()
        if st in {"active", "정상"}:
            cb.status = "정상"
            cb.is_active = True
        elif st in {"suspended", "정지"}:
            cb.status = "정지"
            cb.is_active = False
        elif st in {"inactive", "취소"}:
            cb.status = "취소"
            cb.is_active = False
        else:
            cb.status = str(data["status"])


class ScopeCodeMaster(Base):
    """표준군별 인증수행범위 코드 마스터 (IAF / MDQMS / FSMS / NQMS / BCMS)."""

    __tablename__ = "scope_code_masters"
    __table_args__ = (
        UniqueConstraint("taxonomy", "code", name="uq_scope_code_masters_tax_code"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    taxonomy: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    code: Mapped[str] = mapped_column(String(30), nullable=False)
    name_ko: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    name_en: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    parent_code: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    group_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    meta_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

