"""Auto-generated enum types from MariaDB schema."""

import enum


class ApprovalStatus(str, enum.Enum):
    PENDING = "PENDING"     # 승인 대기
    APPROVED = "APPROVED"   # 승인 완료
    REJECTED = "REJECTED"   # 반려
    EXPIRED = "EXPIRED"     # 만료


# 심사원→인증원 승인 요청 상태 (ApprovalStatus와 동일 값)
class ApplicationStatus(str, enum.Enum):
    PENDING = "PENDING"     # 승인 대기
    APPROVED = "APPROVED"   # 승인 완료
    REJECTED = "REJECTED"   # 반려


class ProposalStatus(str, enum.Enum):
    """인증 제안서 워크플로 상태 (FE types/proposal.ts 와 동일).

    DRAFT → SURVEY_SUBMITTED → MD_CALCULATED → COST_APPLIED
      → AUDITOR_ASSIGNED → PENDING_APPROVAL → APPROVED → DISPATCHED
                                         ↘ REJECTED
    """

    DRAFT = "DRAFT"  # 기업 신청 및 임시저장
    SURVEY_SUBMITTED = "SURVEY_SUBMITTED"  # 설문 제출 완료
    MD_CALCULATED = "MD_CALCULATED"  # M/D 및 가감요인 산정 완료
    COST_APPLIED = "COST_APPLIED"  # 심사비 확정
    AUDITOR_ASSIGNED = "AUDITOR_ASSIGNED"  # 심사원 배정 완료
    PENDING_APPROVAL = "PENDING_APPROVAL"  # 승인 요청 (결재 대기)
    APPROVED = "APPROVED"  # 승인 완료 (제안서 확정)
    REJECTED = "REJECTED"  # 반려 (보완 요청)
    DISPATCHED = "DISPATCHED"  # 기업에 제안서 최종 발송


PROPOSAL_STATUS_LABELS = {
    ProposalStatus.DRAFT: "임시저장",
    ProposalStatus.SURVEY_SUBMITTED: "설문 제출",
    ProposalStatus.MD_CALCULATED: "M/D 산정",
    ProposalStatus.COST_APPLIED: "심사비 확정",
    ProposalStatus.AUDITOR_ASSIGNED: "심사원 배정",
    ProposalStatus.PENDING_APPROVAL: "결재 대기",
    ProposalStatus.APPROVED: "승인 완료",
    ProposalStatus.REJECTED: "반려(보완)",
    ProposalStatus.DISPATCHED: "제안서 발송",
}

PROPOSAL_STATUS_TRANSITIONS = {
    ProposalStatus.DRAFT: {ProposalStatus.SURVEY_SUBMITTED},
    ProposalStatus.SURVEY_SUBMITTED: {ProposalStatus.MD_CALCULATED},
    ProposalStatus.MD_CALCULATED: {ProposalStatus.COST_APPLIED},
    ProposalStatus.COST_APPLIED: {ProposalStatus.AUDITOR_ASSIGNED},
    ProposalStatus.AUDITOR_ASSIGNED: {ProposalStatus.PENDING_APPROVAL},
    ProposalStatus.PENDING_APPROVAL: {
        ProposalStatus.APPROVED,
        ProposalStatus.REJECTED,
    },
    ProposalStatus.APPROVED: {ProposalStatus.DISPATCHED},
    ProposalStatus.REJECTED: {
        ProposalStatus.SURVEY_SUBMITTED,
        ProposalStatus.MD_CALCULATED,
        ProposalStatus.COST_APPLIED,
        ProposalStatus.AUDITOR_ASSIGNED,
        ProposalStatus.PENDING_APPROVAL,
    },
    ProposalStatus.DISPATCHED: set(),
}


def can_transition_proposal_status(from_status: str, to_status: str) -> bool:
    try:
        src = ProposalStatus(from_status)
        dst = ProposalStatus(to_status)
    except ValueError:
        return False
    return dst in PROPOSAL_STATUS_TRANSITIONS.get(src, set())


class CompanyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"       # 정상
    SUSPENDED = "SUSPENDED" # 휴업
    CLOSED = "CLOSED"       # 폐업
    CANCELLED = "CANCELLED" # 인증취소


class IncomeType(str, enum.Enum):
    BUSINESS_3_3 = "BUSINESS_3_3" # 3.3% 사업소득
    OTHER_INCOME = "OTHER_INCOME" # 기타소득
    TAX_INVOICE = "TAX_INVOICE"   # 세금계산서


class AuditAssignmentsRole(str, enum.Enum):
    LEAD = "lead"
    AUDITOR = "auditor"
    EXPERT = "expert"
    OBSERVER = "observer"
    WITNESS = "witness"

class AuditClauseMatrixTargetAuditType(str, enum.Enum):
    SURVEILLANCE = "surveillance"
    RECERTIFICATION = "recertification"

class AuditDocumentRulesAuditType(str, enum.Enum):
    INITIAL = "initial"
    SURVEILLANCE = "surveillance"
    RECERTIFICATION = "recertification"
    TRANSFER = "transfer"
    SPECIAL = "special"

class AuditDocumentsDocStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"

class AuditNcrsGrade(str, enum.Enum):
    MAJOR = "major"
    MINOR = "minor"
    OBS = "obs"

class AuditNcrsStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    CA_SUBMITTED = "ca_submitted"
    CA_APPROVED = "ca_approved"
    CA_REJECTED = "ca_rejected"
    CLOSED = "closed"

class AuditNoteClausesVerdict(str, enum.Enum):
    VAL_0 = "적합"
    VAL_1 = "관찰사항"
    VAL_2 = "경미한부적합"
    VAL_3 = "중대한부적합"
    VAL_4 = "해당없음"

class AuditNoteNcrGrade(str, enum.Enum):
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"

class AuditNoteNcrStatus(str, enum.Enum):
    OPEN = "open"
    CLIENT_RESPONSE = "client_response"
    CB_REVIEW = "cb_review"
    WAITING_TEAM_REVIEW = "waiting_team_review"  # ≥2인 팀 — 팀장 팀검토 전 NCR 종결 보류
    CLOSED = "closed"
    OVERDUE = "overdue"

class AuditNotesStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    APPROVED = "approved"

class AuditNotesOverallVerdict(str, enum.Enum):
    VAL_0 = "적합"
    VAL_1 = "조건부적합"
    VAL_2 = "부적합"

class AuditNotesFindingType(str, enum.Enum):
    OK = "ok"
    MINOR = "minor"
    MAJOR = "major"
    OBS = "obs"

class AuditPlansStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    CONFIRMED = "confirmed"

class AuditProposalNegotiationsSenderType(str, enum.Enum):
    COMPANY = "company"
    CB = "cb"

class AuditReportsReportType(str, enum.Enum):
    STAGE1 = "stage1"
    STAGE2 = "stage2"
    COMBINED = "combined"
    SURVEILLANCE = "surveillance"
    RECERTIFICATION = "recertification"

class AuditReportsVerdict(str, enum.Enum):
    VAL_0 = "적합"
    VAL_1 = "조건부적합"
    VAL_2 = "부적합"

class AuditReportsStatus(str, enum.Enum):
    DRAFT = "draft"
    ISSUED = "issued"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"

class AuditorAnnualEvaluationsGrade(str, enum.Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    AVERAGE = "average"
    POOR = "poor"

class AuditorApprovalHistoryActionType(str, enum.Enum):
    INITIAL_REGISTRATION = "initial_registration"
    INITIAL_VERIFICATION = "initial_verification"
    SCOPE_GRANT = "scope_grant"
    CODE_EXPAND = "code_expand"
    QUALIFICATION_EXPAND = "qualification_expand"
    GRADE_UP = "grade_up"
    RENEWAL = "renewal"
    SUSPENSION = "suspension"
    REINSTATEMENT = "reinstatement"

class AuditorApprovalHistoryFromGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    # legacy aliases
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class AuditorApprovalHistoryToGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    # legacy aliases
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class AuditorApprovalHistoryResult(str, enum.Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"

class AuditorAuditActivitiesActivityType(str, enum.Enum):
    TRAINING = "training"
    EXPERIENCE = "experience"
    AUDIT_TRAINING = "audit_training"
    SENIOR = "senior"
    VERIFIER = "verifier"

class AuditorCbMembershipsEmploymentType(str, enum.Enum):
    FULLTIME = "fulltime"
    PARTTIME = "parttime"

class AuditorCbMembershipsFeeMethod(str, enum.Enum):
    FIXED = "fixed"
    RATIO = "ratio"
    MONTHLY = "monthly"

class AuditorCbMembershipsStatus(str, enum.Enum):
    REQUESTED = "requested"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    TERMINATED = "terminated"
    SUSPENDED = "suspended"
    EXPIRED = "expired"

class AuditorCbMembershipsApplyGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    # legacy aliases
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class AuditorCbMembershipsApprovedGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    # legacy aliases
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class AuditorConflictHistoryConflictType(str, enum.Enum):
    EMPLOYMENT = "employment"
    CONSULTING = "consulting"

class AuditorEducationsDegree(str, enum.Enum):
    HIGH_SCHOOL = "high_school"
    ASSOCIATE = "associate"
    BACHELOR = "bachelor"
    MASTER = "master"
    DOCTOR = "doctor"
    OTHER = "other"

class AuditorEnvCompetencyEnvGrade(str, enum.Enum):
    E1 = "E1"
    E2 = "E2"
    E3 = "E3"
    E4 = "E4"

class AuditorExternalCertsGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class AuditorGradeRequirementsFromGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    SENIOR = "lead_auditor"

class AuditorGradeRequirementsToGrade(str, enum.Enum):
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class AuditorQualificationsGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class AuditorScopeGrantsGrantType(str, enum.Enum):
    EDUCATION = "education"
    WORK_EXP = "work_exp"
    AUDIT_EXP = "audit_exp"
    CONSULTING = "consulting"

class AuditorScopeRequestsRequestType(str, enum.Enum):
    QUALIFICATION = "qualification"
    CODE_EXPAND = "code_expand"
    GRADE_UP = "grade_up"

class AuditorScopeRequestsTargetGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class AuditorScopeRequestsStatus(str, enum.Enum):
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"

class AuditorSettlementsStatus(str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"

class AuditorWitnessRecordsAuditType(str, enum.Enum):
    INITIAL = "initial"
    SURVEILLANCE = "surveillance"
    RECERTIFICATION = "recertification"

class AuditorWitnessRecordsResult(str, enum.Enum):
    PASS = "pass"
    CONDITIONAL = "conditional"
    FAIL = "fail"
    PENDING = "pending"

class AuditorsGrade(str, enum.Enum):
    """심사원 등급 — 표준 정의는 app.core.constants.AuditorGrade 와 동일."""
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    # legacy aliases
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class AuditorsEmploymentType(str, enum.Enum):
    FULLTIME = "fulltime"
    PARTTIME = "parttime"

class AuditorsStatus(str, enum.Enum):
    ACTIVE = "active"
    LEAVE = "leave"
    SUSPENDED = "suspended"

class AuditorsGender(str, enum.Enum):
    M = "M"
    F = "F"
    VAL_2 = ""

class AuditorsProfileStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class CbAccreditationsStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"

class CbApprovalLinesConditionType(str, enum.Enum):
    ALWAYS = "always"
    DISCOUNT_OVER = "discount_over"

class CbApprovalLinesApprovalType(str, enum.Enum):
    ANY = "any"
    ALL = "all"

class CbFeePolicyFeeMethod(str, enum.Enum):
    FIXED = "fixed"
    RATIO = "ratio"

class CbFeePolicyAuditType(str, enum.Enum):
    INITIAL = "initial"
    SURVEILLANCE = "surveillance"
    RECERTIFICATION = "recertification"
    TRANSFER = "transfer"
    SPECIAL = "special"

class CbNoticesTarget(str, enum.Enum):
    ALL = "all"
    AUDITOR = "auditor"
    COMPANY = "company"

class CbNoticesPriority(str, enum.Enum):
    NORMAL = "normal"
    IMPORTANT = "important"
    URGENT = "urgent"

class CbProposalApprovalsApprovalType(str, enum.Enum):
    ANY = "any"
    ALL = "all"

class CbProposalApprovalsStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SKIPPED = "skipped"

class CbProposalNegotiationsSenderType(str, enum.Enum):
    COMPANY = "company"
    CB = "cb"

class CbProposalTeamRole(str, enum.Enum):
    LEAD = "lead"
    AUDITOR = "auditor"
    OBSERVER = "observer"
    EXPERT = "expert"
    WITNESS = "witness"

class CbProposalsApprovalStatus(str, enum.Enum):
    DRAFT = "draft"
    REVIEWING = "reviewing"
    APPROVED = "approved"
    REJECTED = "rejected"

class CertificatesStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"

class CertificationApplicationsApplicationType(str, enum.Enum):
    INITIAL = "initial"
    SURVEILLANCE = "surveillance"
    RECERTIFICATION = "recertification"
    SCOPE_EXTENSION = "scope_extension"
    TRANSFER = "transfer"
    SPECIAL = "special"

class CertificationApplicationsStatus(str, enum.Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    NEED_FIX = "need_fix"
    APPROVED = "approved"
    COMPANY_REVISION_REQUESTED = "company_revision_requested"  # 기업 조율 요청(CB 내부승인 후)
    REJECTED = "rejected"
    CONTRACTED = "contracted"
    WITHDRAWN = "withdrawn"

class CertificationApplicationsAuditMode(str, enum.Enum):
    SINGLE = "single"
    INTEGRATED = "integrated"

class CertificationBodiesCbType(str, enum.Enum):
    CERTIFICATION = "certification"
    EDUCATION = "education"
    CONSULTING = "consulting"
    OTHER = "other"

class CompanyDocumentsStatus(str, enum.Enum):
    ACTIVE = "active"
    REVIEW = "review"
    DRAFT = "draft"
    OBSOLETE = "obsolete"

class CompanyDocumentsAccessLevel(str, enum.Enum):
    ALL = "all"
    MANAGER = "manager"
    ADMIN = "admin"

class CompanySuppliersRelation(str, enum.Enum):
    VENDOR = "vendor"
    CUSTOMER = "customer"
    BOTH = "both"

class CompanySuppliersStatus(str, enum.Enum):
    ACTIVE = "active"
    PENDING = "pending"
    INACTIVE = "inactive"

class ContractsVerificationStatus(str, enum.Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"

class ContractsAuditType(str, enum.Enum):
    INITIAL = "initial"
    SURVEILLANCE = "surveillance"
    RECERTIFICATION = "recertification"
    SPECIAL = "special"
    TRANSFER = "transfer"

class ContractsStage(str, enum.Enum):
    STAGE1 = "stage1"
    STAGE2 = "stage2"
    COMBINED = "combined"

class ContractsStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    CLIENT_SIGNED = "client_signed"
    SIGNED = "signed"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    NOTE_SUBMITTED = "note_submitted"
    REPORT_READY = "report_ready"
    CERTIFIED = "certified"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class ContractsContractType(str, enum.Enum):
    CERTIFICATION = "certification"
    AUDITOR = "auditor"
    NDA = "nda"

class ContractsAuditMode(str, enum.Enum):
    SINGLE = "single"
    INTEGRATED = "integrated"

class EduCoursesDeliveryMode(str, enum.Enum):
    OFFLINE = "offline"
    ONLINE_LIVE = "online_live"
    ELEARNING = "elearning"
    INVITED = "invited"
    BLENDED = "blended"

class EduCoursesStatus(str, enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"
    ARCHIVED = "archived"

class EduEnrollmentsStatus(str, enum.Enum):
    APPLIED = "applied"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    ATTENDING = "attending"
    COMPLETED = "completed"
    FAILED = "failed"

class EduEnrollmentsPaymentStatus(str, enum.Enum):
    UNPAID = "unpaid"
    PAID = "paid"
    INVOICED = "invoiced"
    REFUNDED = "refunded"

class EduEnrollmentsRefundStatus(str, enum.Enum):
    NONE = "none"
    REQUESTED = "requested"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    PAID = "paid"
    REJECTED = "rejected"

class EduProvidersType(str, enum.Enum):
    FOUNDATION = "foundation"
    ASSOCIATION = "association"
    PRIVATE = "private"
    CB_AFFILIATED = "cb_affiliated"
    UNIVERSITY = "university"
    GOV = "gov"

class EduProvidersStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    CLOSED = "closed"

class EduSessionsStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    RECRUITING = "recruiting"
    FULL = "full"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"

class EmissionFactorMasterFuelType(str, enum.Enum):
    ELECTRICITY = "electricity"
    FOSSIL_FUEL = "fossil_fuel"
    RENEWABLE = "renewable"
    STEAM = "steam"
    OTHER = "other"

class EsgMasterCategory(str, enum.Enum):
    E = "E"
    S = "S"
    G = "G"

class EsgMasterSourceType(str, enum.Enum):
    AUDIT = "audit"
    API = "api"
    DIRECT = "direct"

class InvitationsRole(str, enum.Enum):
    CB_STAFF = "cb_staff"
    CB_MANAGER = "cb_manager"
    CB_REVIEWER = "cb_reviewer"

class InvitationsStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    EXPIRED = "expired"

class KarCpdRecordsActivityType(str, enum.Enum):
    EDUCATION = "education"
    SEMINAR = "seminar"
    PUBLICATION = "publication"
    EXAM = "exam"
    OTHER = "other"

class KarCpdRecordsStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"

class KarQualificationsGrade(str, enum.Enum):
    JUNIOR = "junior"
    AUDITOR = "auditor"
    LEAD_AUDITOR = "lead_auditor"
    VERIFIED_AUDITOR = "verified_auditor"
    TRAINEE = "trainee"
    # legacy aliases
    SENIOR = "lead_auditor"
    VERIFIER = "verified_auditor"

class KarQualificationsStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    PENDING = "pending"

class KarRenewalRequestsStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    APPROVED = "approved"
    REJECTED = "rejected"

class KpiMasterCategoryEsg(str, enum.Enum):
    E = "E"
    S = "S"
    G = "G"

class KpiMasterDirection(str, enum.Enum):
    LOWER_BETTER = "lower_better"
    HIGHER_BETTER = "higher_better"
    TARGET = "target"

class MasterIafCodesRisk9001(str, enum.Enum):
    VAL_0 = "낮음"
    VAL_1 = "중간"
    VAL_2 = "높음"
    VAL_3 = "제한"
    VAL_4 = "특별"

class MasterIafCodesRisk14001(str, enum.Enum):
    VAL_0 = "낮음"
    VAL_1 = "중간"
    VAL_2 = "높음"
    VAL_3 = "제한"
    VAL_4 = "특별"

class MasterIafCodesRisk45001(str, enum.Enum):
    VAL_0 = "낮음"
    VAL_1 = "중간"
    VAL_2 = "높음"
    VAL_3 = "제한"
    VAL_4 = "특별"

class MaterialBalanceItemsCategory(str, enum.Enum):
    INPUT = "input"
    OUTPUT = "output"

class NaceCodesRisk9001(str, enum.Enum):
    VAL_0 = "낮음"
    VAL_1 = "중간"
    VAL_2 = "높음"
    VAL_3 = "제한"
    VAL_4 = "특별"

class NaceCodesRisk14001(str, enum.Enum):
    VAL_0 = "낮음"
    VAL_1 = "중간"
    VAL_2 = "높음"
    VAL_3 = "제한"
    VAL_4 = "특별"

class NaceCodesRisk45001(str, enum.Enum):
    VAL_0 = "낮음"
    VAL_1 = "중간"
    VAL_2 = "높음"
    VAL_3 = "제한"
    VAL_4 = "특별"

class NcrReportsNcGrade(str, enum.Enum):
    MAJOR = "major"
    MINOR = "minor"
    OBSERVATION = "observation"

class NcrReportsStatus(str, enum.Enum):
    OPEN = "open"
    IN_REVIEW = "in_review"
    CLOSED = "closed"
    CANCELLED = "cancelled"

class NotificationsChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    PUSH = "push"

class PlatformContactsType(str, enum.Enum):
    VAL_0 = "서비스문의"
    VAL_1 = "기술문의"
    VAL_2 = "기타"

class PlatformContactsStatus(str, enum.Enum):
    VAL_0 = "접수"
    VAL_1 = "처리중"
    VAL_2 = "완료"

class PlatformFaqCategory(str, enum.Enum):
    VAL_0 = "공통"
    VAL_1 = "인증기관"
    VAL_2 = "심사원"
    VAL_3 = "기업"

class PlatformNoticesType(str, enum.Enum):
    UPDATE = "UPDATE"
    PRESS = "PRESS"
    NOTICE = "NOTICE"

class SubscriptionSeatsSeatType(str, enum.Enum):
    STAFF = "staff"
    AUDITOR = "auditor"

class SubscriptionsStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TRIAL = "trial"

class SupplierDueDiligenceHumanRights(str, enum.Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    UNCHECKED = "unchecked"

class SupplierDueDiligenceEnvironment(str, enum.Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    UNCHECKED = "unchecked"

class SupplierDueDiligenceSafety(str, enum.Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    UNCHECKED = "unchecked"

class SupplierDueDiligenceEthics(str, enum.Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    UNCHECKED = "unchecked"

class SupplierDueDiligenceDataSecurity(str, enum.Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    UNCHECKED = "unchecked"

class SupplierDueDiligenceSupplyChain(str, enum.Enum):
    PASS = "pass"
    PARTIAL = "partial"
    FAIL = "fail"
    UNCHECKED = "unchecked"

class SupplierDueDiligenceOverallStatus(str, enum.Enum):
    VAL_0 = "완료"
    VAL_1 = "진행중"
    VAL_2 = "부적합발견"
    VAL_3 = "미실시"

class TenantsCbType(str, enum.Enum):
    CERTIFICATION = "certification"
    EDUCATION = "education"
    CONSULTING = "consulting"
    OTHER = "other"

class TenantsPlanType(str, enum.Enum):
    BASIC = "basic"
    PRO = "pro"
    ENTERPRISE = "enterprise"

class TenantsStatus(str, enum.Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    EXPIRED = "expired"

class UsersMemberType(str, enum.Enum):
    PERSONAL = "personal"
    COMPANY_REP = "company_rep"
    CB_REP = "cb_rep"
    STAFF = "staff"

class UsersRole(str, enum.Enum):
    PLATFORM_ADMIN = "platform_admin"
    CB_ADMIN = "cb_admin"
    CB_STAFF = "cb_staff"
    CB_MANAGER = "cb_manager"
    CB_REVIEWER = "cb_reviewer"
    AUDITOR = "auditor"
    CLIENT_ADMIN = "client_admin"
    CLIENT_STAFF = "client_staff"
