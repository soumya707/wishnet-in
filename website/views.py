# -*- coding: utf-8 -*-

"""Views for the website."""


import random
import string

from flask import (
    current_app, flash, redirect, render_template, request, session, url_for)
from flask_sqlalchemy_caching import FromCache
from flask_wtf.csrf import CSRFProtect

from website import app, cache, plans
from website.forms import AuthenticationForm, NewConnectionForm, RechargeForm
from website.models import (
    FAQ, BestPlans, CarouselImages, Downloads, JobVacancy, RegionalOffices,
    Services, Ventures)
from website.mqs_api import (
    AuthenticateUser, ContractsByKey, CustomerInfo, Recharge)
from website.paytm_utils import (
    initiate_transaction, verify_final_status, verify_transaction)
from website.razorpay_utils import make_order, verify_signature
from website.tasks import (
    add_new_connection_data_to_db, send_async_new_connection_mail)


csrf = CSRFProtect(app)

#TODO: add when self-care portal is ready
# @app.before_first_request
# def init_session_var():
#     """Initialize session variable for portal use."""

#     # set user to be logged out
#     session['user_logged_in'] = False


# Routes

@app.route('/', methods=['GET', 'POST'])
def index():
    """Route for homepage."""

    form = RechargeForm()

    if form.validate_on_submit():
        user = request.form['user_id']

        # Get active plans (reference no. of this API call is passed forward)
        user_contracts = ContractsByKey(app)
        user_contracts.request(user)
        user_contracts.response()

        # user exists
        if user_contracts.valid_user:
            # Get active plans for the user
            active_plans = {
                plans.all_plans[plan][0]: (plans.all_plans[plan][1], validity)
                for (plan, validity) in user_contracts.active_plans
                if plan in plans.all_plans
            }

            # Get customer info
            user_info = CustomerInfo(app)
            user_info.request(user)
            user_info.response()

            session['active_plans'] = active_plans
            session['cust_data'] = user_info.to_dict()
            session['order_id'] = user_contracts.ref_no

            return redirect(
                url_for(
                    'payment',
                    cust_id=user,
                    ref_no=user_contracts.ref_no,
                )
            )
        # user does not exist
        elif not user_contracts.valid_user:
            flash('Invalid customer number! Please try again.', 'danger')
            return redirect(
                url_for('index')
            )

    carousel_images = CarouselImages.query.options(FromCache(cache)).all()
    services = Services.query.options(FromCache(cache)).all()
    best_plans = BestPlans.query.options(FromCache(cache)).all()
    downloads = Downloads.query.options(FromCache(cache)).all()

    return render_template(
        'index.html',
        form=form,
        carousel_images=carousel_images,
        services=services,
        plans=best_plans,
        downloads=downloads,
    )


@app.route('/payment/<int:cust_id>/<ref_no>', methods=['GET', 'POST'])
def payment(cust_id, ref_no):
    """Route for payment."""

    if request.method == 'POST':

        # Check payment gateway
        if request.form['gateway'] == 'paytm':
            # Get Paytm form data
            form_data = initiate_transaction(
                order_id=ref_no,
                cust_info=session['cust_data'],
                amount=request.form['amount']
            )

            return render_template(
                'paytm_pay.html',
                paytm_form=form_data,
            )

        elif request.form['gateway'] == 'razorpay':
            # Get Razorpay form data
            razorpay_order, form_data = make_order(
                order_id=ref_no,
                cust_info=session['cust_data'],
                amount=request.form['amount']
            )

            return render_template(
                'razorpay_pay.html',
                razorpay_form=form_data,
            )

    elif request.method == 'GET':

        return render_template(
            'payment.html',
            cust_data=session['cust_data'],
            active_plans=session['active_plans'],
        )


@app.route('/verify/<gateway>', methods=['POST'])
@csrf.exempt
def verify_response(gateway):
    """Route for verifying response for payment."""
    if request.method == 'POST':

        if gateway == 'paytm':
            verified = verify_transaction(request.form)

            if verified:
                final_status = verify_final_status(session['order_id'])
                # top_up = Recharge(app)
                # top_up.request()
                # top_up.response()
                flash('{}'.format(final_status), 'info')
            else:
                flash('Recharge failed! Please try again.', 'danger')

        elif gateway == 'razorpay':
            verified = verify_signature(request.form)
            if verified:
                # TopUp
                flash('Recharge successful', 'info')
            else:
                flash('Recharge failed! Please try again.', 'danger')

        return redirect(url_for('index'))


@app.route('/tariff')
def tariff():
    """Route for tariff."""
    db = current_app.extensions['sqlalchemy'].db

    classes = [cls for cls in db.Model._decl_class_registry.values()
               if isinstance(cls, type) and issubclass(cls, db.Model)]

    plan_classes = [cls for cls in classes if cls.__name__.endswith('Plan')]

    return render_template('tariff.html', plans=plan_classes)


@app.route('/new_connection', methods=['GET', 'POST'])
def new_conn():
    """Route for new connection."""
    form = NewConnectionForm()

    if form.validate_on_submit():
        query_no = ''.join(
            random.choices(
                string.ascii_letters + string.digits, k=8
            )
        )

        form_data = {
            'query_no': query_no,
            'name': '{} {} {}'.format(
                form.first_name.data,
                form.middle_name.data,
                form.last_name.data
            ),
            'address': form.address.data,
            'location': form.location.data,
            'postal_code': form.postal_code.data,
            'phone_no': form.phone_no.data,
            'email': form.email_address.data,
            'remark': form.remark.data,
        }

        # add data to db async
        add_new_connection_data_to_db.delay(form_data)

        # send mail async
        send_async_new_connection_mail.delay(form.email_address.data, query_no)

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
    categories = {item.category for item in faq}

    return render_template('support.html', categories=categories, items=faq)


@app.route('/career')
def career():
    """Route for career."""
    items = JobVacancy.query.filter_by(status='Active')\
                            .options(FromCache(cache)).all()

    return render_template('careers.html', items=items)


@app.route('/about')
def about():
    """Route for about us."""
    ventures = Ventures.query.options(FromCache(cache)).all()

    return render_template('about.html', ventures=ventures)


#TODO: add when self-care portal is ready
# @app.route('/portal', methods=['GET', 'POST'])
# def portal():
#     """Route for portal."""

#     # preliminary check whether user is already logged in
#     if not session['user_logged_in']:
#         form = AuthenticationForm()

#         if form.validate_on_submit():
#             username = request.form['username']
#             password = request.form['password']

#             authenticate_user = AuthenticateUser(app)
#             authenticate_user.request(username, password)

#             # if login is successful
#             if authenticate_user.response():
#                 session['user_logged_in'] = True
#                 return render_template('portal.html', logged_in=True)

#             # if login fails, display message
#             else:
#                 flash('Could not log in due to invalid credentials', 'danger')
#                 return redirect(url_for('portal'))

#         return render_template('portal.html', logged_in=False, form=form)

#     elif session['user_logged_in']:
#         return render_template('portal.html', logged_in=True)


@app.route('/privacy')
def privacy():
    """Route for privacy."""
    return render_template('privacy.html')
