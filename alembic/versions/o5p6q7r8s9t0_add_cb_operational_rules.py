"""add_cb_operational_rules

Revision ID: o5p6q7r8s9t0
Revises: n4o5p6q7r8s9
Create Date: 2026-08-05

ISO 17021-1 운용/수수료 규칙을 certification_bodies에서 분리한
cb_operational_rules 테이블을 생성하고 기존 값을 이관한다.
또한 CB 마스터에 intro / owner_user_id / phone 컬럼을 보강한다.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "o5p6q7r8s9t0"
down_revision = "n4o5p6q7r8s9"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in inspect(bind).get_columns(table)}
    return column in cols


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    return inspect(bind).has_table(table)


def upgrade() -> None:
    if not _has_column("certification_bodies", "phone"):
        op.add_column(
            "certification_bodies",
            sa.Column("phone", sa.String(length=50), nullable=True, comment="연락처(표시용, tel과 동기화 가능)"),
        )
    if not _has_column("certification_bodies", "intro"):
        op.add_column(
            "certification_bodies",
            sa.Column("intro", sa.Text(), nullable=True, comment="기관 소개"),
        )
    if not _has_column("certification_bodies", "owner_user_id"):
        op.add_column(
            "certification_bodies",
            sa.Column("owner_user_id", sa.Integer(), nullable=True, comment="최고 관리자 user_id"),
        )
    op.execute("UPDATE certification_bodies SET phone = tel WHERE phone IS NULL AND tel IS NOT NULL")

    if not _has_table("cb_operational_rules"):
        op.create_table(
            "cb_operational_rules",
            sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False),
            sa.Column(
                "doc_rule_contract",
                sa.String(length=100),
                nullable=True,
                server_default="CB-QE-{YYMMDD}-{SEQ3}",
                comment="계약서 문서번호 규칙",
            ),
            sa.Column("doc_rule_report", sa.String(length=100), nullable=True, comment="보고서 규칙"),
            sa.Column("doc_rule_ncr", sa.String(length=100), nullable=True, comment="NCR 규칙"),
            sa.Column("fee_per_md", sa.Integer(), nullable=False, server_default="0", comment="M/D 당 기본 수수료"),
            sa.Column("fee_travel", sa.Integer(), nullable=False, server_default="0", comment="기본 출장비"),
            sa.Column("fee_cert", sa.Integer(), nullable=False, server_default="0", comment="기본 인증비"),
            sa.Column(
                "max_consecutive_audits",
                sa.Integer(),
                nullable=False,
                server_default="3",
                comment="동일 기업 연속 심사 제한 횟수",
            ),
            sa.Column(
                "impartiality_cycle_months",
                sa.Integer(),
                nullable=False,
                server_default="12",
                comment="공평성 검토 주기(개월)",
            ),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ),
            sa.ForeignKeyConstraint(["cb_id"], ["certification_bodies.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("cb_id"),
        )

    # 기존 CB의 문서/수수료 규칙을 분리 테이블로 이관 (이미 있으면 무시)
    op.execute(
        """
        INSERT IGNORE INTO cb_operational_rules (
            cb_id, doc_rule_contract, doc_rule_report, doc_rule_ncr,
            fee_per_md, fee_travel, fee_cert,
            max_consecutive_audits, impartiality_cycle_months
        )
        SELECT
            id,
            COALESCE(doc_rule_contract, 'CB-QE-{YYMMDD}-{SEQ3}'),
            doc_rule_report,
            doc_rule_ncr,
            COALESCE(CAST(fee_per_md AS SIGNED), 0),
            COALESCE(CAST(fee_travel AS SIGNED), 0),
            COALESCE(CAST(fee_cert AS SIGNED), 0),
            COALESCE(max_consecutive, 3),
            COALESCE(impartiality_cycle_months, 12)
        FROM certification_bodies
        """
    )


def downgrade() -> None:
    if _has_table("cb_operational_rules"):
        op.drop_table("cb_operational_rules")
    if _has_column("certification_bodies", "owner_user_id"):
        op.drop_column("certification_bodies", "owner_user_id")
    if _has_column("certification_bodies", "intro"):
        op.drop_column("certification_bodies", "intro")
    if _has_column("certification_bodies", "phone"):
        op.drop_column("certification_bodies", "phone")
