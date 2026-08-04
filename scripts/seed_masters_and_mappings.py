# scripts/seed_masters_and_mappings.py
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.models.master_data import KsicCode, IafCode, Major, KsicIafMapping, MajorIafMapping

def seed_master_and_mappings():
    db = SessionLocal()
    try:
        print("🌱 1. 마스터 테이블 시드 데이터 주입 중...")

        # 1-1. IAF 코드 마스터
        iaf_list = [
            {"code": "13", "name_ko": "의약용 물질 및 의약품"},
            {"code": "18", "name_ko": "기계 및 장비"},
            {"code": "19", "name_ko": "전기 및 광학기기"},
            {"code": "23", "name_ko": "기타 제조업"},
            {"code": "33", "name_ko": "정보기술업"},
        ]
        iaf_map = {}
        for item in iaf_list:
            obj = db.query(IafCode).filter_by(code=item["code"]).first()
            if not obj:
                obj = IafCode(**item)
                db.add(obj)
                db.flush()
            iaf_map[item["code"]] = obj.id

        # 1-2. KSIC 코드 마스터
        ksic_list = [
            {"code": "2110", "name_ko": "의약용 물질 제조업", "digit_level": 4},
            {"code": "2911", "name_ko": "내경기관 제조업", "digit_level": 4},
            {"code": "2611", "name_ko": "반도체 소자 제조업", "digit_level": 4},
            {"code": "6201", "name_ko": "컴퓨터 프로그래밍 서비스업", "digit_level": 4},
            {"code": "620", "name_ko": "컴퓨터 프로그래밍, 시스템 통합 및 관리업", "digit_level": 3},
        ]
        ksic_map = {}
        for item in ksic_list:
            obj = db.query(KsicCode).filter_by(code=item["code"]).first()
            if not obj:
                obj = KsicCode(**item)
                db.add(obj)
                db.flush()
            ksic_map[item["code"]] = obj.id

        # 1-3. Major(전공) 마스터
        major_list = [
            {"name": "약학", "category": "의약계열"},
            {"name": "기계공학", "category": "이공계열"},
            {"name": "전기공학", "category": "이공계열"},
            {"name": "컴퓨터공학", "category": "이공계열"},
            {"name": "산업디자인학", "category": "예체능/공학계열"},
        ]
        major_map = {}
        for item in major_list:
            obj = db.query(Major).filter_by(name=item["name"]).first()
            if not obj:
                obj = Major(**item)
                db.add(obj)
                db.flush()
            major_map[item["name"]] = obj.id

        print("🌱 2. 매핑 테이블 데이터 주입 중...")

        # 2-1. KSIC ↔ IAF 매핑
        ksic_mappings = [
            {"ksic_code": "2110", "iaf_code": "13", "qms_complexity": "높음", "ems_complexity": "높음", "ohsms_complexity": "높음"},
            {"ksic_code": "2911", "iaf_code": "18", "qms_complexity": "중간", "ems_complexity": "중간", "ohsms_complexity": "중간"},
            {"ksic_code": "2611", "iaf_code": "19", "qms_complexity": "중간", "ems_complexity": "중간", "ohsms_complexity": "중간"},
            {"ksic_code": "6201", "iaf_code": "33", "qms_complexity": "중간", "ems_complexity": "제한", "ohsms_complexity": "낮음"},
            {"ksic_code": "620",  "iaf_code": "33", "qms_complexity": "중간", "ems_complexity": "제한", "ohsms_complexity": "낮음"},
        ]
        for m in ksic_mappings:
            k_id = ksic_map[m["ksic_code"]]
            i_id = iaf_map[m["iaf_code"]]
            exists = db.query(KsicIafMapping).filter_by(ksic_id=k_id, iaf_id=i_id).first()
            if not exists:
                db.add(KsicIafMapping(
                    ksic_id=k_id, iaf_id=i_id,
                    qms_complexity=m["qms_complexity"],
                    ems_complexity=m["ems_complexity"],
                    ohsms_complexity=m["ohsms_complexity"]
                ))

        # 2-2. 전공 ↔ IAF 매핑 및 단서조항
        major_mappings = [
            {"major_name": "약학", "iaf_code": "13", "extra_exp_years": 3, "requires_committee": False, "notes": "부속서 2 단서조항: 관련 실무경력 3년 추가 필요"},
            {"major_name": "기계공학", "iaf_code": "18", "extra_exp_years": 0, "requires_committee": False, "notes": "일반 지정"},
            {"major_name": "전기공학", "iaf_code": "19", "extra_exp_years": 0, "requires_committee": False, "notes": "일반 지정"},
            {"major_name": "컴퓨터공학", "iaf_code": "33", "extra_exp_years": 0, "requires_committee": False, "notes": "일반 지정"},
            {"major_name": "산업디자인학", "iaf_code": "23", "extra_exp_years": 0, "requires_committee": True, "notes": "부속서 2 단서조항: 자격인증위원회 심의 필요"},
        ]
        for m in major_mappings:
            m_id = major_map[m["major_name"]]
            i_id = iaf_map[m["iaf_code"]]
            exists = db.query(MajorIafMapping).filter_by(major_id=m_id, iaf_id=i_id).first()
            if not exists:
                db.add(MajorIafMapping(
                    major_id=m_id, iaf_id=i_id,
                    extra_exp_years=m["extra_exp_years"],
                    requires_committee=m["requires_committee"],
                    notes=m["notes"]
                ))

        db.commit()
        print("✅ 마스터/매핑 정규화 시드 주입 완수!")
    except Exception as e:
        db.rollback()
        print(f"❌ 오류 발생: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_master_and_mappings()
