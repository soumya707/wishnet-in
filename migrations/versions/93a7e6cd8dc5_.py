"""empty message

Revision ID: 93a7e6cd8dc5
Revises: 2681792229a6
Create Date: 2019-09-30 23:04:14.946821

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '93a7e6cd8dc5'
down_revision = '2681792229a6'
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
    op.drop_table('customer_info2')
    op.drop_index('userID_2', table_name='tab_csv')
    op.drop_table('tab_csv')
    op.alter_column('customer_info', 'customer_name',
               existing_type=mysql.VARCHAR(length=400),
               nullable=False)
    op.alter_column('customer_info', 'customer_no',
               existing_type=mysql.VARCHAR(length=20),
               nullable=False)
    op.alter_column('customer_info', 'user_name',
               existing_type=mysql.VARCHAR(length=100),
               nullable=False)
    # ### end Alembic commands ###


def downgrade_users():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('customer_info', 'user_name',
               existing_type=mysql.VARCHAR(length=100),
               nullable=True)
    op.alter_column('customer_info', 'customer_no',
               existing_type=mysql.VARCHAR(length=20),
               nullable=True)
    op.alter_column('customer_info', 'customer_name',
               existing_type=mysql.VARCHAR(length=400),
               nullable=True)
    op.create_table('tab_csv',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.Column('userID', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('user', mysql.VARCHAR(length=400), nullable=True),
    sa.Column('address', mysql.VARCHAR(length=10000), nullable=True),
    sa.Column('mob_no', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('reg_dt', mysql.VARCHAR(length=50), nullable=True),
    sa.Column('email', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('ip', mysql.VARCHAR(length=50), nullable=True),
    sa.Column('plan_name', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('zone_name', mysql.VARCHAR(length=200), nullable=True),
    sa.Column('user_name', mysql.VARCHAR(length=200), nullable=True),
    sa.Column('gstin', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('pan', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('zone_id', mysql.VARCHAR(length=200), nullable=True),
    sa.Column('status', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('count', mysql.INTEGER(display_width=10), autoincrement=False, nullable=True),
    sa.Column('cust_no', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('status_map', mysql.VARCHAR(length=11), nullable=True),
    sa.Column('gst_dt', sa.DATE(), nullable=True),
    sa.Column('map_status', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('zone_map', mysql.INTEGER(display_width=11), autoincrement=False, nullable=True),
    sa.Column('upd_dt', sa.DATE(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='latin1',
    mysql_engine='InnoDB'
    )
    op.create_index('userID_2', 'tab_csv', ['userID'], unique=False)
    op.create_table('customer_info2',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.Column('customer_no', mysql.VARCHAR(length=20), nullable=False),
    sa.Column('user_name', mysql.VARCHAR(length=100), nullable=False),
    sa.Column('mobile_no', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('ip_addr', mysql.VARCHAR(length=100), nullable=True),
    sa.Column('customer_name', mysql.VARCHAR(length=400), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='latin1',
    mysql_engine='InnoDB'
    )
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
    op.create_table('transaction_entry',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('customer_no', sa.String(length=100), nullable=False),
    sa.Column('wishnet_payment_order_id', sa.String(length=20), nullable=False),
    sa.Column('payment_gateway', sa.String(length=10), nullable=False),
    sa.Column('payment_gateway_order_id', sa.String(length=100), nullable=False),
    sa.Column('payment_amount', sa.String(length=10), nullable=False),
    sa.Column('payment_datetime', sa.String(length=50), nullable=False),
    sa.Column('payment_status', sa.String(length=200), nullable=False),
    sa.Column('mq_topup_reference_id', sa.String(length=20), nullable=False),
    sa.Column('mq_topup_datetime', sa.String(length=50), nullable=False),
    sa.Column('mq_topup_status', sa.String(length=10), nullable=False),
    sa.Column('mq_addplan_reference_id', sa.String(length=20), nullable=False),
    sa.Column('mq_addplan_datetime', sa.String(length=50), nullable=False),
    sa.Column('mq_addplan_status', sa.String(length=10), nullable=False),
    sa.Column('refund_amount', sa.String(length=10), nullable=True),
    sa.Column('refund_datetime', sa.String(length=50), nullable=True),
    sa.Column('refund_status', sa.String(length=10), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.drop_table('recharge_entry')
    # ### end Alembic commands ###


def downgrade_recharge():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('recharge_entry',
    sa.Column('id', mysql.INTEGER(display_width=11), autoincrement=True, nullable=False),
    sa.Column('wishnet_payment_order_id', mysql.VARCHAR(length=20), nullable=False),
    sa.Column('payment_gateway', mysql.VARCHAR(length=10), nullable=False),
    sa.Column('payment_gateway_order_id', mysql.VARCHAR(length=100), nullable=False),
    sa.Column('payment_status', mysql.VARCHAR(length=200), nullable=False),
    sa.Column('mq_topup_reference_id', mysql.VARCHAR(length=20), nullable=False),
    sa.Column('mq_topup_status', mysql.VARCHAR(length=10), nullable=False),
    sa.Column('mq_topup_datetime', mysql.VARCHAR(length=50), nullable=False),
    sa.Column('payment_datetime', mysql.VARCHAR(length=50), nullable=False),
    sa.Column('payment_amount', mysql.VARCHAR(length=10), nullable=False),
    sa.Column('refund_amount', mysql.VARCHAR(length=10), nullable=True),
    sa.Column('refund_datetime', mysql.VARCHAR(length=50), nullable=True),
    sa.Column('refund_status', mysql.VARCHAR(length=10), nullable=True),
    sa.Column('customer_no', mysql.VARCHAR(length=100), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    mysql_default_charset='latin1',
    mysql_engine='InnoDB'
    )
    op.drop_table('transaction_entry')
    # ### end Alembic commands ###


def upgrade_ticket():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###


def downgrade_ticket():
    # ### commands auto generated by Alembic - please adjust! ###
    pass
    # ### end Alembic commands ###

