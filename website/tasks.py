# -*- coding: utf-8 -*-

"""Contains the functions to be used with Celery."""

from celery import Celery
from flask_mail import Mail, Message

from website import app, db
from website.models import *


# setup Flask-Mail
mail = Mail(app)


def make_celery(flask_app):
    celery = Celery(__name__)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)
celery.config_from_object('celeryconfig')


@celery.task
def add_new_connection_data_to_db(data):
    """Asynchronously add new connection data to database."""
    connection = NewConnection(
        query_no=data['query_no'],
        name=data['name'],
        address=data['address'],
        location=data['location'],
        postal_code=data['postal_code'],
        phone_no=data['phone_no'],
        email=data['email'],
        date=data['date'],
        time=data['time'],
    )
    db.session.add(connection)
    db.session.commit()


@celery.task
def send_async_new_connection_mail(recipient_mail, query_no):
    """Asynchronously send mail for new connection request."""

    html_body = ('Dear Sir/Madam,</br></br>'
                 'Thank you for the enquiry posted on our website. '
                 'We will be happy to serve you. Please use the query code '
                 '<strong>{0}</strong> for further communication regarding '
                 'this request.</br></br>'
                 'Based on the details provided, we will conduct a preliminary '
                 'feasibility study and one of our representatives will get in '
                 'touch with you within 24 hours.</br></br>'
                 'Please feel free to contact us at 1800 419 4244 at any time.'
                 '</br></br>Thanking you and with warm regards,</br></br>'
                 'Team Wishnet').format(query_no)
    msg = Message(
        subject='Acknowledgement of receipt of enquiry - Wishnet',
        html=html_body,
        recipients=[recipient_mail]
    )
    mail.send(msg)


@celery.task
def add_txn_data_to_db(data):
    """Asynchronously add transaction data to database."""
    txn = RechargeEntry(
        customer_no=data['customer_no'],
        customer_zone_id=data['customer_zone_id'],
        wishnet_payment_order_id=data['wishnet_order_id'],
        payment_gateway=data['payment_gateway'],
        payment_gateway_order_id=data['txn_order_id'],
        payment_amount=data['txn_amount'],
        payment_datetime=data['txn_datetime'],
        payment_date=data['txn_date'],
        payment_time=data['txn_time'],
        payment_status=data['txn_status'],
        mq_topup_reference_id=data['topup_ref_id'],
        mq_topup_datetime=data['topup_datetime'],
        mq_topup_status=data['topup_status'],
        mq_addplan_reference_id=data['addplan_ref_id'],
        mq_addplan_datetime=data['addplan_datetime'],
        mq_addplan_status=data['addplan_status'],
    )
    db.session.add(txn)
    db.session.commit()


@celery.task
def add_new_ticket_to_db(data):
    """Asynchronously add new connection data to database."""
    ticket = Ticket(
        customer_no=data['customer_no'],
        ticket_no=data['ticket_no'],
        category_desc=data['category_desc'],
        nature_desc=data['nature_desc'],
        remarks=data['remarks'],
        opening_date=data['opening_date'],
        opening_time=data['opening_time']
    )
    db.session.add(ticket)
    db.session.commit()


@celery.task
def add_profile_update_request_to_db(data):
    """Asynchronously add self-care profile update request to database."""
    update_profile = UpdateProfileRequest(
        customer_no=data['customer_no'],
        new_phone_no=data['new_phone_no'],
        new_email=data['new_email'],
        status=data['status'],
        request_date=data['request_date'],
        request_time=data['request_time'],
    )
    db.session.add(update_profile)
    db.session.commit()


@celery.task
def add_mobile_number_update_request_to_db(data):
    """Asynchronously add mobile number update request to database."""
    update_mobile_no = MobileNumberUpdateRequest(
        old_phone_no=data['old_phone_no'],
        new_phone_no=data['new_phone_no'],
        username_or_ip_address=data['username_or_ip_address'],
        postal_code=data['postal_code']
    )
    db.session.add(update_mobile_no)
    db.session.commit()


@celery.task
def update_profile_in_db(data):
    """Asynchronously update email address and/or mobile no. in the database."""
    customer = CustomerInfo.query.filter_by(
        customer_no=data['customer_no']
    ).first()

    # only email
    if data['email'] and not data['mobile_no']:
        customer.email_id = data['email']
    # only mobile no.
    elif not data['email'] and data['mobile_no']:
        customer.mobile_number = data['mobile_no']
    # both email and mobile no.
    elif data['email'] and data['mobile_no']:
        customer.email_id = data['email']
        customer.mobile_number = data['mobile_no']

    db.session.commit()


@celery.task
def add_gst_update_request_to_db(data):
    """Asynchronously add GST number update request to database."""
    update_gst = GSTUpdateRequest(
        customer_no=data['customer_no'],
        gst_no=data['gst_no'],
        request_date=data['request_date'],
        request_time=data['request_time']
    )
    db.session.add(update_gst)
    db.session.commit()


@celery.task
def add_async_softphone_allotment(data):
    """Asynchronously add softphone allotment data to database."""
    softphone = SoftphoneEntry(
        cust_no=data['customer_no'],
        cust_name=data['customer_name'],
        user_name=data['user_name'],
        cust_mob=data['customer_mobile_no'],
        password=data['password_hash'],
        softphone_did='',
        softphone_no=data['softphone_number'],
        softphone_os=data['softphone_os'],
        create_dt=data['create_date'],
        expiry_dt=data['expiry_date'],
        softphone_status=data['status'],
        category_type=data['category'],
        user_type='Customer'
    )
    db.session.add(softphone)
    db.session.commit()
