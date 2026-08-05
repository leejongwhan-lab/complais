"""ESG master KPI catalog API — enterprise + admin read endpoints."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.v1.endpoints.audit_request import _collect_company_cert_badges
from app.api.v1.endpoints.user_common import require_enterprise_user, resolve_company_id
from app.core.security import CurrentUser, get_current_admin_user, get_current_user
from app.models.company import Companies
from app.models.esg import (
    CompanyEsgAuditNote,
    CompanyEsgKpiGoal,
    CompanyEsgKpiValue,
    EsgMasterKpi,
)
from app.schemas.esg_master_kpi import (
    CompanyEsgAuditNoteOut,
    CompanyEsgAuditNoteUpsert,
    CompanyEsgKpiGoalOut,
    CompanyEsgKpiGoalUpsert,
    CompanyEsgKpiValueOut,
    CompanyEsgKpiValueUpsert,
    EsgKpiTrendOut,
    EsgMasterKpiListResponse,
    EsgMasterKpiMetaResponse,
    EsgMasterKpiOut,
    EsgMasterKpiPortalListResponse,
    EsgMasterKpiPortalOut,
)

# Shared ISO number tokens used for fuzzy held↔catalog matching
_ISO_NUM_RE = re.compile(
    r"(9001|14001|45001|27001|27701|50001|37001|37301|22301|22000|13485|42001|19443)",
    re.IGNORECASE,
)

# 산업 특화 세부카테고리 — 필수(공통 외부) 배지 제외
_INDUSTRY_SUBS = {
    "금융",
    "건설",
    "물류",
    "리테일",
    "식품",
    "반도체",
    "화학",
    "헬스케어",
    "IT",
    "공공",
    "확장지표",
}

user_router = APIRouter(prefix="/user", tags=["User ESG Master KPIs"])
admin_router = APIRouter(prefix="/admin", tags=["Admin ESG Master KPIs"])


def _iso_nums(text: str) -> Set[str]:
    return {m.group(1) for m in _ISO_NUM_RE.finditer(text or "")}


def _held_match_clause(held_labels: List[str]):
    """OR of LIKE predicates: managed_standard_name fuzzy-matches any held ISO label."""
    clauses = []
    seen_nums: Set[str] = set()
    for label in held_labels:
        nums = _iso_nums(label)
        if nums:
            for num in nums:
                if num in seen_nums:
                    continue
                seen_nums.add(num)
                clauses.append(EsgMasterKpi.managed_standard_name.ilike(f"%{num}%"))
        else:
            token = (label or "").strip()
            if len(token) >= 2:
                clauses.append(EsgMasterKpi.managed_standard_name.ilike(f"%{token}%"))
    return clauses


def _distinct_standards(db: Session) -> List[str]:
    rows = (
        db.query(EsgMasterKpi.managed_standard_name)
        .distinct()
        .order_by(EsgMasterKpi.managed_standard_name.asc())
        .all()
    )
    return [r[0] for r in rows if r[0]]


def _year_window(now: Optional[datetime] = None) -> Tuple[List[int], int]:
    current = (now or datetime.utcnow()).year
    years = list(range(current - 4, current + 1))
    return years, current


def classify_input_mode(kpi: EsgMasterKpi) -> str:
    """공공 / 심사 / 기업 직접입력 분류.

    A 자동수집형 → public
    B 심사추출형 → auditor
    C 혼합형 + 공공API → public, 아니면 company
    D 기업작성형 → company (공공API 플래그가 있어도 기업 입력)
    """
    code = (kpi.source_type_code or "").strip().upper()[:1]
    api = bool(kpi.is_public_api_available)
    if code == "A":
        return "public"
    if code == "B":
        return "auditor"
    if code == "C":
        return "public" if api else "company"
    if code == "D":
        return "company"
    if api:
        return "public"
    method = kpi.extraction_detail_method or ""
    if "심사" in method:
        return "auditor"
    if "기업" in method:
        return "company"
    return "company"


def data_path_label(kpi: EsgMasterKpi, mode: str) -> Optional[str]:
    """데이터 경로 pill 라벨 — criteria_mapping 첫 토큰 우선."""
    raw = (kpi.criteria_mapping or "").strip()
    if raw:
        token = re.split(r"[;/|]", raw)[0].strip()
        # 너무 긴 ISO 조항 나열은 축약
        if len(token) > 28:
            token = token[:28].rstrip() + "…"
        if token:
            return token
    if mode == "public":
        return "공공API"
    return None


def is_required_kpi(kpi: EsgMasterKpi, mode: str) -> bool:
    """기업 공통 외부 지표 ≈ 필수 배지."""
    if (kpi.sub_category or "") in _INDUSTRY_SUBS:
        return False
    if mode == "public":
        return True
    code = (kpi.source_type_code or "").strip().upper()[:1]
    return code == "A"


def kpi_display_code(kpi: EsgMasterKpi) -> str:
    return f"KPI-{kpi.esg_category}-{int(kpi.kpi_id):03d}"


def _parse_numeric(raw: Optional[str]) -> Optional[float]:
    if raw is None:
        return None
    text = str(raw).strip().replace(",", "").replace("%", "")
    if not text or text == "-":
        return None
    try:
        return float(text)
    except ValueError:
        return None


def compute_trend(year_values: Dict[str, Optional[str]], years: List[int]) -> Optional[EsgKpiTrendOut]:
    nums: List[Tuple[int, float]] = []
    for y in years:
        n = _parse_numeric(year_values.get(str(y)))
        if n is not None:
            nums.append((y, n))
    if len(nums) < 2:
        return None
    (_, a), (_, b) = nums[-2], nums[-1]
    if a == 0:
        return EsgKpiTrendOut(pct=None, direction="flat")
    pct = round(abs((b - a) / a) * 100, 1)
    if b < a:
        direction = "down"
    elif b > a:
        direction = "up"
    else:
        direction = "flat"
    return EsgKpiTrendOut(pct=pct, direction=direction)


def _query_base(
    db: Session,
    *,
    esg_category: Optional[str],
    managed_standard_name: Optional[str],
    q: Optional[str],
    held_labels: Optional[List[str]],
    held_only: bool,
    source_mode: Optional[str] = None,
):
    query = db.query(EsgMasterKpi)

    if esg_category:
        cat = esg_category.strip().upper()
        if cat not in ("E", "S", "G"):
            raise HTTPException(status_code=400, detail="esg_category는 E, S, G 중 하나여야 합니다.")
        query = query.filter(EsgMasterKpi.esg_category == cat)

    if managed_standard_name and managed_standard_name.strip():
        token = managed_standard_name.strip()
        query = query.filter(EsgMasterKpi.managed_standard_name.ilike(f"%{token}%"))

    if q and q.strip():
        like = f"%{q.strip()}%"
        query = query.filter(
            or_(
                EsgMasterKpi.kpi_name.ilike(like),
                EsgMasterKpi.sub_category.ilike(like),
                EsgMasterKpi.description.ilike(like),
                EsgMasterKpi.iso_clause_detail.ilike(like),
                EsgMasterKpi.extraction_detail_method.ilike(like),
                EsgMasterKpi.criteria_mapping.ilike(like),
            )
        )

    matched_to_held = False
    if held_only:
        if not held_labels:
            return None, 0, False
        match_clauses = _held_match_clause(held_labels)
        if not match_clauses:
            return None, 0, False
        query = query.filter(or_(*match_clauses))
        matched_to_held = True

    # source_mode filter applied in Python after classify (small catalog) OR via SQL heuristics
    if source_mode:
        mode = source_mode.strip().lower()
        if mode == "public":
            query = query.filter(
                or_(
                    EsgMasterKpi.source_type_code.ilike("A%"),
                    and_(
                        EsgMasterKpi.source_type_code.ilike("C%"),
                        EsgMasterKpi.is_public_api_available.is_(True),
                    ),
                )
            )
        elif mode == "auditor":
            query = query.filter(EsgMasterKpi.source_type_code.ilike("B%"))
        elif mode == "company":
            query = query.filter(
                or_(
                    EsgMasterKpi.source_type_code.ilike("D%"),
                    and_(
                        EsgMasterKpi.source_type_code.ilike("C%"),
                        or_(
                            EsgMasterKpi.is_public_api_available.is_(False),
                            EsgMasterKpi.is_public_api_available.is_(None),
                        ),
                    ),
                )
            )

    total = query.with_entities(func.count(EsgMasterKpi.kpi_id)).scalar() or 0
    return query, int(total), matched_to_held


def _query_kpis(
    db: Session,
    *,
    esg_category: Optional[str],
    managed_standard_name: Optional[str],
    q: Optional[str],
    held_labels: Optional[List[str]],
    held_only: bool,
    skip: int,
    limit: int,
) -> EsgMasterKpiListResponse:
    query, total, matched_to_held = _query_base(
        db,
        esg_category=esg_category,
        managed_standard_name=managed_standard_name,
        q=q,
        held_labels=held_labels,
        held_only=held_only,
    )
    years, current_year = _year_window()
    if query is None:
        return EsgMasterKpiListResponse(
            total=0,
            skip=skip,
            limit=limit,
            data=[],
            held_standards=held_labels or [],
            available_standards=_distinct_standards(db),
            matched_to_held=False,
            years=years,
            current_year=current_year,
        )

    rows = (
        query.order_by(
            EsgMasterKpi.esg_category.asc(),
            EsgMasterKpi.kpi_id.asc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )

    return EsgMasterKpiListResponse(
        total=total,
        skip=skip,
        limit=limit,
        data=[EsgMasterKpiOut.model_validate(r) for r in rows],
        held_standards=held_labels or [],
        available_standards=_distinct_standards(db),
        matched_to_held=matched_to_held,
        years=years,
        current_year=current_year,
    )


def _enrich_portal_rows(
    db: Session,
    rows: List[EsgMasterKpi],
    company_id: Optional[int],
) -> List[EsgMasterKpiPortalOut]:
    years, current_year = _year_window()
    values_by_kpi: Dict[int, Dict[int, str]] = {}
    goals_by_kpi: Dict[int, CompanyEsgKpiGoal] = {}
    notes_by_kpi: Dict[int, CompanyEsgAuditNote] = {}

    if company_id and rows:
        kpi_ids = [r.kpi_id for r in rows]
        for v in (
            db.query(CompanyEsgKpiValue)
            .filter(
                CompanyEsgKpiValue.company_id == company_id,
                CompanyEsgKpiValue.kpi_id.in_(kpi_ids),
                CompanyEsgKpiValue.year.in_(years),
            )
            .all()
        ):
            values_by_kpi.setdefault(v.kpi_id, {})[v.year] = v.value

        for g in (
            db.query(CompanyEsgKpiGoal)
            .filter(
                CompanyEsgKpiGoal.company_id == company_id,
                CompanyEsgKpiGoal.kpi_id.in_(kpi_ids),
            )
            .order_by(CompanyEsgKpiGoal.target_year.desc())
            .all()
        ):
            if g.kpi_id not in goals_by_kpi:
                goals_by_kpi[g.kpi_id] = g

        for n in (
            db.query(CompanyEsgAuditNote)
            .filter(
                CompanyEsgAuditNote.company_id == company_id,
                CompanyEsgAuditNote.kpi_id.in_(kpi_ids),
            )
            .all()
        ):
            notes_by_kpi[n.kpi_id] = n

    out: List[EsgMasterKpiPortalOut] = []
    for r in rows:
        mode = classify_input_mode(r)
        ymap = values_by_kpi.get(r.kpi_id, {})
        year_values = {str(y): ymap.get(y) for y in years}
        goal = goals_by_kpi.get(r.kpi_id)
        note = notes_by_kpi.get(r.kpi_id)
        preview = None
        if note and note.note:
            preview = note.note[:120] + ("…" if len(note.note) > 120 else "")
        base = EsgMasterKpiOut.model_validate(r)
        out.append(
            EsgMasterKpiPortalOut(
                **base.model_dump(),
                kpi_code=kpi_display_code(r),
                input_mode=mode,
                data_path_label=data_path_label(r, mode),
                is_required=is_required_kpi(r, mode),
                years=years,
                year_values=year_values,
                trend=compute_trend(year_values, years),
                goal_value=goal.target_value if goal else None,
                goal_year=goal.target_year if goal else None,
                has_audit_note=bool(note),
                audit_note_preview=preview,
                can_company_input=(mode == "company"),
                can_set_goal=True,
                current_year=current_year,
            )
        )
    return out


def _query_portal_kpis(
    db: Session,
    *,
    company_id: Optional[int],
    esg_category: Optional[str],
    managed_standard_name: Optional[str],
    q: Optional[str],
    held_labels: Optional[List[str]],
    held_only: bool,
    source_mode: Optional[str],
    skip: int,
    limit: int,
) -> EsgMasterKpiPortalListResponse:
    years, current_year = _year_window()
    query, total, matched_to_held = _query_base(
        db,
        esg_category=esg_category,
        managed_standard_name=managed_standard_name,
        q=q,
        held_labels=held_labels,
        held_only=held_only,
        source_mode=source_mode,
    )
    if query is None:
        return EsgMasterKpiPortalListResponse(
            total=0,
            skip=skip,
            limit=limit,
            data=[],
            held_standards=held_labels or [],
            available_standards=_distinct_standards(db),
            matched_to_held=False,
            years=years,
            current_year=current_year,
        )

    rows = (
        query.order_by(
            EsgMasterKpi.esg_category.asc(),
            EsgMasterKpi.kpi_id.asc(),
        )
        .offset(skip)
        .limit(limit)
        .all()
    )
    return EsgMasterKpiPortalListResponse(
        total=total,
        skip=skip,
        limit=limit,
        data=_enrich_portal_rows(db, rows, company_id),
        held_standards=held_labels or [],
        available_standards=_distinct_standards(db),
        matched_to_held=matched_to_held,
        years=years,
        current_year=current_year,
    )


def _resolve_held(
    db: Session,
    current_user: CurrentUser,
    company_id: Optional[int],
    held_only: bool,
) -> Tuple[List[str], Optional[int]]:
    held: List[str] = []
    cid: Optional[int] = None
    if held_only or current_user.role in ("client_admin", "client_staff", "platform_admin"):
        try:
            cid = resolve_company_id(current_user, company_id)
            company = db.get(Companies, cid)
            if company:
                held, _other = _collect_company_cert_badges(db, company)
        except HTTPException:
            if held_only:
                raise
            cid = None
            held = []
    return held, cid


@user_router.get("/esg-master-kpis", response_model=EsgMasterKpiPortalListResponse)
def list_user_esg_master_kpis(
    esg_category: Optional[str] = Query(None, description="E | S | G"),
    managed_standard_name: Optional[str] = Query(None, description="관리 표준명 부분일치"),
    q: Optional[str] = Query(None, description="KPI명·세부카테고리·설명 검색"),
    held_only: bool = Query(
        False,
        description="true면 기업 보유 표준에 매칭되는 KPI만 (managed_standard_name 퍼지)",
    ),
    source_mode: Optional[str] = Query(
        None, description="public | auditor | company — 데이터 입력 경로 필터"
    ),
    company_id: Optional[int] = Query(None, description="platform_admin 전용"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """기업 포털 — ESG 마스터 KPI + 연도값/목표/심사노트."""
    require_enterprise_user(current_user)
    held, cid = _resolve_held(db, current_user, company_id, held_only)
    return _query_portal_kpis(
        db,
        company_id=cid,
        esg_category=esg_category,
        managed_standard_name=managed_standard_name,
        q=q,
        held_labels=held,
        held_only=held_only,
        source_mode=source_mode,
        skip=skip,
        limit=limit,
    )


@user_router.get("/esg-master-kpis/meta", response_model=EsgMasterKpiMetaResponse)
def user_esg_master_kpis_meta(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """카테고리별 건수 · distinct 표준 목록."""
    require_enterprise_user(current_user)
    total = db.query(func.count(EsgMasterKpi.kpi_id)).scalar() or 0
    by_cat = {
        row[0]: int(row[1])
        for row in db.query(EsgMasterKpi.esg_category, func.count(EsgMasterKpi.kpi_id))
        .group_by(EsgMasterKpi.esg_category)
        .all()
    }
    return EsgMasterKpiMetaResponse(
        total=int(total),
        by_category=by_cat,
        available_standards=_distinct_standards(db),
    )


@user_router.put("/esg-kpi-goals", response_model=CompanyEsgKpiGoalOut)
def upsert_esg_kpi_goal(
    body: CompanyEsgKpiGoalUpsert,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """목표설정 — 기업 포털에서 KPI 목표값 저장."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, body.company_id)
    kpi = db.get(EsgMasterKpi, body.kpi_id)
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI를 찾을 수 없습니다.")
    now = datetime.utcnow()
    row = (
        db.query(CompanyEsgKpiGoal)
        .filter(
            CompanyEsgKpiGoal.company_id == cid,
            CompanyEsgKpiGoal.kpi_id == body.kpi_id,
            CompanyEsgKpiGoal.target_year == body.target_year,
        )
        .first()
    )
    if row:
        row.target_value = body.target_value.strip()
        row.unit = body.unit or kpi.unit_format
        row.updated_at = now
    else:
        row = CompanyEsgKpiGoal(
            company_id=cid,
            kpi_id=body.kpi_id,
            target_year=body.target_year,
            target_value=body.target_value.strip(),
            unit=body.unit or kpi.unit_format,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return CompanyEsgKpiGoalOut.model_validate(row)


@user_router.put("/esg-kpi-values", response_model=CompanyEsgKpiValueOut)
def upsert_esg_kpi_value(
    body: CompanyEsgKpiValueUpsert,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """기업 직접입력 — 당해년도만 허용 (input_mode=company)."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, body.company_id)
    kpi = db.get(EsgMasterKpi, body.kpi_id)
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI를 찾을 수 없습니다.")
    mode = classify_input_mode(kpi)
    if mode != "company":
        raise HTTPException(
            status_code=400,
            detail="이 KPI는 기업 직접입력이 아닙니다. 공공연동 또는 심사노트 경로를 사용하세요.",
        )
    _, current_year = _year_window()
    if body.year != current_year:
        raise HTTPException(
            status_code=400,
            detail=f"기업 직접입력은 당해년도({current_year})만 가능합니다.",
        )
    now = datetime.utcnow()
    row = (
        db.query(CompanyEsgKpiValue)
        .filter(
            CompanyEsgKpiValue.company_id == cid,
            CompanyEsgKpiValue.kpi_id == body.kpi_id,
            CompanyEsgKpiValue.year == body.year,
        )
        .first()
    )
    if row:
        row.value = body.value.strip()
        row.source_mode = "company"
        row.updated_at = now
    else:
        row = CompanyEsgKpiValue(
            company_id=cid,
            kpi_id=body.kpi_id,
            year=body.year,
            value=body.value.strip(),
            source_mode="company",
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return CompanyEsgKpiValueOut.model_validate(row)


@user_router.get("/esg-kpi-audit-notes/{kpi_id}", response_model=CompanyEsgAuditNoteOut)
def get_esg_audit_note(
    kpi_id: int,
    company_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """심사노트 조회."""
    require_enterprise_user(current_user)
    cid = resolve_company_id(current_user, company_id)
    row = (
        db.query(CompanyEsgAuditNote)
        .filter(
            CompanyEsgAuditNote.company_id == cid,
            CompanyEsgAuditNote.kpi_id == kpi_id,
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="등록된 심사노트가 없습니다.")
    return CompanyEsgAuditNoteOut.model_validate(row)


@user_router.put("/esg-kpi-audit-notes", response_model=CompanyEsgAuditNoteOut)
def upsert_esg_audit_note(
    body: CompanyEsgAuditNoteUpsert,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """심사노트 저장 — 심사원/플랫폼어드민 작성. 기업 계정은 열람만.

    스텁: platform_admin 및 향후 심사원 역할이 작성. 기업(client_*)은 403.
    연도 실측값은 source_mode=auditor 로 values에 별도 반영 가능.
    """
    require_enterprise_user(current_user)
    if current_user.role in ("client_admin", "client_staff"):
        raise HTTPException(
            status_code=403,
            detail="심사노트는 심사원이 작성합니다. 열람만 가능합니다.",
        )
    cid = resolve_company_id(current_user, body.company_id)
    kpi = db.get(EsgMasterKpi, body.kpi_id)
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI를 찾을 수 없습니다.")
    now = datetime.utcnow()
    row = (
        db.query(CompanyEsgAuditNote)
        .filter(
            CompanyEsgAuditNote.company_id == cid,
            CompanyEsgAuditNote.kpi_id == body.kpi_id,
        )
        .first()
    )
    if row:
        row.note = body.note.strip()
        row.auditor_user_id = current_user.id
        row.updated_at = now
    else:
        row = CompanyEsgAuditNote(
            company_id=cid,
            kpi_id=body.kpi_id,
            note=body.note.strip(),
            auditor_user_id=current_user.id,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return CompanyEsgAuditNoteOut.model_validate(row)


@admin_router.get("/esg-master-kpis", response_model=EsgMasterKpiListResponse)
def list_admin_esg_master_kpis(
    esg_category: Optional[str] = Query(None, description="E | S | G"),
    managed_standard_name: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    _: CurrentUser = Depends(get_current_admin_user),
):
    """플랫폼 어드민 — ESG 마스터 KPI 카탈로그 조회."""
    return _query_kpis(
        db,
        esg_category=esg_category,
        managed_standard_name=managed_standard_name,
        q=q,
        held_labels=[],
        held_only=False,
        skip=skip,
        limit=limit,
    )
