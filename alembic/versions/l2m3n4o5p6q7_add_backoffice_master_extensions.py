"""add_backoffice_master_extensions

Revision ID: l2m3n4o5p6q7
Revises: k1l2m3n4o5p6
Create Date: 2026-08-05

백오피스 마스터(기업/심사원/인증기관) 요구사항을 기존 companies/auditors/
certification_bodies 및 관련 서브 테이블(company_sites, kar_qualifications,
kar_cpd_records, auditor_consulting_experiences)에 컬럼을 추가하는 방식으로 반영한다
(기존 FK/relationship을 깨지 않기 위해 신규 병렬 테이블을 만들지 않음).

추가로 대응 개념이 없는 순수 신규 서브 엔티티 4종
(company_staff_members, company_audit_history_records,
auditor_experience_records, cb_staff_members)을 신규 생성한다.

companies/auditors의 향후 채번을 100001/10001부터 시작하도록 AUTO_INCREMENT를 조정한다
(기존 데이터의 id는 변경되지 않는다).
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "l2m3n4o5p6q7"
down_revision = "k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 주의: MySQL non-transactional DDL로 이전 적용 시도에서 아래 컬럼들은 이미 반영됨
    # (companies.*, auditors 확장 11컬럼, certification_bodies 확장, company_sites.work_type,
    #  auditor_consulting_experiences.biz_no/consulting_type, kar_qualifications.renewal_date).
    # kar_qualifications에는 고아 auditor_id(2,4)가 있어 FK를 추가하지 않는다.
    # 이 upgrade()는 남은 DDL만 실행한다.

    # --- kar_cpd_records 확장 (CPD) + FK 추가 ---
    op.add_column("kar_cpd_records", sa.Column("is_fulfilled", sa.Boolean(), nullable=True, comment="CPD 이수 요건 충족 여부"))
    op.create_foreign_key(
        "fk_kar_cpd_records_auditor", "kar_cpd_records", "auditors", ["auditor_id"], ["id"], ondelete="CASCADE"
    )

    # --- 신규 서브 엔티티 테이블 ---
    op.create_table(
        "company_staff_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("staff_name", sa.String(length=50), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("position", sa.String(length=50), nullable=True),
        sa.Column("mobile", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_company_staff_members_company_id"), "company_staff_members", ["company_id"], unique=False)

    op.create_table(
        "company_audit_history_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("company_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("initial_cert_date", sa.Date(), nullable=True, comment="최초인증일"),
        sa.Column("surveillance_1_date", sa.Date(), nullable=True, comment="1차 사후심사일"),
        sa.Column("surveillance_2_date", sa.Date(), nullable=True, comment="2차 사후심사일"),
        sa.Column("renewal_date", sa.Date(), nullable=True, comment="갱신심사일"),
        sa.Column("manager_auditor", sa.String(length=50), nullable=True, comment="담당 심사원명"),
        sa.Column("transfer_history", sa.Text(), nullable=True, comment="담당자 인수인계 내역"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["company_id"], ["companies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_company_audit_history_records_company_id"), "company_audit_history_records", ["company_id"], unique=False)

    op.create_table(
        "auditor_experience_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("auditor_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("period_year", sa.Integer(), nullable=False, comment="통계 연도"),
        sa.Column("initial_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("surveillance_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("renewal_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_audit_days", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["auditor_id"], ["auditors.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditor_experience_records_auditor_id"), "auditor_experience_records", ["auditor_id"], unique=False)

    op.create_table(
        "cb_staff_members",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("emp_no", sa.String(length=30), nullable=True, comment="사번"),
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("position", sa.String(length=50), nullable=True),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.Column("mobile", sa.String(length=20), nullable=True),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("task_type", sa.String(length=50), nullable=True, comment="담당 업무 유형"),
        sa.Column("role_level", sa.String(length=20), nullable=True, comment="직급/권한 레벨"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.ForeignKeyConstraint(["cb_id"], ["certification_bodies.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cb_staff_members_cb_id"), "cb_staff_members", ["cb_id"], unique=False)

    # --- 9. 채번 시작값 조정 (기존 데이터 id는 변경되지 않고, 다음 신규 insert부터 적용) ---
    op.execute("ALTER TABLE companies AUTO_INCREMENT = 100001")
    op.execute("ALTER TABLE auditors AUTO_INCREMENT = 10001")


def downgrade() -> None:
    op.drop_table("cb_staff_members")
    op.drop_table("auditor_experience_records")
    op.drop_table("company_audit_history_records")
    op.drop_table("company_staff_members")

    op.drop_constraint("fk_kar_cpd_records_auditor", "kar_cpd_records", type_="foreignkey")
    op.drop_column("kar_cpd_records", "is_fulfilled")

    op.drop_constraint("fk_kar_qualifications_auditor", "kar_qualifications", type_="foreignkey")
    op.drop_column("kar_qualifications", "renewal_date")

    op.drop_column("auditor_consulting_experiences", "consulting_type")
    op.drop_column("auditor_consulting_experiences", "biz_no")

    op.drop_column("company_sites", "work_type")

    for col in (
        "tax_email", "evaluation_score", "status", "expire_date", "iaf_scopes",
        "accredited_standards", "accreditation_no", "stamp_url", "accreditation_body",
        "accreditation_country", "accreditation_region",
    ):
        op.drop_column("certification_bodies", col)

    for col in (
        "subcontract_agreed", "security_pledge_agreed", "commission_type", "cb_affiliation",
        "total_working_days", "career_summary", "major", "school_name", "education_level",
        "income_type", "rrn_hash",
    ):
        op.drop_column("auditors", col)

    # companies 컬럼은 upgrade()에서 추가하지 않으므로(이미 적용된 상태) downgrade에서도 건드리지 않는다.
