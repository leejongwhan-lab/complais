"""Add cert_applications and cert_contracts tables

Revision ID: j0k1l2m3n4o5
Revises: i9j0k1l2m3n4
Create Date: 2026-08-04 18:33:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql


# revision identifiers, used by Alembic.
revision: str = "j0k1l2m3n4o5"
down_revision: Union[str, Sequence[str], None] = "i9j0k1l2m3n4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

contract_status_enum = sa.Enum("draft", "pending", "signed", "cancelled", name="contractstatus")


def upgrade() -> None:
    # --- 인증 신청서 ---
    op.create_table(
        "cert_applications",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # certification_bodies.id는 MySQL에서 INT UNSIGNED이므로 FK 타입을 정확히 맞춘다.
        sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False, comment="CB 멀티테넌시"),
        sa.Column("company_name", sa.String(length=150), nullable=False, comment="피심사 기업명"),
        sa.Column("business_no", sa.String(length=20), nullable=True, comment="사업자등록번호"),
        sa.Column("applicant_name", sa.String(length=50), nullable=False, comment="신청인"),
        sa.Column("total_employees", sa.Integer(), nullable=True, server_default="0", comment="상시 근로자 수"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cb_id"], ["certification_bodies.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cert_applications_id"), "cert_applications", ["id"], unique=False)
    op.create_index(op.f("ix_cert_applications_cb_id"), "cert_applications", ["cb_id"], unique=False)
    op.create_index(op.f("ix_cert_applications_business_no"), "cert_applications", ["business_no"], unique=False)

    # --- 인증 심사 계약서 ---
    op.create_table(
        "cert_contracts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("cb_id", mysql.INTEGER(unsigned=True), nullable=False, comment="CB 멀티테넌시"),
        sa.Column("application_id", sa.Integer(), nullable=False),
        sa.Column("contract_no", sa.String(length=50), nullable=False, comment="계약번호 (예: CNT-2026-0801)"),
        sa.Column("audit_type", sa.String(length=30), nullable=False, comment="최초, 사후, 갱신 등"),
        sa.Column("total_md", sa.Numeric(5, 2), nullable=False, comment="산정된 총 MD"),
        sa.Column("total_amount", sa.Numeric(12, 0), nullable=True, server_default="0", comment="계약 금액"),
        sa.Column("contract_date", sa.Date(), nullable=False, comment="계약 체결일"),
        sa.Column("status", contract_status_enum, nullable=False, server_default="draft"),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cb_id"], ["certification_bodies.id"]),
        sa.ForeignKeyConstraint(["application_id"], ["cert_applications.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contract_no"),
    )
    op.create_index(op.f("ix_cert_contracts_id"), "cert_contracts", ["id"], unique=False)
    op.create_index(op.f("ix_cert_contracts_cb_id"), "cert_contracts", ["cb_id"], unique=False)
    op.create_index(op.f("ix_cert_contracts_contract_no"), "cert_contracts", ["contract_no"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_cert_contracts_contract_no"), table_name="cert_contracts")
    op.drop_index(op.f("ix_cert_contracts_cb_id"), table_name="cert_contracts")
    op.drop_index(op.f("ix_cert_contracts_id"), table_name="cert_contracts")
    op.drop_table("cert_contracts")

    op.drop_index(op.f("ix_cert_applications_business_no"), table_name="cert_applications")
    op.drop_index(op.f("ix_cert_applications_cb_id"), table_name="cert_applications")
    op.drop_index(op.f("ix_cert_applications_id"), table_name="cert_applications")
    op.drop_table("cert_applications")

    contract_status_enum.drop(op.get_bind(), checkfirst=True)
