# -*- coding: utf-8 -*-

"""Views for the website."""


import random
import string

from flask import (
    current_app, flash, redirect, render_template, request, url_for)

from website import app
from website.forms import ContactForm, NewConnectionForm, RechargeForm
from website.models import (
    FAQ, BestPlans, Downloads, JobVacancy, NewConnection, Services, Ventures)
from website.helpers import Recharge


@app.route('/', methods=['GET', 'POST'])
def index():
    """Route for homepage."""
    form = RechargeForm()

    if form.validate_on_submit():
        user = request.form['user_id']
        recharge_user = Recharge(app)
        recharge_user.request(user)
        recharge_user.response()

        flash('Transaction no.: {} Reference no.: {} Message: {}'.format(
            recharge_user.txn_no, recharge_user.ref_no, recharge_user.txn_msg),
              category='success')

        return redirect(url_for('index'))



    services = Services.query.all()
    best_plans = BestPlans.query.all()
    downloads = Downloads.query.all()
    ventures = Ventures.query.all()

    return render_template(
        'index.html',
        form=form,
        services=services,
        plans=best_plans,
        downloads=downloads,
        ventures=ventures
    )


@app.route('/tariff')
def tariff():
    """Route for tariff."""
    db = current_app.extensions['sqlalchemy'].db

    classes = [cls for cls in db.Model._decl_class_registry.values()
               if isinstance(cls, type) and issubclass(cls, db.Model)]

    plans = [cls for cls in classes if cls.__name__.endswith('Plan')]

    return render_template('tariff.html', plans=plans)


@app.route('/new_connection', methods=['GET', 'POST'])
def new_conn():
    """Route for new connection."""
    form = NewConnectionForm()

    if form.validate_on_submit():
        connection = NewConnection(
            query_no=''.join(
                random.choices(
                    string.ascii_letters + string.digits, k=8
                )
            ),
            name='{} {} {}'.format(
                form.first_name.data,
                form.middle_name.data,
                form.last_name.data
            ),
            address=form.address.data,
            location=form.location.data,
            postal_code=form.postal_code.data,
            phone_no=form.phone_no.data,
            remark=form.remark.data,
        )
        db = current_app.extensions['sqlalchemy'].db
        db.session.add(connection)
        db.session.commit()

        flash('Request sent successfully!', 'success')
        return redirect(url_for('new_conn'))

    return render_template('new_connection.html', form=form)


@app.route('/contact', methods=['GET', 'POST'])
def contact():
    """Route for contact."""
    form = ContactForm()

    if form.validate_on_submit():
        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))

    return render_template('contact.html', form=form)


@app.route('/support')
def support():
    """Route for support."""
    faq = FAQ.query.all()

    return render_template('support.html', items=faq)


@app.route('/career')
def career():
    """Route for career."""
    items = JobVacancy.query.all()
    return render_template('careers.html', items=items)


@app.route('/about')
def about():
    """Route for about us."""
    return render_template('about.html')


@app.route('/login')
def login():
    """Route for login."""
    return render_template('login.html')


@app.route('/recharge')
def recharge():
    """Route for recharge."""
    form = RechargeForm()

    if form.validate_on_submit():
        flash('Recharge completed!', 'success')
        return redirect(url_for('recharge'))

    return render_template('recharge.html')


@app.route('/privacy')
def privacy():
    """Route for privacy."""
    return render_template('privacy.html')
