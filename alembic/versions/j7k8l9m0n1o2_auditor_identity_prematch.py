"""ci_key + pre_registered_auditors for PortOne identity match

Revision ID: j7k8l9m0n1o2
Revises: i6j7k8l9m0n1
Create Date: 2026-08-07

Additive only — preserves companies/CBs.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text
import json

revision = "j7k8l9m0n1o2"
down_revision = "i6j7k8l9m0n1"
branch_labels = None
depends_on = None


def _has_table(table: str) -> bool:
    return inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    cols = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    return column in cols


def upgrade() -> None:
    bind = op.get_bind()

    if _has_table("users") and not _has_column("users", "ci_key"):
        op.add_column(
            "users",
            sa.Column(
                "ci_key",
                sa.String(128),
                nullable=True,
                comment="본인인증 CI (PortOne/Kakao/Naver)",
            ),
        )
        op.create_index("ix_users_ci_key", "users", ["ci_key"])

    if _has_table("auditors") and not _has_column("auditors", "ci_key"):
        op.add_column(
            "auditors",
            sa.Column(
                "ci_key",
                sa.String(128),
                nullable=True,
                comment="본인인증 CI (PortOne)",
            ),
        )
        op.create_index("ix_auditors_ci_key", "auditors", ["ci_key"])

    if not _has_table("pre_registered_auditors"):
        op.create_table(
            "pre_registered_auditors",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("phone", sa.String(50), nullable=True),
            sa.Column("ci_key", sa.String(128), nullable=True),
            sa.Column("email", sa.String(200), nullable=True),
            sa.Column("cb_id", sa.Integer(), nullable=True, comment="사전 배정 CB (선택)"),
            sa.Column("apply_grade", sa.String(50), nullable=True),
            sa.Column(
                "education_json",
                sa.JSON(),
                nullable=True,
                comment="학력 배열 JSON",
            ),
            sa.Column(
                "career_json",
                sa.JSON(),
                nullable=True,
                comment="경력 배열 JSON",
            ),
            sa.Column(
                "qualification_json",
                sa.JSON(),
                nullable=True,
                comment="자격 배열 JSON",
            ),
            sa.Column(
                "iaf_codes_json",
                sa.JSON(),
                nullable=True,
                comment="IAF 코드 목록 JSON",
            ),
            sa.Column("major_name", sa.String(200), nullable=True),
            sa.Column("memo", sa.Text(), nullable=True),
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("1"),
            ),
            sa.Column(
                "matched_user_id",
                sa.Integer(),
                nullable=True,
                comment="가입 매칭된 users.id",
            ),
            sa.Column(
                "uploaded_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"),
            ),
            sa.PrimaryKeyConstraint("id"),
            mysql_charset="utf8mb4",
        )
        op.create_index("ix_pre_reg_auditors_ci_key", "pre_registered_auditors", ["ci_key"])
        op.create_index("ix_pre_reg_auditors_name_phone", "pre_registered_auditors", ["name", "phone"])

        seeds = [
            {
                "name": "테스트심사원",
                "phone": "01012345678",
                "ci_key": "MOCK-CI-TEST-001",
                "email": "prematch.auditor1@example.com",
                "apply_grade": "auditor",
                "major_name": "화학공학",
                "education_json": [
                    {
                        "school_name": "한국대학교",
                        "degree": "bachelor",
                        "major": "화학공학",
                        "graduated_at": "2015-02-01",
                    }
                ],
                "career_json": [
                    {
                        "company_name": "테스트제조(주)",
                        "biz_no": "1234567890",
                        "position": "품질팀",
                        "start_date": "2016-03-01",
                        "end_date": "2022-12-31",
                        "is_current": False,
                        "is_temporary": True,
                        "duties": "ISO 9001 내부심사 및 품질관리",
                    }
                ],
                "qualification_json": [
                    {
                        "standard_code": "QMS",
                        "cert_body_name": "KAR",
                        "cert_no": "KAR-QMS-TEST-001",
                        "auditor_grade": "auditor",
                        "iaf_codes": ["14", "19"],
                        "major_name": "화학공학",
                    },
                    {
                        "standard_code": "EMS",
                        "cert_body_name": "IRCA",
                        "cert_no": "IRCA-EMS-TEST-001",
                        "auditor_grade": "lead_auditor",
                        "iaf_codes": ["14"],
                        "major_name": "화학공학",
                    },
                ],
                "iaf_codes_json": ["14", "19", "28"],
                "memo": "smoke seed — mock CI flow",
            },
            {
                "name": "나검증",
                "phone": "01098765432",
                "ci_key": "MOCK-CI-TEST-002",
                "email": "prematch.auditor2@example.com",
                "apply_grade": "lead_auditor",
                "major_name": "환경공학",
                "education_json": [
                    {
                        "school_name": "서울과학기술대학교",
                        "degree": "master",
                        "major": "환경공학",
                        "graduated_at": "2018-08-01",
                    }
                ],
                "career_json": [
                    {
                        "company_name": "그린컨설팅",
                        "start_date": "2019-01-01",
                        "is_current": True,
                        "is_temporary": True,
                        "duties": "환경경영시스템 컨설팅",
                    }
                ],
                "qualification_json": [
                    {
                        "standard_code": "EMS",
                        "cert_body_name": "KAR",
                        "cert_no": "KAR-EMS-TEST-002",
                        "auditor_grade": "lead_auditor",
                        "iaf_codes": ["01", "39"],
                        "major_name": "환경공학",
                    }
                ],
                "iaf_codes_json": ["01", "39"],
                "memo": "smoke seed — name+phone match",
            },
        ]
        for s in seeds:
            bind.execute(
                text(
                    """
                    INSERT INTO pre_registered_auditors
                    (name, phone, ci_key, email, apply_grade, major_name,
                     education_json, career_json, qualification_json, iaf_codes_json,
                     memo, is_active, uploaded_at, created_at, updated_at)
                    VALUES
                    (:name, :phone, :ci_key, :email, :apply_grade, :major_name,
                     :education_json, :career_json, :qualification_json, :iaf_codes_json,
                     :memo, 1, UTC_TIMESTAMP(), UTC_TIMESTAMP(), UTC_TIMESTAMP())
                    """
                ),
                {
                    "name": s["name"],
                    "phone": s["phone"],
                    "ci_key": s["ci_key"],
                    "email": s["email"],
                    "apply_grade": s["apply_grade"],
                    "major_name": s["major_name"],
                    "education_json": json.dumps(s["education_json"], ensure_ascii=False),
                    "career_json": json.dumps(s["career_json"], ensure_ascii=False),
                    "qualification_json": json.dumps(s["qualification_json"], ensure_ascii=False),
                    "iaf_codes_json": json.dumps(s["iaf_codes_json"], ensure_ascii=False),
                    "memo": s["memo"],
                },
            )


def downgrade() -> None:
    if _has_table("pre_registered_auditors"):
        op.drop_index("ix_pre_reg_auditors_name_phone", table_name="pre_registered_auditors")
        op.drop_index("ix_pre_reg_auditors_ci_key", table_name="pre_registered_auditors")
        op.drop_table("pre_registered_auditors")

    if _has_table("auditors") and _has_column("auditors", "ci_key"):
        op.drop_index("ix_auditors_ci_key", table_name="auditors")
        op.drop_column("auditors", "ci_key")

    if _has_table("users") and _has_column("users", "ci_key"):
        op.drop_index("ix_users_ci_key", table_name="users")
        op.drop_column("users", "ci_key")
