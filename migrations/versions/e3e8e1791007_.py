"""empty message

Revision ID: e3e8e1791007
Revises: 360effe62bbe
Create Date: 2019-12-09 11:42:24.322646

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'e3e8e1791007'
down_revision = '360effe62bbe'
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
    op.alter_column('customer_info', 'customer_name',
               existing_type=mysql.VARCHAR(length=400),
               nullable=False)
    op.alter_column('customer_info', 'customer_no',
               existing_type=mysql.VARCHAR(length=20),
               nullable=False)
    op.alter_column('customer_info', 'ip_addr',
               existing_type=mysql.VARCHAR(length=100),
               nullable=False)
    op.alter_column('customer_info', 'user_name',
               existing_type=mysql.VARCHAR(length=100),
               nullable=False)
    op.alter_column('customer_info', 'using_wishtalk',
               existing_type=mysql.VARCHAR(length=3),
               nullable=False)
    op.alter_column('customer_info', 'zone_id',
               existing_type=mysql.VARCHAR(length=50),
               nullable=False)
    # ### end Alembic commands ###


def downgrade_users():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('customer_info', 'zone_id',
               existing_type=mysql.VARCHAR(length=50),
               nullable=True)
    op.alter_column('customer_info', 'using_wishtalk',
               existing_type=mysql.VARCHAR(length=3),
               nullable=True)
    op.alter_column('customer_info', 'user_name',
               existing_type=mysql.VARCHAR(length=100),
               nullable=True)
    op.alter_column('customer_info', 'ip_addr',
               existing_type=mysql.VARCHAR(length=100),
               nullable=True)
    op.alter_column('customer_info', 'customer_no',
               existing_type=mysql.VARCHAR(length=20),
               nullable=True)
    op.alter_column('customer_info', 'customer_name',
               existing_type=mysql.VARCHAR(length=400),
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
    pass
    # ### end Alembic commands ###


def downgrade_recharge():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
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
    op.drop_table('tbl_series_master')
    op.drop_table('tbl_user')
    op.drop_table('tbl_category_master')
    op.drop_index('idx_pname', table_name='tbl_series_number_generator')
    # ### end Alembic commands ###


def downgrade_softphone():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_index('idx_pname', 'tbl_series_number_generator', ['softphone_no'], unique=False)
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
    # ### end Alembic commands ###


def upgrade_voucher():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_voucher():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

