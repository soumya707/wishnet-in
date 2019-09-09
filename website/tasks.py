# -*- coding: utf-8 -*-

"""Contains the functions to be used with Celery."""

from celery import Celery
from flask_mail import Mail, Message

from website import app, db
from website.models import NewConnection, RechargeEntry


# setup Flask-Mail
mail = Mail(app)


def make_celery(flask_app):
    celery = Celery(
        flask_app.import_name,
        backend=flask_app.config['CELERY_RESULT_BACKEND'],
        broker=flask_app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(flask_app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with flask_app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)


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
        remark=data['remark'],
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
def add_recharge_data_to_db(data):
    """Asynchronously add recharge data to database."""
    recharge = RechargeEntry(
        wishnet_payment_order_id=data['wishnet_order_id'],
        payment_gateway=data['payment_gateway'],
        payment_gateway_order_id=data['txn_order_id'],
        payment_amount=data['txn_amount'],
        payment_datetime=data['txn_datetime'],
        payment_status=data['txn_status'],
        mq_topup_reference_id=data['topup_ref_id'],
        mq_topup_datetime=data['topup_datetime'],
        mq_topup_status=data['topup_status'],
    )
    db.session.add(recharge)
    db.session.commit()
