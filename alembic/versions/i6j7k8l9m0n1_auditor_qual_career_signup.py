"""auditor qualifications + career temp columns for signup/affiliation

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2026-08-07

Additive only:
- auditor_qualifications: nullable cb_id, cert_body_name, cert_no, iaf_codes, major_name, membership_id
- auditor_work_experiences: is_temporary, duties
- master_majors: lightweight major name suggestions (optional master)
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "i6j7k8l9m0n1"
down_revision = "h5i6j7k8l9m0"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def _is_nullable(table: str, column: str) -> bool:
    for c in inspect(op.get_bind()).get_columns(table):
        if c["name"] == column:
            return bool(c.get("nullable"))
    return True


def upgrade() -> None:
    bind = op.get_bind()

    if _has_table("auditor_qualifications"):
        # Identity signup may store quals before CB affiliation
        if _has_column("auditor_qualifications", "cb_id") and not _is_nullable(
            "auditor_qualifications", "cb_id"
        ):
            try:
                op.alter_column(
                    "auditor_qualifications",
                    "cb_id",
                    existing_type=sa.Integer(),
                    nullable=True,
                    comment="자격 관리 CB (Identity 신청 시 NULL 허용)",
                )
            except Exception:
                bind.execute(
                    text(
                        "ALTER TABLE auditor_qualifications "
                        "MODIFY COLUMN cb_id INT NULL COMMENT '자격 관리 CB (Identity 신청 시 NULL 허용)'"
                    )
                )

        if not _has_column("auditor_qualifications", "cert_body_name"):
            op.add_column(
                "auditor_qualifications",
                sa.Column(
                    "cert_body_name",
                    sa.String(100),
                    nullable=True,
                    comment="자격 발급기관 (KAR/IRCA/Exemplar Global 등)",
                ),
            )
        if not _has_column("auditor_qualifications", "cert_no"):
            op.add_column(
                "auditor_qualifications",
                sa.Column(
                    "cert_no",
                    sa.String(100),
                    nullable=True,
                    comment="자격증 번호",
                ),
            )
        if not _has_column("auditor_qualifications", "iaf_codes"):
            op.add_column(
                "auditor_qualifications",
                sa.Column(
                    "iaf_codes",
                    sa.JSON(),
                    nullable=True,
                    comment="신청/보유 IAF 코드 목록",
                ),
            )
        if not _has_column("auditor_qualifications", "major_name"):
            op.add_column(
                "auditor_qualifications",
                sa.Column(
                    "major_name",
                    sa.String(200),
                    nullable=True,
                    comment="관련 전공학과명",
                ),
            )
        if not _has_column("auditor_qualifications", "membership_id"):
            op.add_column(
                "auditor_qualifications",
                sa.Column(
                    "membership_id",
                    sa.Integer(),
                    nullable=True,
                    comment="auditor_cb_memberships.id (소속 신청 연계)",
                ),
            )

    if _has_table("auditor_work_experiences"):
        if not _has_column("auditor_work_experiences", "is_temporary"):
            op.add_column(
                "auditor_work_experiences",
                sa.Column(
                    "is_temporary",
                    sa.Boolean(),
                    nullable=False,
                    server_default=sa.text("0"),
                    comment="미등록 기업 직접입력(임시) 여부",
                ),
            )
        if not _has_column("auditor_work_experiences", "duties"):
            op.add_column(
                "auditor_work_experiences",
                sa.Column(
                    "duties",
                    sa.Text(),
                    nullable=True,
                    comment="담당 업무",
                ),
            )

    if not _has_table("master_majors"):
        op.create_table(
            "master_majors",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(200), nullable=False, comment="전공학과명"),
            sa.Column("category", sa.String(100), nullable=True, comment="계열/분류"),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.PrimaryKeyConstraint("id"),
            mysql_charset="utf8mb4",
        )
        op.create_index("ix_master_majors_name", "master_majors", ["name"])

        seeds = [
            ("화학공학", "공학"),
            ("기계공학", "공학"),
            ("전기전자공학", "공학"),
            ("컴퓨터공학", "공학"),
            ("산업공학", "공학"),
            ("토목공학", "공학"),
            ("환경공학", "공학"),
            ("식품공학", "공학"),
            ("생명공학", "공학"),
            ("재료공학", "공학"),
            ("경영학", "상경"),
            ("회계학", "상경"),
            ("경제학", "상경"),
            ("화학", "자연"),
            ("물리학", "자연"),
            ("생물학", "자연"),
            ("간호학", "보건"),
            ("약학", "보건"),
            ("식품영양학", "보건"),
            ("안전공학", "공학"),
        ]
        for name, cat in seeds:
            bind.execute(
                text(
                    "INSERT INTO master_majors (name, category, is_active) "
                    "VALUES (:n, :c, 1)"
                ),
                {"n": name, "c": cat},
            )


def downgrade() -> None:
    if _has_table("master_majors"):
        op.drop_index("ix_master_majors_name", table_name="master_majors")
        op.drop_table("master_majors")

    if _has_table("auditor_work_experiences"):
        if _has_column("auditor_work_experiences", "duties"):
            op.drop_column("auditor_work_experiences", "duties")
        if _has_column("auditor_work_experiences", "is_temporary"):
            op.drop_column("auditor_work_experiences", "is_temporary")

    if _has_table("auditor_qualifications"):
        for col in (
            "membership_id",
            "major_name",
            "iaf_codes",
            "cert_no",
            "cert_body_name",
        ):
            if _has_column("auditor_qualifications", col):
                op.drop_column("auditor_qualifications", col)
