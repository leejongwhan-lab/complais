"""심사노트(AuditNote) 및 부적합관리(AuditNCR) 모델.

`Contract`(audit_contracts, master_data/AuditApplication 기반 신규 정규화 계약)와
`StandardClause`(standard_clause_masters, 신규 조항 마스터)를 FK로 참조한다.
레거시 `Contracts`(contracts 테이블) / `StandardClauses`(standard_clauses 테이블, 체크리스트형)와는
별개의 신규 정규화 체인이다.
"""
import enum

from sqlalchemy import BigInteger, Column, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.mysql import INTEGER as MySQLInteger
from sqlalchemy.orm import relationship

from app.core.database import Base


class NCRGrade(str, enum.Enum):
    MAJOR = "major"   # 중부적합
    MINOR = "minor"   # 경부적합
    OBS = "obs"       # 권고사항(Observation)


class AuditNote(Base):
    """심사노트: 계약(Contract) + 표준조항(Clause) 단위 현장 관찰 기록.

    주의: 레거시 `AuditNotes`(app/models/audit.py, 테이블 audit_notes)와 이름이 겹치지만
    contract/clause를 느슨한 정수/문자열로 참조하는 별개의(더 상세한 워크플로우) 스키마이므로,
    `auditor_career_records` 등과 동일한 규칙에 따라 테이블명을 `audit_note_records`로 분리한다.
    """
    __tablename__ = "audit_note_records"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(BigInteger, ForeignKey("audit_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = Column(Integer, ForeignKey("standard_clause_masters.id"), nullable=False, index=True)
    # auditors.id는 MySQL에서 INT UNSIGNED이므로 FK 타입을 정확히 맞춘다.
    auditor_id = Column(MySQLInteger(unsigned=True), ForeignKey("auditors.id"), nullable=False)

    audit_findings = Column(Text, nullable=False)  # 심사 발견사항 및 확인 기록
    compliance_status = Column(String(20), default="conform", nullable=False)  # conform(적합), nc(부적합), obs(권고)
    created_at = Column(DateTime, server_default=func.now())

    contract = relationship("Contract", back_populates="notes")
    clause = relationship("StandardClause", back_populates="notes")
    auditor = relationship("Auditor", back_populates="audit_notes")


class AuditNCR(Base):
    """부적합 관리: 부적합 조항 매핑 및 시정조치(CA) 추적.

    주의: 레거시 `AuditNcrs`(app/models/audit.py, 테이블 audit_ncrs)와 이름이 겹치지만
    별개의(더 상세한 워크플로우) 스키마이므로 테이블명을 `audit_ncr_records`로 분리한다.
    """
    __tablename__ = "audit_ncr_records"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(BigInteger, ForeignKey("audit_contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    clause_id = Column(Integer, ForeignKey("standard_clause_masters.id"), nullable=False, index=True)
    auditor_id = Column(MySQLInteger(unsigned=True), ForeignKey("auditors.id"), nullable=False)

    grade = Column(Enum(NCRGrade), nullable=False)                 # major / minor / obs
    nc_description = Column(Text, nullable=False)                  # 부적합 내용 (요구사항 대비 미흡 사항)
    corrective_action = Column(Text, nullable=True)                # 피심사 기업이 제출한 시정조치 내용
    root_cause = Column(Text, nullable=True)                       # 근본 원인 분석
    status = Column(String(30), default="issued", nullable=False)  # issued, ca_submitted, ca_accepted, closed

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    contract = relationship("Contract", back_populates="ncrs")
    clause = relationship("StandardClause", back_populates="ncrs")
    auditor = relationship("Auditor", back_populates="audit_ncrs")
