"""empty message

Revision ID: d8c9a3c5a67e
Revises: 
Create Date: 2019-08-09 22:39:55.019177

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd8c9a3c5a67e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade(engine_name):
    globals()["upgrade_%s" % engine_name]()


def downgrade(engine_name):
    globals()["downgrade_%s" % engine_name]()





def upgrade_():
    pass


def downgrade_():
    pass


def upgrade_users():
    pass


def downgrade_users():
    pass


def upgrade_assets():
    pass


def downgrade_assets():
    pass


def upgrade_connection():
    pass


def downgrade_connection():
    pass

