"""empty message

Revision ID: 801012041cf3
Revises: dbc12bb65900
Create Date: 2019-09-08 13:06:33.936584

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '801012041cf3'
down_revision = 'dbc12bb65900'
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
    op.create_table('customer_login',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_no', sa.String(length=100), nullable=False),
    sa.Column('password', sa.String(length=100), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade_users():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('customer_login')
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
    op.alter_column('recharge_entry', 'payment_status',
               existing_type=mysql.VARCHAR(length=200),
               nullable=False)
    # ### end Alembic commands ###


def downgrade_recharge():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('recharge_entry', 'payment_status',
               existing_type=mysql.VARCHAR(length=200),
               nullable=True)
    # ### end Alembic commands ###
