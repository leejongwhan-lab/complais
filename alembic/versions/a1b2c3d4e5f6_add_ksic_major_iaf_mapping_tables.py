"""Add normalized ksic/iaf/major master and mapping tables

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
    # --- 마스터 테이블 ---
    op.create_table(
        "ksic_codes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False, comment="KSIC 코드 (예: 26110, 6202)"),
        sa.Column("name_ko", sa.String(length=150), nullable=False, comment="국문 업종명"),
        sa.Column("name_en", sa.String(length=150), nullable=True, comment="영문 업종명"),
        sa.Column("digit_level", sa.Integer(), nullable=True, comment="코드 자릿수 (3: 소분류, 4: 세분류, 5: 세세분류)"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_ksic_codes_id"), "ksic_codes", ["id"], unique=False)
    op.create_index(op.f("ix_ksic_codes_code"), "ksic_codes", ["code"], unique=True)

    op.create_table(
        "iaf_codes",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=10), nullable=False, comment="IAF 코드 (예: 19, 19B, 33)"),
        sa.Column("name_ko", sa.String(length=100), nullable=False, comment="국문 범주명"),
        sa.Column("name_en", sa.String(length=100), nullable=True, comment="영문 범주명"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_iaf_codes_id"), "iaf_codes", ["id"], unique=False)
    op.create_index(op.f("ix_iaf_codes_code"), "iaf_codes", ["code"], unique=True)

    op.create_table(
        "majors",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False, comment="전공학과명"),
        sa.Column("category", sa.String(length=50), nullable=True, comment="계열 (예: 이공계열, 인문사회계열)"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_majors_id"), "majors", ["id"], unique=False)
    op.create_index(op.f("ix_majors_name"), "majors", ["name"], unique=True)

    # --- 매핑 테이블 ---
    op.create_table(
        "ksic_iaf_mappings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ksic_id", sa.BigInteger(), nullable=False),
        sa.Column("iaf_id", sa.BigInteger(), nullable=False),
        sa.Column("qms_complexity", sa.String(length=20), nullable=True, comment="QMS 복잡도 (높음/중간/낮음/제한)"),
        sa.Column("ems_complexity", sa.String(length=20), nullable=True, comment="EMS 복잡도"),
        sa.Column("ohsms_complexity", sa.String(length=20), nullable=True, comment="OHSMS 복잡도"),
        sa.ForeignKeyConstraint(["ksic_id"], ["ksic_codes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["iaf_id"], ["iaf_codes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ksic_iaf_mappings_id"), "ksic_iaf_mappings", ["id"], unique=False)

    op.create_table(
        "major_iaf_mappings",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("major_id", sa.BigInteger(), nullable=False),
        sa.Column("iaf_id", sa.BigInteger(), nullable=False),
        sa.Column("degree_level", sa.String(length=20), nullable=True, comment="학위 기준 (BACHELOR_4Y, MASTER, 등)"),
        sa.Column("is_mandatory", sa.Boolean(), nullable=True, comment="전공 인정 필수 여부"),
        sa.Column("extra_exp_years", sa.Integer(), nullable=True, comment="단서조항: 추가 실무경력 필요 년수"),
        sa.Column("requires_committee", sa.Boolean(), nullable=True, comment="단서조항: 자격인증위원회 심의 필요 여부"),
        sa.Column("notes", sa.Text(), nullable=True, comment="비고 및 부속서 2 근거 조항"),
        sa.ForeignKeyConstraint(["major_id"], ["majors.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["iaf_id"], ["iaf_codes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_major_iaf_mappings_id"), "major_iaf_mappings", ["id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_major_iaf_mappings_id"), table_name="major_iaf_mappings")
    op.drop_table("major_iaf_mappings")

    op.drop_index(op.f("ix_ksic_iaf_mappings_id"), table_name="ksic_iaf_mappings")
    op.drop_table("ksic_iaf_mappings")

    op.drop_index(op.f("ix_majors_name"), table_name="majors")
    op.drop_index(op.f("ix_majors_id"), table_name="majors")
    op.drop_table("majors")

    op.drop_index(op.f("ix_iaf_codes_code"), table_name="iaf_codes")
    op.drop_index(op.f("ix_iaf_codes_id"), table_name="iaf_codes")
    op.drop_table("iaf_codes")

    op.drop_index(op.f("ix_ksic_codes_code"), table_name="ksic_codes")
    op.drop_index(op.f("ix_ksic_codes_id"), table_name="ksic_codes")
    op.drop_table("ksic_codes")
