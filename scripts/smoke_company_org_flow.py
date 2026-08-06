#!/usr/bin/env python3
"""기업정보 org 플로우 스모크 테스트 — company / sites / depts / staff / headcount yearly.

Usage (from repo root):
  .venv/bin/python scripts/smoke_company_org_flow.py
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.backoffice import CompanyStaff
from app.models.company import (
    Companies,
    CompanyDepartments,
    CompanyHeadcountYearly,
    CompanySites,
)


def main() -> int:
    db: Session = SessionLocal()
    stamp = datetime.now().strftime("%H%M%S")
    marker = f"SMOKE-ORG-{stamp}"
    year = datetime.now().year
    company = None
    try:
        now = datetime.now()
        company = Companies(
            name=f"{marker} 테스트기업",
            name_en=f"{marker} Co",
            biz_no=f"999-99-{stamp[-5:]}",
            ceo_name="스모크테스터",
            entity_type="법인",
            address="서울시 테스트구 1",
            detail_address="101호",
            address_en="1 Test-gu, Seoul",
            tel="02-0000-0000",
            email=f"smoke-{stamp}@example.com",
            employee_count=10,
            headcount_regular=8,
            headcount_non_regular=2,
            headcount_outsourced=1,
            scope_kr="소프트웨어 개발",
            scope_en="Software development",
            ksic_code="62010",
            iaf_code="33",
            is_active=True,
            status="정상",
            created_at=now,
            updated_at=now,
        )
        db.add(company)
        db.flush()

        site = CompanySites(
            company_id=company.id,
            site_name=f"{marker}-공장",
            address="경기 테스트시",
            detail_address="2층",
            address_en="Test City",
            employee_count=5,
            is_main=False,
            work_type="생산",
            created_at=now,
            updated_at=now,
        )
        db.add(site)

        dept = CompanyDepartments(
            company_id=company.id,
            name="품질경영팀",
            sort_order=0,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        db.add(dept)

        staff = CompanyStaff(
            company_id=company.id,
            staff_name="김담당",
            role="인증담당",
            department="품질경영팀",
            position="과장",
            phone="02-111-2222",
            mobile="010-1111-2222",
            email=f"staff-{stamp}@example.com",
        )
        db.add(staff)

        hc = CompanyHeadcountYearly(
            company_id=company.id,
            year=year,
            employee_count=12,
            headcount_regular=9,
            headcount_non_regular=3,
            headcount_outsourced=1,
            created_at=now,
            updated_at=now,
        )
        db.add(hc)
        db.commit()

        # re-read asserts
        cid = company.id
        c2 = db.get(Companies, cid)
        assert c2 is not None and c2.name.startswith(marker)
        assert c2.ceo_name == "스모크테스터"

        sites = db.query(CompanySites).filter(CompanySites.company_id == cid).all()
        assert len(sites) == 1
        assert sites[0].detail_address == "2층"
        assert sites[0].address_en == "Test City"

        depts = (
            db.query(CompanyDepartments)
            .filter(CompanyDepartments.company_id == cid, CompanyDepartments.is_active.is_(True))
            .all()
        )
        assert len(depts) == 1 and depts[0].name == "품질경영팀"

        staffs = db.query(CompanyStaff).filter(CompanyStaff.company_id == cid).all()
        assert len(staffs) == 1
        assert staffs[0].role == "인증담당"
        assert staffs[0].phone == "02-111-2222"

        # update company + yearly overwrite
        c2.tel = "02-9999-8888"
        c2.employee_count = 15
        snap = (
            db.query(CompanyHeadcountYearly)
            .filter(CompanyHeadcountYearly.company_id == cid, CompanyHeadcountYearly.year == year)
            .one()
        )
        snap.employee_count = 15
        snap.headcount_regular = 11
        snap.updated_at = datetime.now()
        c2.updated_at = datetime.now()
        db.commit()

        c3 = db.get(Companies, cid)
        assert c3.tel == "02-9999-8888"
        assert c3.employee_count == 15
        snap2 = (
            db.query(CompanyHeadcountYearly)
            .filter(CompanyHeadcountYearly.company_id == cid, CompanyHeadcountYearly.year == year)
            .one()
        )
        assert snap2.employee_count == 15
        assert snap2.headcount_regular == 11

        print("OK company_org_flow")
        print(f"  company_id={cid}")
        print(f"  site_id={sites[0].id}")
        print(f"  dept_id={depts[0].id}")
        print(f"  staff_id={staffs[0].id}")
        print(f"  headcount_year={year} employee_count={snap2.employee_count}")
        return 0
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    finally:
        # cleanup smoke rows
        try:
            if company and company.id:
                cid = company.id
                db.query(CompanyHeadcountYearly).filter(CompanyHeadcountYearly.company_id == cid).delete()
                db.query(CompanyStaff).filter(CompanyStaff.company_id == cid).delete()
                db.query(CompanyDepartments).filter(CompanyDepartments.company_id == cid).delete()
                db.query(CompanySites).filter(CompanySites.company_id == cid).delete()
                db.query(Companies).filter(Companies.id == cid).delete()
                db.commit()
                print("  cleaned up smoke rows")
        except Exception as cleanup_exc:  # noqa: BLE001
            db.rollback()
            print(f"  cleanup warning: {cleanup_exc}", file=sys.stderr)
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
