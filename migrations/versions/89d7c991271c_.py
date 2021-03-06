"""empty message

Revision ID: 89d7c991271c
Revises: 801012041cf3
Create Date: 2019-09-08 13:17:46.299705

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '89d7c991271c'
down_revision = '801012041cf3'
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
    op.add_column('customer_login', sa.Column('password_hash', sa.String(length=100), nullable=True))
    op.drop_column('customer_login', 'password')
    # ### end Alembic commands ###


def downgrade_users():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('customer_login', sa.Column('password', mysql.VARCHAR(length=100), nullable=True))
    op.drop_column('customer_login', 'password_hash')
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

