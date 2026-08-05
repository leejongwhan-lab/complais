"""Pydantic DTO schemas — auto-generated from 20260721_complais_DB_Backup.sql."""
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import (
    ApprovalStatus,
    AuditorAnnualEvaluationsGrade,
    AuditorApprovalHistoryActionType,
    AuditorApprovalHistoryFromGrade,
    AuditorApprovalHistoryResult,
    AuditorApprovalHistoryToGrade,
    AuditorAuditActivitiesActivityType,
    AuditorCbMembershipsApplyGrade,
    AuditorCbMembershipsApprovedGrade,
    AuditorCbMembershipsEmploymentType,
    AuditorCbMembershipsFeeMethod,
    AuditorCbMembershipsStatus,
    AuditorConflictHistoryConflictType,
    AuditorEducationsDegree,
    AuditorEnvCompetencyEnvGrade,
    AuditorExternalCertsGrade,
    AuditorGradeRequirementsFromGrade,
    AuditorGradeRequirementsToGrade,
    AuditorQualificationsGrade,
    AuditorScopeGrantsGrantType,
    AuditorScopeRequestsRequestType,
    AuditorScopeRequestsStatus,
    AuditorScopeRequestsTargetGrade,
    AuditorSettlementsStatus,
    AuditorWitnessRecordsAuditType,
    AuditorWitnessRecordsResult,
    AuditorsEmploymentType,
    AuditorsGender,
    AuditorsGrade,
    AuditorsProfileStatus,
    AuditorsStatus,
)


class AuditorAnnualEvaluationsBase(BaseModel):
    auditor_id: int
    cb_id: int
    eval_year: int
    score_total: Optional[Decimal] = Field(default=None, description="종합 점수")
    score_knowledge: Optional[Decimal] = Field(default=None, description="지식/기술 점수")
    score_conduct: Optional[Decimal] = Field(default=None, description="행동강령 점수")
    score_report: Optional[Decimal] = Field(default=None, description="보고서 작성 점수")
    grade: Optional[AuditorAnnualEvaluationsGrade] = None
    evaluated_by: Optional[int] = Field(default=None, description="CB 담당자")
    evaluated_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime


class AuditorAnnualEvaluationsCreate(AuditorAnnualEvaluationsBase):
    pass


class AuditorAnnualEvaluationsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    eval_year: Optional[int] = None
    score_total: Optional[Decimal] = None
    score_knowledge: Optional[Decimal] = None
    score_conduct: Optional[Decimal] = None
    score_report: Optional[Decimal] = None
    grade: Optional[AuditorAnnualEvaluationsGrade] = None
    evaluated_by: Optional[int] = None
    evaluated_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditorAnnualEvaluationsResponse(AuditorAnnualEvaluationsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorApprovalHistoryBase(BaseModel):
    auditor_id: int
    cb_id: int
    action_type: AuditorApprovalHistoryActionType
    standard_code: Optional[str] = None
    from_grade: Optional[AuditorApprovalHistoryFromGrade] = None
    to_grade: Optional[AuditorApprovalHistoryToGrade] = None
    iaf_codes: Optional[str] = Field(default=None, description="관련 IAF 코드")
    result: AuditorApprovalHistoryResult
    detail: Optional[str] = None
    evidence_doc: Optional[str] = Field(default=None, description="증빙 참조")
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    witness_auditor_id: Optional[int] = None
    witness_contract_id: Optional[int] = None
    witness_date: Optional[date] = None
    created_at: datetime


class AuditorApprovalHistoryCreate(AuditorApprovalHistoryBase):
    pass


class AuditorApprovalHistoryUpdate(BaseModel):
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    action_type: Optional[AuditorApprovalHistoryActionType] = None
    standard_code: Optional[str] = None
    from_grade: Optional[AuditorApprovalHistoryFromGrade] = None
    to_grade: Optional[AuditorApprovalHistoryToGrade] = None
    iaf_codes: Optional[str] = None
    result: Optional[AuditorApprovalHistoryResult] = None
    detail: Optional[str] = None
    evidence_doc: Optional[str] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    witness_auditor_id: Optional[int] = None
    witness_contract_id: Optional[int] = None
    witness_date: Optional[date] = None
    created_at: Optional[datetime] = None


class AuditorApprovalHistoryResponse(AuditorApprovalHistoryBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorAuditActivitiesBase(BaseModel):
    auditor_id: int
    activity_type: AuditorAuditActivitiesActivityType
    standard_code: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: Optional[int] = None
    note: Optional[str] = None
    is_verified: Optional[bool] = None
    created_at: Optional[datetime] = None


class AuditorAuditActivitiesCreate(AuditorAuditActivitiesBase):
    pass


class AuditorAuditActivitiesUpdate(BaseModel):
    auditor_id: Optional[int] = None
    activity_type: Optional[AuditorAuditActivitiesActivityType] = None
    standard_code: Optional[str] = None
    organization: Optional[str] = None
    role: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    days: Optional[int] = None
    note: Optional[str] = None
    is_verified: Optional[bool] = None
    created_at: Optional[datetime] = None


class AuditorAuditActivitiesResponse(AuditorAuditActivitiesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorCbMembershipsBase(BaseModel):
    auditor_id: int
    cb_id: int
    employment_type: AuditorCbMembershipsEmploymentType
    is_freelance: bool
    cb_auditor_seq: Optional[int] = Field(default=None, description="플랫폼 일련번호 (전체 통합)")
    fee_method: Optional[AuditorCbMembershipsFeeMethod] = None
    fee_ratio: Optional[Decimal] = Field(default=None, description="적용비율 %")
    auditor_pct: Optional[Decimal] = Field(default=None, description="심사수당 %")
    marketing_pct: Optional[Decimal] = Field(default=None, description="마케팅 %")
    monthly_salary: Optional[Decimal] = Field(default=None, description="상근 월급")
    contract_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    status: AuditorCbMembershipsStatus
    is_primary: bool
    approved_by: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    memo: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    grade_at_cb: Optional[str] = None
    reject_reason: Optional[str] = None
    apply_message: Optional[str] = None
    apply_grade: Optional[AuditorCbMembershipsApplyGrade] = None
    cb_review_note: Optional[str] = None
    approved_grade: Optional[AuditorCbMembershipsApprovedGrade] = None
    approved_iaf_codes: Optional[str] = None
    daily_rate: Optional[int] = None
    cert_standards: Optional[str] = None
    kar_no: Optional[str] = None


class AuditorCbMembershipsCreate(AuditorCbMembershipsBase):
    pass


class AuditorCbMembershipsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    employment_type: Optional[AuditorCbMembershipsEmploymentType] = None
    is_freelance: Optional[bool] = None
    cb_auditor_seq: Optional[int] = None
    fee_method: Optional[AuditorCbMembershipsFeeMethod] = None
    fee_ratio: Optional[Decimal] = None
    auditor_pct: Optional[Decimal] = None
    marketing_pct: Optional[Decimal] = None
    monthly_salary: Optional[Decimal] = None
    contract_date: Optional[date] = None
    contract_end_date: Optional[date] = None
    status: Optional[AuditorCbMembershipsStatus] = None
    is_primary: Optional[bool] = None
    approved_by: Optional[int] = None
    requested_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    memo: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    grade_at_cb: Optional[str] = None
    reject_reason: Optional[str] = None
    apply_message: Optional[str] = None
    apply_grade: Optional[AuditorCbMembershipsApplyGrade] = None
    cb_review_note: Optional[str] = None
    approved_grade: Optional[AuditorCbMembershipsApprovedGrade] = None
    approved_iaf_codes: Optional[str] = None
    daily_rate: Optional[int] = None
    cert_standards: Optional[str] = None
    kar_no: Optional[str] = None


class AuditorCbMembershipsResponse(AuditorCbMembershipsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorClientConfirmationsBase(BaseModel):
    application_id: int
    auditor_user_id: int
    confirmation_status: str
    has_consulting_fact: bool
    note: Optional[str] = None
    confirmed_by_user_id: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditorClientConfirmationsCreate(AuditorClientConfirmationsBase):
    pass


class AuditorClientConfirmationsUpdate(BaseModel):
    application_id: Optional[int] = None
    auditor_user_id: Optional[int] = None
    confirmation_status: Optional[str] = None
    has_consulting_fact: Optional[bool] = None
    note: Optional[str] = None
    confirmed_by_user_id: Optional[int] = None
    confirmed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditorClientConfirmationsResponse(AuditorClientConfirmationsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorCompetencyScoresBase(BaseModel):
    auditor_id: int
    cb_id: int
    standard_code: str
    score: int = Field(description="0~100")
    evaluated_at: Optional[date] = None
    evaluator_id: Optional[int] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditorCompetencyScoresCreate(AuditorCompetencyScoresBase):
    pass


class AuditorCompetencyScoresUpdate(BaseModel):
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    standard_code: Optional[str] = None
    score: Optional[int] = None
    evaluated_at: Optional[date] = None
    evaluator_id: Optional[int] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditorCompetencyScoresResponse(AuditorCompetencyScoresBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorConductSignsBase(BaseModel):
    auditor_id: int
    signed_at: datetime
    expires_at: Optional[date] = None
    ip_address: Optional[str] = None
    is_valid: bool


class AuditorConductSignsCreate(AuditorConductSignsBase):
    pass


class AuditorConductSignsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    signed_at: Optional[datetime] = None
    expires_at: Optional[date] = None
    ip_address: Optional[str] = None
    is_valid: Optional[bool] = None


class AuditorConductSignsResponse(AuditorConductSignsBase):
    id: int
    signed_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorConflictChecksBase(BaseModel):
    application_id: int
    auditor_user_id: int
    has_consulting_history: bool
    has_special_relationship: bool
    has_other_support: bool
    result_status: str
    note: Optional[str] = None
    checked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditorConflictChecksCreate(AuditorConflictChecksBase):
    pass


class AuditorConflictChecksUpdate(BaseModel):
    application_id: Optional[int] = None
    auditor_user_id: Optional[int] = None
    has_consulting_history: Optional[bool] = None
    has_special_relationship: Optional[bool] = None
    has_other_support: Optional[bool] = None
    result_status: Optional[str] = None
    note: Optional[str] = None
    checked_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditorConflictChecksResponse(AuditorConflictChecksBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorConflictDeclarationsBase(BaseModel):
    auditor_id: int
    cb_id: int
    declare_year: int
    has_conflict: bool
    conflict_detail: Optional[str] = Field(default=None, description="이해상충 내용 상세")
    declared_at: datetime
    confirmed_by: Optional[int] = Field(default=None, description="CB 담당자 user_id")
    confirmed_at: Optional[datetime] = None


class AuditorConflictDeclarationsCreate(AuditorConflictDeclarationsBase):
    pass


class AuditorConflictDeclarationsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    declare_year: Optional[int] = None
    has_conflict: Optional[bool] = None
    conflict_detail: Optional[str] = None
    declared_at: Optional[datetime] = None
    confirmed_by: Optional[int] = None
    confirmed_at: Optional[datetime] = None


class AuditorConflictDeclarationsResponse(AuditorConflictDeclarationsBase):
    id: int
    model_config = ConfigDict(from_attributes=True)


class AuditorConflictHistoryBase(BaseModel):
    auditor_id: int
    company_id: Optional[int] = Field(default=None, description="companies.id")
    conflict_type: AuditorConflictHistoryConflictType
    cb_id: Optional[int] = Field(default=None, description="신고 받은 CB")
    company_biz_no: Optional[str] = None
    consult_type: Optional[str] = None
    consult_start_date: Optional[date] = None
    consult_end_date: Optional[date] = None
    restriction_until: Optional[date] = None
    note: Optional[str] = None
    created_at: datetime


class AuditorConflictHistoryCreate(AuditorConflictHistoryBase):
    pass


class AuditorConflictHistoryUpdate(BaseModel):
    auditor_id: Optional[int] = None
    company_id: Optional[int] = None
    conflict_type: Optional[AuditorConflictHistoryConflictType] = None
    cb_id: Optional[int] = None
    company_biz_no: Optional[str] = None
    consult_type: Optional[str] = None
    consult_start_date: Optional[date] = None
    consult_end_date: Optional[date] = None
    restriction_until: Optional[date] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditorConflictHistoryResponse(AuditorConflictHistoryBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorConsultingExperiencesBase(BaseModel):
    auditor_id: int
    company_name: str
    company_id: Optional[int] = None
    biz_no: Optional[str] = Field(default=None, description="자문 기업 사업자등록번호 (이해상충 검증용)")
    consulting_type: Optional[str] = Field(default=None, description="자문 유형")
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = Field(default=None, description="KSIC→IAF 자동변환")
    standard_code: Optional[str] = Field(default=None, description="컨설팅 표준")
    start_date: date
    end_date: Optional[date] = None
    consulting_days: Optional[int] = Field(default=None, description="자문 일수")
    is_verified: bool
    note: Optional[str] = None
    created_at: datetime


class AuditorConsultingExperiencesCreate(AuditorConsultingExperiencesBase):
    pass


class AuditorConsultingExperiencesUpdate(BaseModel):
    auditor_id: Optional[int] = None
    company_name: Optional[str] = None
    company_id: Optional[int] = None
    biz_no: Optional[str] = None
    consulting_type: Optional[str] = None
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    standard_code: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    consulting_days: Optional[int] = None
    is_verified: Optional[bool] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditorConsultingExperiencesResponse(AuditorConsultingExperiencesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorEducationsBase(BaseModel):
    auditor_id: int
    degree: AuditorEducationsDegree
    school_name: str
    major: str = Field(description="전공학과")
    entered_at: Optional[date] = Field(default=None, description="입학·시작일")
    graduated_at: Optional[date] = None
    mapped_iaf_codes: Optional[str] = Field(default=None, description="JSON 배열 — 자동 매핑 결과")
    is_verified: bool = Field(description="CB 확인 여부")
    created_at: datetime


class AuditorEducationsCreate(AuditorEducationsBase):
    pass


class AuditorEducationsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    degree: Optional[AuditorEducationsDegree] = None
    school_name: Optional[str] = None
    major: Optional[str] = None
    entered_at: Optional[date] = None
    graduated_at: Optional[date] = None
    mapped_iaf_codes: Optional[str] = None
    is_verified: Optional[bool] = None
    created_at: Optional[datetime] = None


class AuditorEducationsResponse(AuditorEducationsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorEnvCompetencyBase(BaseModel):
    auditor_id: int
    cb_id: int
    iaf_code: str
    env_grade: AuditorEnvCompetencyEnvGrade = Field(description="E1=매우높음~E4=낮음")
    score_total: Optional[int] = Field(default=None, description="총 점수")
    score_education: Optional[int] = Field(default=None, description="전공 점수")
    score_work_exp: Optional[int] = Field(default=None, description="실무경력 점수")
    score_training: Optional[int] = Field(default=None, description="교육이수 점수")
    score_audit_exp: Optional[int] = Field(default=None, description="심사경력 점수")
    granted_by: Optional[int] = None
    granted_at: Optional[date] = None
    is_active: bool
    created_at: datetime


class AuditorEnvCompetencyCreate(AuditorEnvCompetencyBase):
    pass


class AuditorEnvCompetencyUpdate(BaseModel):
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    iaf_code: Optional[str] = None
    env_grade: Optional[AuditorEnvCompetencyEnvGrade] = None
    score_total: Optional[int] = None
    score_education: Optional[int] = None
    score_work_exp: Optional[int] = None
    score_training: Optional[int] = None
    score_audit_exp: Optional[int] = None
    granted_by: Optional[int] = None
    granted_at: Optional[date] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None


class AuditorEnvCompetencyResponse(AuditorEnvCompetencyBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorExternalCertsBase(BaseModel):
    auditor_id: int
    qual_org: str = Field(description="자격기관 이니셜 (KAR/KFQ/ITS 등)")
    qual_no: str = Field(description="자격증 번호 (원본 그대로)")
    standard_code: str = Field(description="QMS/EMS/OHSMS 등")
    grade: AuditorExternalCertsGrade
    granted_at: Optional[date] = None
    expires_at: Optional[date] = None
    note: Optional[str] = None
    created_at: datetime


class AuditorExternalCertsCreate(AuditorExternalCertsBase):
    pass


class AuditorExternalCertsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    qual_org: Optional[str] = None
    qual_no: Optional[str] = None
    standard_code: Optional[str] = None
    grade: Optional[AuditorExternalCertsGrade] = None
    granted_at: Optional[date] = None
    expires_at: Optional[date] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditorExternalCertsResponse(AuditorExternalCertsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorGradeRequirementsBase(BaseModel):
    from_grade: AuditorGradeRequirementsFromGrade
    to_grade: AuditorGradeRequirementsToGrade
    standard_code: str = Field(description="ALL=공통, QMS/EMS=표준별")
    min_audit_days: Optional[int] = Field(default=None, description="최소 심사일수")
    min_full_audit_count: Optional[int] = Field(default=None, description="최소 전체심사 횟수")
    min_initial_renewal: Optional[int] = Field(default=None, description="최소 최초/갱신심사 횟수")
    min_lead_count: Optional[int] = Field(default=None, description="최소 팀장 역할 횟수")
    min_lead_days: Optional[int] = Field(default=None, description="팀장으로서 최소 심사일수")
    min_years_as_grade: Optional[int] = Field(default=None, description="현 등급 최소 유지 연수")
    cross_standard_discount: int = Field(description="타 표준 보유 시 요건 완화")
    cross_discount_days: Optional[int] = Field(default=None, description="완화 시 심사일수")
    requires_witness: int = Field(description="입회 필요 여부")
    witness_count: Optional[int] = Field(default=None, description="필요 입회 횟수")
    note: Optional[str] = None
    created_at: datetime


class AuditorGradeRequirementsCreate(AuditorGradeRequirementsBase):
    pass


class AuditorGradeRequirementsUpdate(BaseModel):
    from_grade: Optional[AuditorGradeRequirementsFromGrade] = None
    to_grade: Optional[AuditorGradeRequirementsToGrade] = None
    standard_code: Optional[str] = None
    min_audit_days: Optional[int] = None
    min_full_audit_count: Optional[int] = None
    min_initial_renewal: Optional[int] = None
    min_lead_count: Optional[int] = None
    min_lead_days: Optional[int] = None
    min_years_as_grade: Optional[int] = None
    cross_standard_discount: Optional[int] = None
    cross_discount_days: Optional[int] = None
    requires_witness: Optional[int] = None
    witness_count: Optional[int] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditorGradeRequirementsResponse(AuditorGradeRequirementsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorQualificationsBase(BaseModel):
    auditor_id: int
    cb_id: int = Field(description="자격 관리 CB")
    standard_code: str = Field(description="QMS/EMS/OHSMS/EnMS/BCMS/ISMS/IATF")
    grade: AuditorQualificationsGrade
    pcaa_seq: Optional[int] = Field(default=None, description="플랫폼 일련번호 (전체 통합)")
    pcaa_no: Optional[str] = Field(default=None, description="SMI-Q-10001 형식 (cb_initial+standard+seq)")
    granted_at: Optional[date] = None
    expires_at: Optional[date] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AuditorQualificationsCreate(AuditorQualificationsBase):
    pass


class AuditorQualificationsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    standard_code: Optional[str] = None
    grade: Optional[AuditorQualificationsGrade] = None
    pcaa_seq: Optional[int] = None
    pcaa_no: Optional[str] = None
    granted_at: Optional[date] = None
    expires_at: Optional[date] = None
    is_active: Optional[bool] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AuditorQualificationsResponse(AuditorQualificationsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorScopeGrantsBase(BaseModel):
    auditor_id: int
    cb_id: int
    standard_code: str
    iaf_code: str = Field(description="IAF 코드 (03, 04A 등)")
    nace_code: Optional[str] = None
    grant_type: AuditorScopeGrantsGrantType = Field(description="부여 근거")
    granted_by: Optional[int] = Field(default=None, description="CB 담당자 user_id")
    granted_at: date
    expires_at: Optional[date] = None
    is_active: bool
    note: Optional[str] = None
    created_at: datetime
    nace_codes: Optional[str] = Field(default=None, description="NACE Division 코드 (콤마구분)")
    iaf_codes: Optional[str] = Field(default=None, description="IAF 코드 (콤마구분)")
    mdqms_areas: Optional[str] = Field(default=None, description="ISO 13485 기술영역")
    sub_codes: Optional[str] = Field(default=None, description="IAF 세분류 코드 (콤마구분)")
    witness_auditor_id: Optional[int] = Field(default=None, description="참관 검증심사원")
    witness_contract_id: Optional[int] = Field(default=None, description="참관 심사 계약")
    witness_date: Optional[date] = Field(default=None, description="참관 일자")


class AuditorScopeGrantsCreate(AuditorScopeGrantsBase):
    pass


class AuditorScopeGrantsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    standard_code: Optional[str] = None
    iaf_code: Optional[str] = None
    nace_code: Optional[str] = None
    grant_type: Optional[AuditorScopeGrantsGrantType] = None
    granted_by: Optional[int] = None
    granted_at: Optional[date] = None
    expires_at: Optional[date] = None
    is_active: Optional[bool] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    nace_codes: Optional[str] = None
    iaf_codes: Optional[str] = None
    mdqms_areas: Optional[str] = None
    sub_codes: Optional[str] = None
    witness_auditor_id: Optional[int] = None
    witness_contract_id: Optional[int] = None
    witness_date: Optional[date] = None


class AuditorScopeGrantsResponse(AuditorScopeGrantsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorScopeRequestsBase(BaseModel):
    auditor_id: int
    cb_id: int
    request_type: AuditorScopeRequestsRequestType = Field(description="qualification=자격확대, code_expand=코드확대, grade_up=등급승급")
    standard_code: Optional[str] = Field(default=None, description="자격확대 시 새 표준")
    iaf_codes: Optional[str] = Field(default=None, description="IAF 코드 (콤마구분)")
    target_grade: Optional[AuditorScopeRequestsTargetGrade] = Field(default=None, description="승급 목표 등급")
    reason: Optional[str] = Field(default=None, description="신청 사유")
    evidence_note: Optional[str] = Field(default=None, description="증빙 안내 (메일 발송 내용)")
    status: AuditorScopeRequestsStatus
    reviewed_by: Optional[int] = Field(default=None, description="CB 담당자 user_id")
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    requested_at: datetime
    updated_at: datetime
    nace_codes: Optional[str] = Field(default=None, description="NACE Division 코드 (콤마구분)")
    sub_codes: Optional[str] = Field(default=None, description="IAF 세분류 코드 (콤마구분)")


class AuditorScopeRequestsCreate(AuditorScopeRequestsBase):
    pass


class AuditorScopeRequestsUpdate(BaseModel):
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    request_type: Optional[AuditorScopeRequestsRequestType] = None
    standard_code: Optional[str] = None
    iaf_codes: Optional[str] = None
    target_grade: Optional[AuditorScopeRequestsTargetGrade] = None
    reason: Optional[str] = None
    evidence_note: Optional[str] = None
    status: Optional[AuditorScopeRequestsStatus] = None
    reviewed_by: Optional[int] = None
    reviewed_at: Optional[datetime] = None
    review_note: Optional[str] = None
    requested_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    nace_codes: Optional[str] = None
    sub_codes: Optional[str] = None


class AuditorScopeRequestsResponse(AuditorScopeRequestsBase):
    id: int
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorSeqBase(BaseModel):
    last_seq: int = Field(description="마지막 채번 번호")
    updated_at: datetime


class AuditorSeqCreate(AuditorSeqBase):
    pass


class AuditorSeqUpdate(BaseModel):
    last_seq: Optional[int] = None
    updated_at: Optional[datetime] = None


class AuditorSeqResponse(AuditorSeqBase):
    id: int
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorSettlementsBase(BaseModel):
    contract_id: int = Field(description="contracts.id (also used as project_id)")
    auditor_id: int
    cb_id: Optional[int] = None
    settlement_month: Optional[str] = Field(default=None, description="YYYY-MM")
    amount: Decimal
    status: AuditorSettlementsStatus
    paid_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: datetime


class AuditorSettlementsCreate(AuditorSettlementsBase):
    pass


class AuditorSettlementsUpdate(BaseModel):
    contract_id: Optional[int] = None
    auditor_id: Optional[int] = None
    cb_id: Optional[int] = None
    settlement_month: Optional[str] = None
    amount: Optional[Decimal] = None
    status: Optional[AuditorSettlementsStatus] = None
    paid_at: Optional[datetime] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None


class AuditorSettlementsResponse(AuditorSettlementsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorWitnessRecordsBase(BaseModel):
    contract_id: int = Field(description="심사 계약")
    cb_id: int
    witness_auditor_id: int = Field(description="입회한 검증심사원")
    observed_auditor_id: int = Field(description="관찰받은 심사원")
    witness_date: date
    audit_type: AuditorWitnessRecordsAuditType
    result: AuditorWitnessRecordsResult
    observation_days: Optional[Decimal] = Field(default=None, description="입회 일수")
    note: Optional[str] = None
    checklist_id: Optional[int] = Field(default=None, description="나중에 체크리스트 연결")
    created_at: datetime


class AuditorWitnessRecordsCreate(AuditorWitnessRecordsBase):
    pass


class AuditorWitnessRecordsUpdate(BaseModel):
    contract_id: Optional[int] = None
    cb_id: Optional[int] = None
    witness_auditor_id: Optional[int] = None
    observed_auditor_id: Optional[int] = None
    witness_date: Optional[date] = None
    audit_type: Optional[AuditorWitnessRecordsAuditType] = None
    result: Optional[AuditorWitnessRecordsResult] = None
    observation_days: Optional[Decimal] = None
    note: Optional[str] = None
    checklist_id: Optional[int] = None
    created_at: Optional[datetime] = None


class AuditorWitnessRecordsResponse(AuditorWitnessRecordsBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorWorkExperiencesBase(BaseModel):
    auditor_id: int
    company_name: str
    company_id: Optional[int] = Field(default=None, description="complais 등록 기업이면 연결")
    ksic_code: Optional[str] = Field(default=None, description="KSIC 코드")
    iaf_code: Optional[str] = Field(default=None, description="KSIC→IAF 자동변환 결과")
    nace_code: Optional[str] = None
    position: Optional[str] = Field(default=None, description="직위/직책")
    department: Optional[str] = Field(default=None, description="부서")
    start_date: date
    end_date: Optional[date] = Field(default=None, description="NULL이면 현재 재직 중")
    is_current: bool
    work_years: Optional[Decimal] = Field(default=None, description="근무 연수 (자동계산)")
    is_verified: bool
    note: Optional[str] = None
    created_at: datetime
    biz_no: Optional[str] = Field(default=None, description="사업자등록번호 (IAF 자동 조회용)")


class AuditorWorkExperiencesCreate(AuditorWorkExperiencesBase):
    pass


class AuditorWorkExperiencesUpdate(BaseModel):
    auditor_id: Optional[int] = None
    company_name: Optional[str] = None
    company_id: Optional[int] = None
    ksic_code: Optional[str] = None
    iaf_code: Optional[str] = None
    nace_code: Optional[str] = None
    position: Optional[str] = None
    department: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: Optional[bool] = None
    work_years: Optional[Decimal] = None
    is_verified: Optional[bool] = None
    note: Optional[str] = None
    created_at: Optional[datetime] = None
    biz_no: Optional[str] = None


class AuditorWorkExperiencesResponse(AuditorWorkExperiencesBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorsBase(BaseModel):
    complais_no: Optional[str] = Field(default=None, description="ComplAIs 개인번호 (YYYYMMDD-NNN)")
    user_id: Optional[int] = None
    name: str
    name_en: Optional[str] = None
    email: str
    phone: Optional[str] = None
    grade: AuditorsGrade
    employment_type: AuditorsEmploymentType
    is_freelance: bool
    primary_cb_id: Optional[int] = Field(default=None, description="주 소속 CB")
    registration_no: Optional[str] = None
    iaf_codes: Optional[str] = None
    is_active: bool
    status: AuditorsStatus
    contract_type: str
    daily_rate: Decimal
    fee_ratio: Decimal
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None
    intro: Optional[str] = None
    monthly_fee: Decimal
    created_at: datetime
    updated_at: datetime
    birth_date: Optional[date] = None
    gender: Optional[AuditorsGender] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    profile_status: Optional[AuditorsProfileStatus] = None


class AuditorsCreate(AuditorsBase):
    pass


class AuditorsUpdate(BaseModel):
    complais_no: Optional[str] = None
    user_id: Optional[int] = None
    name: Optional[str] = None
    name_en: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    grade: Optional[AuditorsGrade] = None
    employment_type: Optional[AuditorsEmploymentType] = None
    is_freelance: Optional[bool] = None
    primary_cb_id: Optional[int] = None
    registration_no: Optional[str] = None
    iaf_codes: Optional[str] = None
    is_active: Optional[bool] = None
    status: Optional[AuditorsStatus] = None
    contract_type: Optional[str] = None
    daily_rate: Optional[Decimal] = None
    fee_ratio: Optional[Decimal] = None
    bank_name: Optional[str] = None
    account_no: Optional[str] = None
    account_holder: Optional[str] = None
    intro: Optional[str] = None
    monthly_fee: Optional[Decimal] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    birth_date: Optional[date] = None
    gender: Optional[AuditorsGender] = None
    address: Optional[str] = None
    detail_address: Optional[str] = None
    profile_status: Optional[AuditorsProfileStatus] = None


class AuditorsResponse(AuditorsBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# --- Qualification approval workflow ---

class QualificationApplyRequest(BaseModel):
    """심사원 자격 신청."""
    standard: str
    sub_code: str


class QualificationApproveAction(BaseModel):
    """인증기관 자격 승인/반려."""
    action: ApprovalStatus  # APPROVED 또는 REJECTED


class QualificationResponse(BaseModel):
    id: int
    auditor_id: int
    standard: str
    sub_code: str
    approval_status: str
    approved_by: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)


class AuditorExperienceRecordBase(BaseModel):
    auditor_id: int
    period_year: int = Field(description="통계 연도")
    initial_count: int = 0
    surveillance_count: int = 0
    renewal_count: int = 0
    total_audit_days: int = 0


class AuditorExperienceRecordCreate(AuditorExperienceRecordBase):
    pass


class AuditorExperienceRecordUpdate(BaseModel):
    auditor_id: Optional[int] = None
    period_year: Optional[int] = None
    initial_count: Optional[int] = None
    surveillance_count: Optional[int] = None
    renewal_count: Optional[int] = None
    total_audit_days: Optional[int] = None


class AuditorExperienceRecordResponse(AuditorExperienceRecordBase):
    id: int
    created_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)


# Re-export profile/detail schemas (canonical definitions in auditor_profile.py)
from app.schemas.auditor_profile import (  # noqa: E402
    AuditorDetailResponse,
    ConsultingExperienceSchema,
    EducationSchema,
    ExternalCertSchema,
    WorkExperienceSchema,
)
