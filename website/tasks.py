# -*- coding: utf-8 -*-

"""Contains the functions to be used with Celery."""

from website import app, db, mail
from website.models import NewConnection

from celery import Celery
from flask_mail import Message


def make_celery(app):
    celery = Celery(
        app.import_name,
        backend=app.config['CELERY_RESULT_BACKEND'],
        broker=app.config['CELERY_BROKER_URL']
    )
    celery.conf.update(app.config)

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)


@celery.task()
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


@celery.task()
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
                 'Team Wishnet</br>'
                 '<img src="162.241.200.22/static/img/logo/wishnet.svg" '
                 'style="width: 150px; height: 50px">').format(query_no)

    msg = Message(
        subject='Acknowledgement of receipt of enquiry - Wishnet',
        html=html_body,
        recipients=[recipient_mail]
    )

    mail.send(msg)
