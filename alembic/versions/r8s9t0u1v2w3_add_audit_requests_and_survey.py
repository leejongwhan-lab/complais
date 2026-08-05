"""add audit_requests + company survey/cycle fields

Revision ID: r8s9t0u1v2w3
Revises: q7r8s9t0u1v2
Create Date: 2026-08-05

인증 신청 설문 이력(audit_requests) 및 기업(clients=companies)의
심사주기/최신 설문 스냅샷 컬럼을 추가한다.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

revision = "r8s9t0u1v2w3"
down_revision = "q7r8s9t0u1v2"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    # companies (= clients) 설문/주기 컬럼
    if _has_table("companies"):
        if not _has_column("companies", "audit_cycle_months"):
            op.add_column(
                "companies",
                sa.Column(
                    "audit_cycle_months",
                    sa.Integer(),
                    nullable=False,
                    server_default="12",
                    comment="기본 선호 심사 주기(6|12)",
                ),
            )
        if not _has_column("companies", "latest_survey_snapshot"):
            op.add_column(
                "companies",
                sa.Column(
                    "latest_survey_snapshot",
                    mysql.JSON(),
                    nullable=True,
                    comment="최신 확정 설문 응답 스냅샷",
                ),
            )

    if not _has_table("audit_requests"):
        op.create_table(
            "audit_requests",
            sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
            sa.Column(
                "company_id",
                mysql.INTEGER(unsigned=True),
                nullable=False,
                comment="신청 기업(clients)",
            ),
            sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column("applicant_user_id", sa.Integer(), nullable=True),
            sa.Column(
                "iso_standards",
                mysql.JSON(),
                nullable=False,
                comment='["ISO 9001","ISO 14001"]',
            ),
            sa.Column(
                "audit_type",
                sa.String(50),
                nullable=False,
                server_default="initial",
                comment="initial|surveillance|recertification|special",
            ),
            sa.Column(
                "audit_cycle_months",
                sa.Integer(),
                nullable=False,
                server_default="12",
                comment="6 또는 12",
            ),
            sa.Column(
                "survey_responses",
                mysql.JSON(),
                nullable=True,
                comment="공통+표준별 설문 응답",
            ),
            sa.Column("previous_request_id", sa.BigInteger(), nullable=True),
            sa.Column(
                "status",
                sa.String(30),
                nullable=False,
                server_default="submitted",
                comment="draft|submitted|under_review|completed|cancelled",
            ),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("submitted_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["company_id"],
                ["companies.id"],
                name="fk_audit_requests_company",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["cb_id"],
                ["certification_bodies.id"],
                name="fk_audit_requests_cb",
            ),
            sa.ForeignKeyConstraint(
                ["previous_request_id"],
                ["audit_requests.id"],
                name="fk_audit_requests_previous",
                ondelete="SET NULL",
            ),
            mysql_engine="InnoDB",
            mysql_charset="utf8mb4",
        )
        op.create_index("ix_audit_requests_company_id", "audit_requests", ["company_id"])
        op.create_index("ix_audit_requests_cb_id", "audit_requests", ["cb_id"])
        op.create_index("ix_audit_requests_status", "audit_requests", ["status"])
        op.create_index(
            "ix_audit_requests_previous_request_id",
            "audit_requests",
            ["previous_request_id"],
        )


def downgrade() -> None:
    if _has_table("audit_requests"):
        op.drop_table("audit_requests")
    if _has_table("companies"):
        if _has_column("companies", "latest_survey_snapshot"):
            op.drop_column("companies", "latest_survey_snapshot")
        if _has_column("companies", "audit_cycle_months"):
            op.drop_column("companies", "audit_cycle_months")
