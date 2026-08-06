# scripts/seed_mappings.py
import os
import sys

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.master_data import IafCode, KsicCode, Major, KsicIafMapping, MajorIafMapping


def _get_or_create_ksic(db, code: str, name_ko: str) -> KsicCode:
    obj = db.query(KsicCode).filter_by(code=code).first()
    if not obj:
        obj = KsicCode(code=code, name_ko=name_ko or code, digit_level=len(code))
        db.add(obj)
        db.flush()
    return obj


def _get_or_create_iaf(db, code: str, name_ko: str) -> IafCode:
    obj = db.query(IafCode).filter_by(code=code).first()
    if not obj:
        obj = IafCode(code=code, name_ko=name_ko or code)
        db.add(obj)
        db.flush()
    return obj


def _get_or_create_major(db, name: str) -> Major:
    obj = db.query(Major).filter_by(name=name).first()
    if not obj:
        obj = Major(name=name)
        db.add(obj)
        db.flush()
    return obj


def seed_ksic_iaf_mappings(db):
    print("🌱 seeding ksic_iaf_mappings...")

    # 부속서 1 & IAF ID1 복잡도 기준 샘플/핵심 데이터 세트
    ksic_data = [
        # 19 전기 및 광학기기
        {"ksic_code": "2611", "ksic_name": "반도체 소자 제조업", "iaf_code": "19B", "iaf_name_ko": "전기 및 광학기기", "qms_complexity": "중간", "ems_complexity": "중간", "ohsms_complexity": "중간"},
        {"ksic_code": "2621", "ksic_name": "전자축전지 제조업", "iaf_code": "19B", "iaf_name_ko": "전기 및 광학기기", "qms_complexity": "중간", "ems_complexity": "중간", "ohsms_complexity": "중간"},
        {"ksic_code": "2631", "ksic_name": "통신장비 제조업", "iaf_code": "19A", "iaf_name_ko": "전기 및 광학기기", "qms_complexity": "중간", "ems_complexity": "중간", "ohsms_complexity": "중간"},
        # 18 기계 및 장비
        {"ksic_code": "2911", "ksic_name": "내경기관 제조업", "iaf_code": "18A", "iaf_name_ko": "기계 및 장비", "qms_complexity": "중간", "ems_complexity": "중간", "ohsms_complexity": "중간"},
        {"ksic_code": "2921", "ksic_name": "농업용 기계 제조업", "iaf_code": "18A", "iaf_name_ko": "기계 및 장비", "qms_complexity": "중간", "ems_complexity": "중간", "ohsms_complexity": "중간"},
        # 13 의약품 (고위험/높음)
        {"ksic_code": "2110", "ksic_name": "의약용 물질 제조업", "iaf_code": "13A", "iaf_name_ko": "의약용 물질 및 의약품", "qms_complexity": "높음", "ems_complexity": "높음", "ohsms_complexity": "높음"},
        {"ksic_code": "2121", "ksic_name": "완제 의약품 제조업", "iaf_code": "13A", "iaf_name_ko": "의약용 물질 및 의약품", "qms_complexity": "높음", "ems_complexity": "높음", "ohsms_complexity": "높음"},
        # 33 정보기술업
        {"ksic_code": "6201", "ksic_name": "컴퓨터 프로그래밍 서비스업", "iaf_code": "33B", "iaf_name_ko": "정보기술업", "qms_complexity": "중간", "ems_complexity": "제한", "ohsms_complexity": "낮음"},
        {"ksic_code": "6202", "ksic_name": "컴퓨터 시스템 통합 자문 및 구축 서비스업", "iaf_code": "33B", "iaf_name_ko": "정보기술업", "qms_complexity": "중간", "ems_complexity": "제한", "ohsms_complexity": "낮음"},
        {"ksic_code": "620", "ksic_name": "컴퓨터 프로그래밍, 시스템 통합 및 관리업", "iaf_code": "33B", "iaf_name_ko": "정보기술업", "qms_complexity": "중간", "ems_complexity": "제한", "ohsms_complexity": "낮음"},
    ]

    for row in ksic_data:
        ksic_obj = _get_or_create_ksic(db, row["ksic_code"], row["ksic_name"])
        iaf_obj = _get_or_create_iaf(db, row["iaf_code"], row["iaf_name_ko"])

        exists = (
            db.query(KsicIafMapping)
            .filter_by(ksic_id=ksic_obj.id, iaf_id=iaf_obj.id)
            .first()
        )
        if not exists:
            db.add(
                KsicIafMapping(
                    ksic_id=ksic_obj.id,
                    iaf_id=iaf_obj.id,
                    qms_complexity=row["qms_complexity"],
                    ems_complexity=row["ems_complexity"],
                    ohsms_complexity=row["ohsms_complexity"],
                )
            )
    db.commit()


def seed_major_iaf_mappings(db):
    print("🌱 seeding major_iaf_mappings...")

    # 부속서 2 전공학과별 인정 코드 및 단서조항 데이터 세트
    major_data = [
        # 일반 이공계
        {"major_name": "기계공학", "iaf_code": "18", "degree_level": "BACHELOR_4Y", "is_mandatory": True, "extra_exp_years": 0, "requires_committee": False, "notes": "기계 및 장비 제조업 관련 인정"},
        {"major_name": "전기공학", "iaf_code": "19", "degree_level": "BACHELOR_4Y", "is_mandatory": True, "extra_exp_years": 0, "requires_committee": False, "notes": "전기 및 광학기기 제조업 관련 인정"},
        {"major_name": "전자공학", "iaf_code": "19", "degree_level": "BACHELOR_4Y", "is_mandatory": True, "extra_exp_years": 0, "requires_committee": False, "notes": "전기 및 광학기기 제조업 관련 인정"},
        {"major_name": "컴퓨터공학", "iaf_code": "33", "degree_level": "BACHELOR_4Y", "is_mandatory": True, "extra_exp_years": 0, "requires_committee": False, "notes": "정보기술업 관련 인정"},
        # 단서조항 적용 항목 (의약 13, 원자력 11, 의료기기 193 -> 실무경력 3년 추가 필수)
        {"major_name": "약학", "iaf_code": "13", "degree_level": "BACHELOR_4Y", "is_mandatory": False, "extra_exp_years": 3, "requires_committee": False, "notes": "부속서 2 단서조항: 전공만으로 부여 불가, 해당 분야 실무경력 3년 추가 제출 필수"},
        {"major_name": "제약학", "iaf_code": "13", "degree_level": "BACHELOR_4Y", "is_mandatory": False, "extra_exp_years": 3, "requires_committee": False, "notes": "부속서 2 단서조항: 전공만으로 부여 불가, 해당 분야 실무경력 3년 추가 제출 필수"},
        {"major_name": "원자력공학", "iaf_code": "11", "degree_level": "BACHELOR_4Y", "is_mandatory": False, "extra_exp_years": 3, "requires_committee": False, "notes": "부속서 2 단서조항: 전공만으로 부여 불가, 해당 분야 실무경력 3년 추가 제출 필수"},
        # 자격인증위원회 심의 필요 항목 (기타 제조업 23번)
        {"major_name": "산업디자인학", "iaf_code": "23", "degree_level": "BACHELOR_4Y", "is_mandatory": False, "extra_exp_years": 0, "requires_committee": True, "notes": "부속서 2 단서조항: 업종별 특성이 상이하므로 KAR 자격인증위원회 심의로 결정"},
        # 인문사회계
        {"major_name": "경영학", "iaf_code": "29", "degree_level": "BACHELOR_4Y", "is_mandatory": True, "extra_exp_years": 0, "requires_committee": False, "notes": "도소매업 관련 인정"},
        {"major_name": "경영학", "iaf_code": "32", "degree_level": "BACHELOR_4Y", "is_mandatory": True, "extra_exp_years": 0, "requires_committee": False, "notes": "금융, 보험, 부동산 및 임대업 관련 인정"},
    ]

    for row in major_data:
        major_obj = _get_or_create_major(db, row["major_name"])
        iaf_obj = _get_or_create_iaf(db, row["iaf_code"], row["iaf_code"])

        exists = (
            db.query(MajorIafMapping)
            .filter_by(major_id=major_obj.id, iaf_id=iaf_obj.id)
            .first()
        )
        if not exists:
            db.add(
                MajorIafMapping(
                    major_id=major_obj.id,
                    iaf_id=iaf_obj.id,
                    degree_level=row["degree_level"],
                    is_mandatory=row["is_mandatory"],
                    extra_exp_years=row["extra_exp_years"],
                    requires_committee=row["requires_committee"],
                    notes=row["notes"],
                )
            )
    db.commit()


def run_seed():
    db = SessionLocal()
    try:
        seed_ksic_iaf_mappings(db)
        seed_major_iaf_mappings(db)
        print("✅ 시드 데이터 주입 완수!")
    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
