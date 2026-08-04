"""기업 인증심사 신청서(CertApplication) 및 계약서(CertContract).

주의 (충돌 해소):
- `Contract` 클래스명은 이미 app/models/contract.py에서 사용 중이며(테이블 audit_contracts,
  AuditApplication/AuditAssignment/AuditNote/AuditNCR와 back_populates로 연결됨) 동일 이름을
  다시 선언하면 SQLAlchemy 선언적 레지스트리에서 클래스명 충돌(Multiple classes found for
  path "Contract")이 발생한다. 따라서 `CertContract`로 명명한다.
- `__tablename__ = "contracts"` 역시 레거시 `Contracts`(app/models/contract.py, 실제 운영
  스키마 컬럼 보유)와 충돌하므로 `cert_contracts`로 분리한다.
- `Application` 자체는 이름 충돌이 없지만, 기존 `AuditApplication`(심사원의 IAF 자격 신청)과
  혼동을 피하기 위해 대칭적으로 `CertApplication`(기업의 인증심사 신청)으로 명명하고
  테이블도 `cert_applications`로 분리한다.
- `cert_bodies`는 존재하지 않는 테이블명이며, 실제 라이브 테이블은 `certification_bodies`이므로
  FK를 정정하고, `certification_bodies.id`가 MySQL에서 INT UNSIGNED이므로 타입도 맞춘다.
- `AuditAssignment.contract`는 이미 기존 `Contract`(audit_contracts)와 1:1 back_populates로
  고정되어 있으므로, 이 새 `CertContract`에는 별도의 assignments 관계를 두지 않는다.
"""
import enum

from sqlalchemy import Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import relationship

from app.core.database import Base


class ContractStatus(str, enum.Enum):
    DRAFT = "draft"          # 작성 중
    PENDING = "pending"      # 승인 대기
    SIGNED = "signed"        # 계약 체결 완료
    CANCELLED = "cancelled"  # 해지/취소


class CertApplication(Base):
    """인증 신청서"""
    __tablename__ = "cert_applications"

    id = Column(Integer, primary_key=True, index=True)
    cb_id = Column(MySQLInteger(unsigned=True), ForeignKey("certification_bodies.id"), nullable=False, index=True)  # CB 멀티테넌시
    company_name = Column(String(150), nullable=False)                                # 피심사 기업명
    business_no = Column(String(20), index=True)                                      # 사업자등록번호
    applicant_name = Column(String(50), nullable=False)                               # 신청인
    total_employees = Column(Integer, default=0)                                      # 상시 근로자 수
    created_at = Column(DateTime, server_default=func.now())

    contracts = relationship("CertContract", back_populates="application")


class CertContract(Base):
    """인증 심사 계약서"""
    __tablename__ = "cert_contracts"

    id = Column(Integer, primary_key=True, index=True)
    cb_id = Column(MySQLInteger(unsigned=True), ForeignKey("certification_bodies.id"), nullable=False, index=True)  # CB 멀티테넌시
    application_id = Column(Integer, ForeignKey("cert_applications.id"), nullable=False)
    contract_no = Column(String(50), unique=True, nullable=False, index=True)        # 계약번호 (예: CNT-2026-0801)

    # 계약 세부 정보
    audit_type = Column(String(30), nullable=False)                                    # 최초, 사후, 갱신 등
    total_md = Column(Numeric(5, 2), nullable=False)                                   # 산정된 총 MD
    total_amount = Column(Numeric(12, 0), default=0)                                   # 계약 금액
    contract_date = Column(Date, nullable=False)                                       # 계약 체결일
    # SQLAlchemy Enum()은 기본적으로 멤버의 .name(예: 'DRAFT')을 DB 값으로 사용하므로,
    # 마이그레이션에서 생성한 소문자 MySQL enum('draft','pending',...)과 맞추기 위해
    # values_callable로 .value(예: 'draft')를 사용하도록 명시한다.
    status = Column(
        Enum(ContractStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=ContractStatus.DRAFT,
        nullable=False,
    )

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    application = relationship("CertApplication", back_populates="contracts")
