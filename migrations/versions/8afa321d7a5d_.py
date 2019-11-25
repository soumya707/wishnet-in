"""empty message

Revision ID: 8afa321d7a5d
Revises: 9a18de471b8e
Create Date: 2019-11-21 00:02:09.938841

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '8afa321d7a5d'
down_revision = '9a18de471b8e'
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
    op.drop_column('customer_info', 'first_name')
    op.drop_column('customer_info', 'last_name')
    op.drop_column('customer_info', 'zip_code')
    # ### end Alembic commands ###


def downgrade_users():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('customer_info', sa.Column('zip_code', mysql.VARCHAR(length=10), nullable=True))
    op.add_column('customer_info', sa.Column('last_name', mysql.VARCHAR(length=50), nullable=True))
    op.add_column('customer_info', sa.Column('first_name', mysql.VARCHAR(length=50), nullable=True))
    op.alter_column('customer_info', 'zone_id',
               existing_type=mysql.VARCHAR(length=50),
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
    pass
    # ### end Alembic commands ###


def downgrade_softphone():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###
