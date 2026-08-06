"""Add auditor career, IAF qualification, and application tables

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-04 16:55:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- 심사원 실무경력 (KSIC/IAF 정규화 매핑) ---
    op.create_table(
        "auditor_career_records",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        # auditors.id는 MySQL에서 INT UNSIGNED이므로 FK 타입을 정확히 맞춘다.
        sa.Column("auditor_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False, comment="근무/컨설팅 기업명"),
        sa.Column("position", sa.String(length=100), nullable=True, comment="직위/역할"),
        sa.Column("ksic_id", sa.BigInteger(), nullable=True, comment="해당 업종 KSIC 마스터 FK"),
        sa.Column("iaf_id", sa.BigInteger(), nullable=True, comment="환산된 IAF 코드 마스터 FK"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=True, comment="현재 재직/진행 여부"),
        sa.Column("career_months", sa.Integer(), nullable=True, comment="경력 개월 수 (자동 계산 캐시)"),
        sa.Column("is_verified", sa.Boolean(), nullable=True, comment="증빙 확인 여부"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["auditor_id"], ["auditors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ksic_id"], ["ksic_codes.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["iaf_id"], ["iaf_codes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditor_career_records_id"), "auditor_career_records", ["id"], unique=False)
    op.create_index(op.f("ix_auditor_career_records_auditor_id"), "auditor_career_records", ["auditor_id"], unique=False)

    # --- 심사원 IAF 코드별 보유 자격 ---
    op.create_table(
        "auditor_iaf_qualifications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("auditor_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("iaf_id", sa.BigInteger(), nullable=False),
        sa.Column("source_type", sa.String(length=20), nullable=False, comment="자격 취득 근거 (MAJOR/CAREER/COMMITTEE/TRAINING 등)"),
        sa.Column("source_major_id", sa.BigInteger(), nullable=True, comment="전공 기반 취득 시 근거 전공 FK"),
        sa.Column("source_career_id", sa.BigInteger(), nullable=True, comment="경력 기반 취득 시 근거 경력 FK"),
        sa.Column("grade", sa.String(length=50), nullable=True, comment="심사원 등급 (Trainee/Auditor/Lead 등)"),
        sa.Column("granted_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["auditor_id"], ["auditors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["iaf_id"], ["iaf_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["source_major_id"], ["majors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["source_career_id"], ["auditor_career_records.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditor_iaf_qualifications_id"), "auditor_iaf_qualifications", ["id"], unique=False)
    op.create_index(op.f("ix_auditor_iaf_qualifications_auditor_id"), "auditor_iaf_qualifications", ["auditor_id"], unique=False)
    op.create_index(op.f("ix_auditor_iaf_qualifications_iaf_id"), "auditor_iaf_qualifications", ["iaf_id"], unique=False)

    # --- 심사원 신규/확대 IAF 자격 신청서 ---
    op.create_table(
        "audit_applications",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("auditor_id", mysql.INTEGER(unsigned=True), nullable=False),
        sa.Column("iaf_id", sa.BigInteger(), nullable=False),
        sa.Column("application_type", sa.String(length=20), nullable=False, comment="신청 유형 (NEW=신규자격, EXPAND=자격확대, RENEWAL=갱신)"),
        sa.Column("career_id", sa.BigInteger(), nullable=True, comment="근거 경력"),
        sa.Column("major_id", sa.BigInteger(), nullable=True, comment="근거 전공"),
        sa.Column("status", sa.String(length=20), nullable=True, comment="PENDING/APPROVED/REJECTED/COMMITTEE_REVIEW"),
        sa.Column("requires_committee", sa.Boolean(), nullable=True, comment="자격인증위원회 심의 필요 여부 (부속서 2 단서조항)"),
        sa.Column("reason", sa.Text(), nullable=True, comment="신청 사유/자기소개"),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(length=50), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("resulting_qualification_id", sa.BigInteger(), nullable=True, comment="승인 시 생성된 자격 레코드"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["auditor_id"], ["auditors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["iaf_id"], ["iaf_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["career_id"], ["auditor_career_records.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["major_id"], ["majors.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["resulting_qualification_id"], ["auditor_iaf_qualifications.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_applications_id"), "audit_applications", ["id"], unique=False)
    op.create_index(op.f("ix_audit_applications_auditor_id"), "audit_applications", ["auditor_id"], unique=False)
    op.create_index(op.f("ix_audit_applications_iaf_id"), "audit_applications", ["iaf_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_applications_iaf_id"), table_name="audit_applications")
    op.drop_index(op.f("ix_audit_applications_auditor_id"), table_name="audit_applications")
    op.drop_index(op.f("ix_audit_applications_id"), table_name="audit_applications")
    op.drop_table("audit_applications")

    op.drop_index(op.f("ix_auditor_iaf_qualifications_iaf_id"), table_name="auditor_iaf_qualifications")
    op.drop_index(op.f("ix_auditor_iaf_qualifications_auditor_id"), table_name="auditor_iaf_qualifications")
    op.drop_index(op.f("ix_auditor_iaf_qualifications_id"), table_name="auditor_iaf_qualifications")
    op.drop_table("auditor_iaf_qualifications")

    op.drop_index(op.f("ix_auditor_career_records_auditor_id"), table_name="auditor_career_records")
    op.drop_index(op.f("ix_auditor_career_records_id"), table_name="auditor_career_records")
    op.drop_table("auditor_career_records")
