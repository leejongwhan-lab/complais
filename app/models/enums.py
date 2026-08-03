"""Auto-generated enum types from MariaDB schema."""

import enum

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
    SENIOR = "senior"
    VERIFIER = "verifier"

class AuditorApprovalHistoryToGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    SENIOR = "senior"
    VERIFIER = "verifier"

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

class AuditorCbMembershipsApplyGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    SENIOR = "senior"
    VERIFIER = "verifier"

class AuditorCbMembershipsApprovedGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    SENIOR = "senior"
    VERIFIER = "verifier"

class AuditorConflictHistoryConflictType(str, enum.Enum):
    EMPLOYMENT = "employment"
    CONSULTING = "consulting"

class AuditorEducationsDegree(str, enum.Enum):
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
    SENIOR = "senior"
    VERIFIER = "verifier"

class AuditorGradeRequirementsFromGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    SENIOR = "senior"

class AuditorGradeRequirementsToGrade(str, enum.Enum):
    AUDITOR = "auditor"
    SENIOR = "senior"
    VERIFIER = "verifier"

class AuditorQualificationsGrade(str, enum.Enum):
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    SENIOR = "senior"
    VERIFIER = "verifier"

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
    SENIOR = "senior"
    VERIFIER = "verifier"

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
    TRAINEE = "trainee"
    AUDITOR = "auditor"
    SENIOR = "senior"
    VERIFIER = "verifier"

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
    SENIOR = "senior"
    VERIFIER = "verifier"
    LEAD_AUDITOR = "lead_auditor"
    TRAINEE = "trainee"

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
