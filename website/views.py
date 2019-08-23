# -*- coding: utf-8 -*-

"""Views for the website."""


import random
import string

from flask import (
    current_app, flash, redirect, render_template, request, session, url_for)
from flask_sqlalchemy_caching import FromCache
from flask_wtf.csrf import CSRFProtect

from website import app, cache
from website.forms import AuthenticationForm, NewConnectionForm, RechargeForm
from website.helpers import (
    ActivePlan, AuthenticateUser, ContractsByKey, Recharge)
from website.models import (
    FAQ, BestPlans, Downloads, JobVacancy, NewConnection, RegionalOffices,
    Services, Ventures)
from website.paytm_utils import initiate_transaction, verify_transaction


csrf = CSRFProtect(app)


@app.route('/', methods=['GET', 'POST'])
def index():
    """Route for homepage."""
    form = RechargeForm()

    if form.validate_on_submit():
        user = request.form['user_id']
        user_contracts = ContractsByKey(app)
        user_contracts.request(user)
        user_contracts.response()

        active_plan_objs = [ActivePlan(plan) for plan in
                            user_contracts.active_plans]

        form_data = initiate_transaction(user_contracts.ref_no, user)

        session['active_plans'] = active_plan_objs
        session['paytm_form'] = form_data

        # return render_template('payment.html', active_plans=active_plan_objs,
        #                        paytm_data=form_data)

        return redirect(
            url_for(
                'payment',
                cust_id=user,
                ref_no=user_contracts.ref_no,
            )
        )

    services = Services.query.options(FromCache(cache)).all()
    best_plans = BestPlans.query.options(FromCache(cache)).all()
    downloads = Downloads.query.options(FromCache(cache)).all()

    return render_template(
        'index.html',
        form=form,
        services=services,
        plans=best_plans,
        downloads=downloads,
    )


@app.route('/tariff')
def tariff():
    """Route for tariff."""
    db = current_app.extensions['sqlalchemy'].db

    classes = [cls for cls in db.Model._decl_class_registry.values()
               if isinstance(cls, type) and issubclass(cls, db.Model)]

    plan_classes = [cls for cls in classes if cls.__name__.endswith('Plan')]

    # plans = [entry for plan in plan_classes for entry in plan.query.all()]

    return render_template('tariff.html', plans=plan_classes)


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
            email=form.email_address.data,
            remark=form.remark.data,
        )
        db = current_app.extensions['sqlalchemy'].db
        db.session.add(connection)
        db.session.commit()

        flash('Request sent successfully!', 'success')
        return redirect(url_for('new_conn'))

    return render_template('new_connection.html', form=form)


@app.route('/contact')
def contact():
    """Route for contact."""
    regional_offices = RegionalOffices.query.options(FromCache(cache)).all()

    return render_template('contact.html', regional_offices=regional_offices)


@app.route('/support')
def support():
    """Route for support."""
    faq = FAQ.query.options(FromCache(cache)).all()

    return render_template('support.html', items=faq)


@app.route('/career')
def career():
    """Route for career."""
    items = JobVacancy.query.options(FromCache(cache)).all()

    return render_template('careers.html', items=items)


@app.route('/about')
def about():
    """Route for about us."""
    ventures = Ventures.query.options(FromCache(cache)).all()

    return render_template('about.html', ventures=ventures)


# @app.route('/login')
# def login():
#     """Route for login."""
#     return render_template('login.html')


@app.route('/payment/<int:cust_id>/<ref_no>/')
def payment(cust_id, ref_no):
    """Route for payment."""
    return render_template(
        'payment.html',
        active_plans=session['active_plans'],
        paytm_data=session['paytm_form']
    )


@app.route('/verify', methods=['GET', 'POST'])
def verify_response():
    """Route for verifying response for payment."""
    bank_txn_id = request.form['BANKTXNID']
    checksumhash = request.form['CHECKSUMHASH']

    verified = verify_transaction(checksumhash)

    #TODO: add transaction status API call
    if verified:
        top_up = Recharge(app)
        top_up.request()
        top_up.response()
        redirect(url_for('index'))
    else:
        redirect(url_for('payment'))


@app.route('/privacy')
def privacy():
    """Route for privacy."""
    return render_template('privacy.html')
