"""Add ksic_iaf_mappings and major_iaf_mappings tables

Revision ID: a1b2c3d4e5f6
Revises: 11ab37321abd
Create Date: 2026-08-04 14:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "11ab37321abd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ksic_iaf_mappings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ksic_code", sa.String(length=10), nullable=False, comment="KSIC 코드 (예: 2611)"),
        sa.Column("iaf_code", sa.String(length=10), nullable=False, comment="IAF 코드 (예: 19B)"),
        sa.Column("iaf_name_ko", sa.String(length=100), nullable=False, comment="IAF 국문명"),
        sa.Column("iaf_name_en", sa.String(length=100), nullable=True, comment="IAF 영문명"),
        sa.Column("qms_complexity", sa.String(length=20), nullable=True, comment="QMS 복잡도 (높음/중간/낮음)"),
        sa.Column("ems_complexity", sa.String(length=20), nullable=True, comment="EMS 복잡도 (높음/중간/낮음/제한)"),
        sa.Column("ohsms_complexity", sa.String(length=20), nullable=True, comment="OHSMS 복잡도 (높음/중간/낮음)"),
        sa.Column("description", sa.Text(), nullable=True, comment="세부분류 및 비고"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ksic_iaf_mappings_id"), "ksic_iaf_mappings", ["id"], unique=False)
    op.create_index(op.f("ix_ksic_iaf_mappings_ksic_code"), "ksic_iaf_mappings", ["ksic_code"], unique=False)
    op.create_index(op.f("ix_ksic_iaf_mappings_iaf_code"), "ksic_iaf_mappings", ["iaf_code"], unique=False)

    op.create_table(
        "major_iaf_mappings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("major_name", sa.String(length=100), nullable=False, comment="전공학과명/키워드 (예: 기계공학)"),
        sa.Column("iaf_code", sa.String(length=10), nullable=False, comment="매핑/추천 IAF 코드 (예: 18)"),
        sa.Column("degree_level", sa.String(length=20), nullable=True, comment="요구 학력 수준"),
        sa.Column("is_mandatory", sa.Boolean(), nullable=True, comment="전공만으로 즉시 부여 가능 여부"),
        sa.Column("extra_exp_years", sa.Integer(), nullable=True, comment="추가 필수 실무경력 년수 (예: 의약/원자력 3년)"),
        sa.Column("requires_committee", sa.Boolean(), nullable=True, comment="자격인증위원회 심의 필요 여부 (예: 기타제조업 23번)"),
        sa.Column("notes", sa.Text(), nullable=True, comment="인정/제한 규정 요약 설명"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_major_iaf_mappings_id"), "major_iaf_mappings", ["id"], unique=False)
    op.create_index(op.f("ix_major_iaf_mappings_major_name"), "major_iaf_mappings", ["major_name"], unique=False)
    op.create_index(op.f("ix_major_iaf_mappings_iaf_code"), "major_iaf_mappings", ["iaf_code"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_major_iaf_mappings_iaf_code"), table_name="major_iaf_mappings")
    op.drop_index(op.f("ix_major_iaf_mappings_major_name"), table_name="major_iaf_mappings")
    op.drop_index(op.f("ix_major_iaf_mappings_id"), table_name="major_iaf_mappings")
    op.drop_table("major_iaf_mappings")

    op.drop_index(op.f("ix_ksic_iaf_mappings_iaf_code"), table_name="ksic_iaf_mappings")
    op.drop_index(op.f("ix_ksic_iaf_mappings_ksic_code"), table_name="ksic_iaf_mappings")
    op.drop_index(op.f("ix_ksic_iaf_mappings_id"), table_name="ksic_iaf_mappings")
    op.drop_table("ksic_iaf_mappings")
