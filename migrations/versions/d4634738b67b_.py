"""empty message

Revision ID: d4634738b67b
Revises: 9739ccc46b16
Create Date: 2019-08-29 19:34:00.283447

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'd4634738b67b'
down_revision = '9739ccc46b16'
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
    pass
    # ### end Alembic commands ###


def upgrade_assets():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('job_vacancy', 'key_skills')
    # ### end Alembic commands ###


def downgrade_assets():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('job_vacancy', sa.Column('key_skills', mysql.VARCHAR(length=50), nullable=False))
    # ### end Alembic commands ###


def upgrade_connection():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_connection():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

