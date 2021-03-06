"""empty message

Revision ID: 68f3f3555648
Revises: 07d770cf0052
Create Date: 2020-01-25 12:43:24.716991

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '68f3f3555648'
down_revision = '07d770cf0052'
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def upgrade_users():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_users():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('mobile_number_update_request', sa.Column('cust_no', mysql.VARCHAR(length=15), nullable=True))
    op.add_column('email_address_update_request', sa.Column('cust_no', mysql.VARCHAR(length=15), nullable=True))
    # ### end Alembic commands ###


def upgrade_assets():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_assets():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def upgrade_connection():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_connection():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def upgrade_recharge():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_recharge():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('lco_transaction_entry')
    # ### end Alembic commands ###


def upgrade_ticket():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_ticket():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def upgrade_softphone():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_softphone():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('idx_pname', 'tbl_series_number_generator', ['softphone_no'], unique=False)
    op.create_table('tbl_user',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=False, nullable=False),
    sa.Column('name', mysql.VARCHAR(length=700), nullable=True),
    sa.Column('uid', mysql.VARCHAR(length=700), nullable=True),
    sa.Column('pass', mysql.VARCHAR(length=700), nullable=True),
    sa.Column('priviledge', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.Column('dept', mysql.VARCHAR(length=100), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='latin1',
    mysql_engine='InnoDB'
    )
    op.create_table('tbl_category_master',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.Column('category_id', mysql.VARCHAR(length=15), nullable=True),
    sa.Column('category_type', mysql.VARCHAR(length=15), nullable=True),
    sa.Column('category_status', mysql.VARCHAR(length=15), nullable=True),
    sa.Column('rate', mysql.DECIMAL(precision=10, scale=2), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='latin1',
    mysql_engine='InnoDB'
    )
    op.create_table('tbl_block',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.Column('softphone', mysql.VARCHAR(length=100), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='latin1',
    mysql_engine='InnoDB'
    )
    op.create_table('tbl_series_master',
    sa.Column('id', mysql.INTEGER(display_width=10), autoincrement=True, nullable=False),
    sa.Column('series_no', mysql.INTEGER(display_width=10), autoincrement=False, nullable=True),
    sa.Column('series_from', mysql.INTEGER(display_width=10), autoincrement=False, nullable=True),
    sa.Column('series_to', mysql.INTEGER(display_width=10), autoincrement=False, nullable=True),
    sa.Column('series_status', mysql.VARCHAR(length=15), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='latin1',
    mysql_engine='InnoDB'
    )
    # ### end Alembic commands ###


def upgrade_voucher():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('tbl_ott_provider', sa.Column('ott_provider_pkg_name', sa.String(length=50), nullable=False))
    op.alter_column('tbl_ott_provider', 'ott_provider_app_name',
               existing_type=mysql.VARCHAR(length=50),
               nullable=False)
    # ### end Alembic commands ###


def downgrade_voucher():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('tbl_ott_provider', 'ott_provider_app_name',
               existing_type=mysql.VARCHAR(length=50),
               nullable=True)
    op.drop_column('tbl_ott_provider', 'ott_provider_pkg_name')
    # ### end Alembic commands ###


def upgrade_lco():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_lco():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

