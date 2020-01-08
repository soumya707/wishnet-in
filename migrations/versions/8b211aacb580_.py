"""empty message

Revision ID: 8b211aacb580
Revises: fde9d81e9e1f
Create Date: 2020-01-04 22:36:35.258839

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8b211aacb580'
down_revision = 'fde9d81e9e1f'
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
    op.add_column('customer_info', sa.Column('using_wishtalk', mysql.VARCHAR(length=3), nullable=True))
    op.alter_column('customer_info', 'user_name',
               existing_type=mysql.VARCHAR(length=100),
               nullable=True)
    op.alter_column('customer_info', 'ip_addr',
               existing_type=mysql.VARCHAR(length=100),
               nullable=True)
    op.alter_column('customer_info', 'installation_address',
               existing_type=mysql.VARCHAR(length=500),
               nullable=True)
    op.alter_column('customer_info', 'customer_no',
               existing_type=mysql.VARCHAR(length=20),
               nullable=True)
    op.alter_column('customer_info', 'customer_name',
               existing_type=mysql.VARCHAR(length=400),
               nullable=True)
    op.alter_column('customer_info', 'billing_address',
               existing_type=mysql.VARCHAR(length=500),
               nullable=True)
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
    op.add_column('tariff_info', sa.Column('ott_package_codes', sa.String(length=500), nullable=True))
    # ### end Alembic commands ###


def downgrade_recharge():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('tariff_info', 'ott_package_codes')
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
    # ### end Alembic commands ###


def upgrade_voucher():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_voucher():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
