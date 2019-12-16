# -*- coding: utf-8 -*-

"""Views for the website."""


import json
import random
import string
from datetime import datetime, timedelta

from flask import (
    current_app, flash, redirect, render_template, request, session, url_for)
from flask_paginate import Pagination, get_page_args
from flask_sqlalchemy import SignallingSession
from flask_sqlalchemy_caching import FromCache
from flask_wtf.csrf import CSRFProtect
from passlib.exc import MalformedTokenError, TokenError
from passlib.hash import pbkdf2_sha256
from razorpay.errors import BadRequestError, SignatureVerificationError
from sqlalchemy import and_, or_

from website import CACHE, TOTPFACTORY, app
from website.forms import *
from website.messages import *
from website.models import *
from website.mqs_api import *
from website.paytm_utils import (
    initiate_transaction, verify_final_status, verify_transaction)
from website.razorpay_utils import get_notes, make_order, verify_signature
from website.softphone_utils import *
from website.tasks import *
from website.utils import *


CSRF = CSRFProtect(app)


@app.before_first_request
def init_session_var():
    """Initialize session variable for portal use."""
    # set user to be logged out
    session['user_logged_in'] = False


# Routes

@app.route('/', methods=['GET', 'POST'])
def index():
    """Route for homepage."""
    form = RechargeForm()

    if form.validate_on_submit():
        user = form.user_id.data

        # Get customer info
        customer = CustomerInfo.query.filter_by(customer_no=user).first()

        # Check if customer data is available in the db
        # user data available in the db
        if customer is not None:
            # Get active plans (ref no. of this API call is passed forward)
            user_contracts = ContractsByKey(app)
            user_contracts.request(user)
            user_contracts.response()

            # User is valid in MQS
            if user_contracts.valid_user:
                plans = {
                    row.plan_code: row
                    for row in TariffInfo.query.options(FromCache(CACHE)).all()
                }
                # Get active plans for the user
                # {plan_name: (price, validity, plan_code)}
                active_plans = {
                    plans[plan_code].plan_name: (
                        plans[plan_code].price, validity_period, plan_code
                    )
                    for (plan_code, validity_period) in
                    user_contracts.active_plans if plan_code in plans
                }

                # No active plans
                if not active_plans:
                    flash(NO_ACTIVE_PLANS, 'danger')
                    return redirect(url_for('index'))

                # Has active plans
                elif active_plans:
                    return redirect(
                        url_for(
                            'insta_recharge',
                            order_id=user_contracts.ref_no,
                            customer_no=customer.customer_no,
                            customer_name=customer.customer_name,
                            customer_mobile_no=customer.mobile_no,
                            active_plans=json.dumps(active_plans),
                        )
                    )

            # User is invalid in MQS
            elif not user_contracts.valid_user:
                flash(USER_NOT_FOUND_IN_DB, 'danger')
                return redirect(url_for('index'))
        # user data not available in the db; might be a new user
        else:
            flash(USER_NOT_FOUND_IN_DB, 'danger')
            return redirect(url_for('index'))

    # GET request
    carousel_images = CarouselImages.query.options(FromCache(CACHE)).all()
    services = Services.query.options(FromCache(CACHE)).all()
    best_plans = BestPlans.query.options(FromCache(CACHE)).all()
    downloads = Downloads.query.options(FromCache(CACHE)).all()

    return render_template(
        'index.html',
        form=form,
        carousel_images=carousel_images,
        services=services,
        plans=best_plans,
        downloads=downloads,
    )


@app.route('/insta_recharge/<order_id>', methods=['GET', 'POST'])
def insta_recharge(order_id):
    """Route for insta-recharge."""

    if request.method == 'GET':

        return render_template(
            'insta_recharge.html',
            customer_no=request.args.get('customer_no'),
            customer_name=request.args.get('customer_name'),
            customer_mobile_no=request.args.get('customer_mobile_no'),
            active_plans=json.loads(request.args.get('active_plans')),
        )

    elif request.method == 'POST':
        # store customer number in session
        session['insta_customer_no'] = request.form['customer_no']
        # store customer name in session
        session['insta_customer_name'] = request.form['customer_name']
        # store amount in session
        session['insta_amount'] = request.form['amount']
        # store selected plan code in session
        session['insta_plan_code'] = request.form['plan_code']
        # store order id in session
        session['insta_order_id'] = order_id

        # Check payment gateway
        if request.form['gateway'] == 'paytm':
            # Get Paytm form data
            form_data = initiate_transaction(
                order_id=order_id,
                customer_no=request.form['customer_no'],
                customer_mobile_no=request.form['customer_mobile_no'],
                amount=request.form['amount'],
                # _ is used as the delimiter; check paytm_utils
                pay_source='insta_recharge',
            )

        elif request.form['gateway'] == 'razorpay':
            # Get Razorpay form data
            form_data = make_order(
                order_id=order_id,
                customer_no=request.form['customer_no'],
                customer_mobile_no=request.form['customer_mobile_no'],
                customer_email=app.config['RAZORPAY_DEFAULT_MAIL'],
                amount=request.form['amount'],
                # list is used for passing data; check razorpay_utils
                pay_source=['insta', 'recharge'],
            )

            # store Razorpay order id for verification later
            session['razorpay_order_id'] = form_data['order_id']

        return render_template(
            '{}_pay.html'.format(request.form['gateway']),
            form=form_data,
        )


@app.route('/verify/<gateway>', methods=['GET', 'POST'])
@CSRF.exempt
def verify_response(gateway):
    """Route for verifying response for payment."""
    if request.method == 'POST':
        # check payment gateway
        # PAYTM
        if gateway == 'paytm':
            session_var_prefix, txn_type = \
                request.form['MERC_UNQ_REF'].split('_')

            # get zone id for table entry
            zone_id = CustomerInfo.query.\
                options(FromCache(CACHE)).\
                filter_by(
                    customer_no=session[f'{session_var_prefix}_customer_no']
                ).first().zone_id

            # store response data
            data = {
                'customer_no': session[f'{session_var_prefix}_customer_no'],
                'customer_zone_id': zone_id,
                'wishnet_order_id': session[f'{session_var_prefix}_order_id'],
                'payment_gateway': 'Paytm',
                'txn_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'txn_date': datetime.now().astimezone().date(),
                'txn_time': datetime.now().astimezone().time(),
            }

            # initial checksum verification
            verified = verify_transaction(request.form)

            # check verification success
            if verified:
                data.update(txn_order_id=request.form['TXNID'])
                # final status verification
                final_status_code = verify_final_status(
                    session[f'{session_var_prefix}_order_id']
                )

                # check if transaction successful
                if final_status_code == '01':
                    data.update(
                        txn_amount=request.form['TXNAMOUNT'],
                        txn_datetime=str(request.form['TXNDATE']),
                        txn_status='SUCCESS'
                    )

                    # check transaction type: recharge or add plan
                    if txn_type == 'recharge':
                        # TopUp in MQS
                        top_up = Recharge(app)
                        top_up.request(
                            session[f'{session_var_prefix}_customer_no'],
                            session[f'{session_var_prefix}_plan_code']
                        )
                        top_up.response()

                        # verify MQS TopUp status
                        db_entry_status, status, flash_msg, msg_stat = \
                            verify_mqs_topup(top_up)

                        # update data to be passed further
                        data.update(
                            topup_ref_id=top_up.ref_no,
                            topup_datetime=datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            topup_status=db_entry_status,
                            addplan_ref_id='',
                            addplan_datetime='',
                            addplan_status=''
                        )

                    elif txn_type == 'addplan':
                        # AddPlan in MQS
                        addplan = AddPlan(app)
                        addplan.request(
                            session[f'{session_var_prefix}_customer_no'],
                            session[f'{session_var_prefix}_plan_code']
                        )
                        addplan.response()

                        # verify MQS AddPlan status
                        db_entry_status, status, flash_msg, msg_stat = \
                            verify_mqs_addplan(addplan)

                        # update data to be passed further
                        data.update(
                            addplan_ref_id=addplan.ref_no,
                            addplan_datetime=datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            addplan_status=db_entry_status,
                            topup_ref_id='',
                            topup_datetime='',
                            topup_status=''
                        )

                    flash(flash_msg, msg_stat)

                # Transaction Status failure
                else:
                    data.update(
                        txn_amount='',
                        txn_status='INCOMPLETE',
                        topup_ref_id='',
                        topup_datetime='',
                        topup_status='',
                        addplan_ref_id='',
                        addplan_datetime='',
                        addplan_status='',
                    )
                    status = 'unsuccessful'
                    flash(INCOMPLETE_PAYMENT, 'danger')

            # checksumhash verification failure
            # data tampered during transaction
            elif not verified:
                data.update(
                    txn_order_id='',
                    txn_amount='',
                    txn_status='VERIFICATION FAILURE',
                    topup_ref_id='',
                    topup_datetime='',
                    topup_status='',
                    addplan_ref_id='',
                    addplan_datetime='',
                    addplan_status='',
                )
                status = 'unsuccessful'
                flash(UNSUCCESSFUL_PAYMENT, 'danger')

        # RAZORPAY
        elif gateway == 'razorpay':
            # verify signature
            verify_params = {
                'razorpay_order_id': session['razorpay_order_id'],
                'razorpay_payment_id': request.form.get('razorpay_payment_id'),
                'razorpay_signature': request.form.get('razorpay_signature')
            }

            try:
                verify_signature(verify_params)
                verified = True
            except (SignatureVerificationError, BadRequestError) as _:
                verified = False

            # get metadata of order (skipping customer no.)
            _, session_var_prefix, txn_type = get_notes(
                session['razorpay_order_id']
            )

            # get zone id for table entry
            zone_id = CustomerInfo.query.\
                options(FromCache(CACHE)).\
                filter_by(
                    customer_no=session[f'{session_var_prefix}_customer_no']
                ).first().zone_id

            # store response data
            data = {
                'customer_no': session[f'{session_var_prefix}_customer_no'],
                'customer_zone_id': zone_id,
                'wishnet_order_id': session[f'{session_var_prefix}_order_id'],
                'payment_gateway': 'Razorpay',
                'txn_order_id': session['razorpay_order_id'],
                'txn_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'txn_date': datetime.now().astimezone().date(),
                'txn_time': datetime.now().astimezone().time(),
            }

            # remove Razorpay order id from session storage
            session.pop('razorpay_order_id', None)

            # signature verification success
            if verified:
                data.update(
                    txn_amount=session[f'{session_var_prefix}_amount'],
                    txn_status='SUCCESS',
                )

                if txn_type == 'recharge':
                    # TopUp in MQS
                    top_up = Recharge(app)
                    top_up.request(
                        session[f'{session_var_prefix}_customer_no'],
                        session[f'{session_var_prefix}_plan_code']
                    )
                    top_up.response()

                    # verify MQS TopUp status
                    db_entry_status, status, flash_msg, msg_stat = \
                        verify_mqs_topup(top_up)

                    # update data to be passed further
                    data.update(
                        topup_ref_id=top_up.ref_no,
                        topup_datetime=datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        topup_status=db_entry_status,
                        addplan_ref_id='',
                        addplan_datetime='',
                        addplan_status=''
                    )

                elif txn_type == 'addplan':
                    # AddPlan in MQS
                    addplan = AddPlan(app)
                    addplan.request(
                        session[f'{session_var_prefix}_customer_no'],
                        session[f'{session_var_prefix}_plan_code']
                    )
                    addplan.response()

                    # verify MQS AddPlan status
                    db_entry_status, status, flash_msg, msg_stat = \
                        verify_mqs_addplan(addplan)

                    # update data to be passed further
                    data.update(
                        addplan_ref_id=addplan.ref_no,
                        addplan_datetime=datetime.now().strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        addplan_status=db_entry_status,
                        topup_ref_id='',
                        topup_datetime='',
                        topup_status=''
                    )

                flash(flash_msg, msg_stat)

            # signature verification failure
            # data tampered during transaction
            else:
                data.update(
                    txn_amount='',
                    txn_status='VERIFICATION FAILURE',
                    topup_ref_id='',
                    topup_datetime='',
                    topup_status='',
                    addplan_ref_id='',
                    addplan_datetime='',
                    addplan_status='',
                )
                status = 'unsuccessful'
                flash(UNSUCCESSFUL_PAYMENT, 'danger')

        # add transaction data to db async
        add_txn_data_to_db.delay(data)

        return redirect(
            url_for(
                f'{session_var_prefix}_receipt',
                order_id=session[f'{session_var_prefix}_order_id'],
                status=status,
                txn_datetime=data['txn_datetime']
            )
        )

    # handle Razorpay transaction cancel
    elif request.method == 'GET':
        # get metadata of order (skipping customer no. and txn type)
        _, session_var_prefix, _ = get_notes(
            session['razorpay_order_id']
        )

        # get zone id for table entry
        zone_id = CustomerInfo.query.\
            options(FromCache(CACHE)).\
            filter_by(
                customer_no=session[f'{session_var_prefix}_customer_no']
            ).first().zone_id

        # prepare data to be sent to db
        data = {
            'customer_no': session[f'{session_var_prefix}_customer_no'],
            'customer_zone_id': zone_id,
            'wishnet_order_id': session[f'{session_var_prefix}_order_id'],
            'payment_gateway': 'Razorpay',
            'txn_order_id': session['razorpay_order_id'],
            'txn_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'txn_date': datetime.now().astimezone().date(),
            'txn_time': datetime.now().astimezone().time(),
            'txn_amount': '',
            'txn_status': 'INCOMPLETE',
            'topup_ref_id': '',
            'topup_datetime': '',
            'topup_status': '',
            'addplan_ref_id': '',
            'addplan_datetime': '',
            'addplan_status': '',
        }
        # remove Razorpay order id from session storage
        session.pop('razorpay_order_id', None)

        flash(INCOMPLETE_PAYMENT, 'danger')

        # add transaction data to db async
        add_txn_data_to_db.delay(data)

        return redirect(
            url_for(
                f'{session_var_prefix}_receipt',
                order_id=session[f'{session_var_prefix}_order_id'],
                status='unsuccessful',
                txn_datetime=data['txn_datetime']
            )
        )


@app.route('/receipt/<order_id>')
def insta_receipt(order_id):
    """Route to transaction receipt."""

    return render_template(
        'receipt.html',
        customer_no=session['insta_customer_no'],
        customer_name=session['insta_customer_name'],
        amount=session['insta_amount'],
        date_and_time=request.args.get('txn_datetime'),
        txn_status=request.args.get('status'),
        txn_no=order_id
    )


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
    form.location.choices = [
        (row.location, row.location) for row in
        AvailableLocations.query.options(FromCache(CACHE)).\
        order_by(AvailableLocations.location).all()
    ]

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
            'date': datetime.now().astimezone().date(),
            'time': datetime.now().astimezone().time(),
        }

        # add data to db async
        add_new_connection_data_to_db.delay(form_data)

        # send mail async
        send_async_new_connection_mail.delay(form.email_address.data, query_no)

        flash(SUCCESSFUL_NEW_CONN_REQUEST, 'success')
        return redirect(url_for('new_conn'))

    return render_template('new_connection.html', form=form)


@app.route('/contact')
def contact():
    """Route for contact."""
    regional_offices = RegionalOffices.query.options(FromCache(CACHE)).all()
    return render_template('contact.html', regional_offices=regional_offices)


@app.route('/support')
def support():
    """Route for support."""
    faq = FAQ.query.options(FromCache(CACHE)).all()
    categories = {item.category for item in faq}
    return render_template('support.html', categories=categories, items=faq)


@app.route('/career')
def career():
    """Route for career."""
    items = JobVacancy.query.filter_by(status='Active')\
                            .options(FromCache(CACHE)).all()
    return render_template('careers.html', items=items)


@app.route('/about')
def about():
    """Route for about us."""
    ventures = Ventures.query.options(FromCache(CACHE)).all()
    return render_template('about.html', ventures=ventures)


@app.route('/privacy')
def privacy():
    """Route for privacy."""
    return render_template('privacy.html')


@app.route('/terms_and_conditions')
def terms_and_conditions():
    """Route for terms and conditions."""
    return render_template('terms_and_conditions.html')


@app.route('/end_user_license_wishtalk')
def end_user_license_wishtalk():
    """Route for end user license of WishTalk."""
    return render_template('end_user_license_wishtalk.html')


@app.route('/wishtalk')
def wishtalk_instructions():
    """Route for WishTalk instructions."""
    return render_template('wishtalk_instructions.html')


# Self-care routes

@app.route('/login', methods=['GET', 'POST'])
def login():
    """Route for self-care login."""
    form = LoginForm()

    if form.validate_on_submit():
        # get customer login credentials
        customer = CustomerLogin.query.filter_by(
            customer_no=form.customer_no.data
        ).first()

        redirect_to = None

        # valid customer and valid password
        if customer is not None and customer.password_hash is not None:
            # verify password
            pwd_verified = pbkdf2_sha256.verify(
                str(form.password.data),
                customer.password_hash
            )
            # condition based on password sanity
            if pwd_verified:
                session['user_logged_in'] = True
                redirect_to = 'portal'
                # store customer number in session
                session['portal_customer_no'] = customer.customer_no
            else:
                redirect_to = 'login'
                flash(INCORRECT_PWD, 'danger')

        # non-registered customer
        elif customer is not None and customer.password_hash is None:
            redirect_to = 'register'
            flash(NON_REGISTERED_USER, 'danger')

        # invalid customer
        else:
            redirect_to = 'login'
            flash(USER_NOT_FOUND_IN_DB, 'danger')

        return redirect(url_for(redirect_to))

    # user logged in
    if session.get('user_logged_in'):
        return redirect(url_for('portal'))
    # user not logged in
    else:
        return render_template(
            'login.html',
            form=form
        )


@app.route('/logout')
def logout():
    """Route for self-care logout."""
    # user logged in already
    if session.get('user_logged_in'):
        flash(SUCCESSFUL_LOGOUT, 'success')
        # revoke session entry
        session['user_logged_in'] = False
        # remove portal customer data storage
        session.pop('portal_customer_no', None)
        session.pop('portal_customer_data', None)
        session.pop('portal_order_id', None)
        session.pop('portal_plan_code', None)
        session.pop('portal_open_ticket_no', None)
    # user not logged in (invalid access to route)
    elif not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')

    return redirect(url_for('login'))


@app.route('/get_customer_number', methods=['GET', 'POST'])
def get_cust_no():
    """Route for getting customer number."""
    form = GetCustomerNumberForm()

    if form.validate_on_submit():
        user = form.username.data
        ip_addr = form.ip_address.data

        # query with `or` condition
        customer = CustomerInfo.query.filter(
            or_(
                CustomerInfo.user_name == user,
                CustomerInfo.ip_addr == ip_addr
            )
        ).first()

        # credentials okay and data available
        if customer is not None and customer.mobile_no is not None:
            # send SMS
            mobile_no = customer.mobile_no.strip()
            sms_msg = SMS_CUSTOMER_NO.format(customer.customer_no)

            successful = send_sms(
                app.config['SMS_URL'],
                {
                    'username': app.config['SMS_USERNAME'],
                    'password': app.config['SMS_PASSWORD'],
                    'from': app.config['SMS_SENDER'],
                    'to': '91{}'.format(mobile_no),
                    'text': sms_msg,
                }
            )

            if successful:
                text = CUSTOMER_NO_SENT
                status = 'success'

            else:
                text = CUSTOMER_NO_NOT_SENT
                status = 'danger'

            flash(text, status)

        # mobile number not available
        elif customer is not None and customer.mobile_no is None:
            flash(NO_MOBILE_NO, 'danger')
        # invalid credentials
        elif customer is None:
            flash(INVALID_CUSTOMER, 'danger')

        return redirect(url_for('get_cust_no'))

    # GET request
    return render_template(
        'customer_no.html',
        form=form
    )


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Route for self-care registration."""
    form = RegistrationForm()

    if form.validate_on_submit():
        # get customer from login db
        customer = CustomerLogin.query.filter_by(
            customer_no=form.customer_no.data
        ).first()

        redirect_to = None

        # valid customer and valid password
        if customer is not None and customer.password_hash is not None:
            redirect_to = 'login'
            flash(ALREADY_REGISTERED, 'info')

        # non-registered customer
        elif customer is not None and customer.password_hash is None:
            # get customer info
            customer_info = CustomerInfo.query.filter_by(
                customer_no=form.customer_no.data
            ).first()

            # mobile no. exists in db
            if customer_info.mobile_no is not None:
                # generate OTP
                totp = TOTPFACTORY.new()
                session['otp_data'] = totp.to_dict()
                session['customer_no'] = form.customer_no.data
                redirect_to = 'verify_otp'

                # send SMS
                mobile_no = customer_info.mobile_no.strip()
                sms_msg = SMS_REG_OTP.format(totp.generate().token)

                successful = send_sms(
                    app.config['SMS_URL'],
                    {
                        'username': app.config['SMS_USERNAME'],
                        'password': app.config['SMS_PASSWORD'],
                        'from': app.config['SMS_SENDER'],
                        'to': '91{}'.format(mobile_no),
                        'text': sms_msg,
                    }
                )

                # successfully sent OTP
                if successful:
                    text = OTP_SENT
                    status = 'success'

                # OTP not sent
                else:
                    text = OTP_NOT_SENT
                    status = 'danger'

                    flash(text, status)

            # mobile no. does not exist in db
            elif customer_info.mobile_no is None:
                flash(NO_MOBILE_NO, 'danger')

        # invalid customer
        elif customer is None:
            redirect_to = 'register'
            flash(USER_NOT_FOUND_IN_DB, 'danger')

        return redirect(url_for(redirect_to))

    return render_template(
        'register.html',
        form=form
    )


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot():
    """Route for generating new password for self-care."""
    form = ForgotPasswordForm()

    if form.validate_on_submit():
        # get customer login credentials
        customer = CustomerLogin.query.filter_by(
            customer_no=form.customer_no.data
        ).first()

        redirect_to = None

        # valid customer and valid password
        if customer is not None and customer.password_hash is not None:
            # generate OTP
            totp = TOTPFACTORY.new()
            session['otp_data'] = totp.to_dict()
            session['customer_no'] = form.customer_no.data
            redirect_to = 'verify_otp'

            # send SMS
            customer_info = CustomerInfo.query.filter_by(
                customer_no=form.customer_no.data
            ).first()
            mobile_no = customer_info.mobile_no.strip()
            sms_msg = SMS_PWD_RESET_OTP.format(totp.generate().token)

            successful = send_sms(
                app.config['SMS_URL'],
                {
                    'username': app.config['SMS_USERNAME'],
                    'password': app.config['SMS_PASSWORD'],
                    'from': app.config['SMS_SENDER'],
                    'to': '91{}'.format(mobile_no),
                    'text': sms_msg,
                }
            )

            if successful:
                text = OTP_SENT
                status = 'success'

            else:
                text = OTP_NOT_SENT
                status = 'danger'

            flash(text, status)

        # non-registered customer
        elif customer is not None and customer.password_hash is None:
            redirect_to = 'register'
            flash(NON_REGISTERED_USER, 'danger')

        # invalid customer
        else:
            redirect_to = 'forgot'
            flash(USER_NOT_FOUND_IN_DB, 'danger')

        return redirect(url_for(redirect_to))

    return render_template(
        'forgot_password.html',
        form=form
    )


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """Route for verifying OTP."""
    form = OTPVerificationForm()

    if form.validate_on_submit():
        otp = form.otp.data

        redirect_to = None

        # Verify OTP
        totp = TOTPFACTORY.from_dict(session['otp_data'])

        try:
            totp.verify(str(otp), totp)
        except (MalformedTokenError, TokenError) as _:
            otp_verified = False
        else:
            otp_verified = True

        # destroy OTP data
        session.pop('otp_data', None)

        if otp_verified:
            redirect_to = 'set_password'
        elif not otp_verified:
            session.pop('customer_no', None)
            redirect_to = 'login'
            flash(OTP_VERIFY_FAILED, 'danger')

        return redirect(url_for(redirect_to))

    return render_template(
        'verify_otp.html',
        form=form
    )


@app.route('/set_password', methods=['GET', 'POST'])
def set_password():
    """Route for setting new password for self-care."""
    form = SetPasswordForm()

    if form.validate_on_submit():
        customer = CustomerLogin.query.filter_by(
            customer_no=session['customer_no']
        ).first()

        # generate hashed password and store
        hashed_pwd = pbkdf2_sha256.hash(str(form.password.data))
        customer.password_hash = hashed_pwd

        # make synchronous call to save password
        db = current_app.extensions['sqlalchemy'].db
        db.session.add(customer)
        db.session.commit()

        # remove customer number from session storage
        session.pop('customer_no', None)

        flash(SUCCESSFUL_PWD_SAVE, 'success')
        return redirect(url_for('login'))

    return render_template(
        'set_password.html',
        form=form
    )


@app.route('/update_mobile_number', methods=['GET', 'POST'])
def update_mobile_number():
    """Route for requesting mobile number update."""
    form = MobileNumberUpdateRequestForm()

    if form.validate_on_submit():
        form_data = {
            'old_phone_no': form.old_phone_no.data,
            'new_phone_no': form.new_phone_no.data,
            'username_or_ip_address': form.username_or_ip_address.data,
            'postal_code': form.postal_code.data,
        }

        # add data to db async
        add_mobile_number_update_request_to_db(form_data)

        flash(SUCCESSFUL_MOBILE_NO_UPDATE_REQUEST, 'success')
        return redirect(url_for('update_mobile_number'))

    return render_template(
        'update_mobile_number.html',
        form=form
    )


# Self-care portal views

@app.route('/portal/', methods=['GET'])
def portal():
    """Route for self-care portal."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))

    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        # check if session variable exists for customer data
        if not session.get('portal_customer_data'):
            # Get customer info
            user_info = GetCustomerInfo(app)
            user_info.request(session['portal_customer_no'])
            user_info.response()
            # add customer data to session for quick access
            session['portal_customer_data'] = user_info.to_dict()

        plans = {
            row.plan_code: row
            for row in TariffInfo.query.options(FromCache(CACHE)).all()
        }
        # Get active plans for the user
        # {plan_name: validity_period }
        active_plans = {
            plans[plan_code].plan_name: validity_period
            for (_, plan_code, validity_period) in
            session['portal_customer_data']['active_plans']
            if plan_code in plans
        }

        # Get GSTIN for customer
        customer_gst = GSTUpdateRequest.query.filter(
            and_(
                GSTUpdateRequest.customer_no == \
                session['portal_customer_no'],
                GSTUpdateRequest.status == 'REGISTERED'
            )
        ).first()

        return render_template(
            'portal.html',
            cust_no=session['portal_customer_no'],
            cust_data=session['portal_customer_data'],
            gstin=customer_gst,
            active_plans=active_plans
        )


@app.route('/portal/recharge', methods=['GET', 'POST'])
def recharge():
    """Route for self-care portal recharge."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        if request.method == 'GET':
            plans = {
                row.plan_code: row
                for row in TariffInfo.query.options(FromCache(CACHE)).all()
            }
            # Get active plans for the user
            # {plan_name: (price, validity, plan_code)}
            active_plans = {
                plans[plan_code].plan_name: (
                    plans[plan_code].price, validity_period, plan_code
                )
                for (_, plan_code, validity_period) in
                session['portal_customer_data']['active_plans']
                if plan_code in plans
            }
            # Get inactive plans for the user
            # {plan_name: (price, validity, plan_code) }
            inactive_plans = {
                plans[plan_code].plan_name: (
                    plans[plan_code].price, validity_period, plan_code
                )
                for (_, plan_code, validity_period) in
                session['portal_customer_data']['inactive_plans']
                if plan_code in plans
            }

            return render_template(
                'recharge.html',
                active_plans=active_plans,
                inactive_plans=inactive_plans,
            )

        elif request.method == 'POST':
            # store amount in session
            session['portal_amount'] = request.form['amount']
            # store selected plan code in session
            session['portal_plan_code'] = request.form['plan_code']
            # generate and store a transaction id
            session['portal_order_id'] = order_no_gen()

            # Check payment gateway
            if request.form['gateway'] == 'paytm':
                # Get Paytm form data
                form_data = initiate_transaction(
                    order_id=session['portal_order_id'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=\
                    session['portal_customer_data']['contact_no'],
                    amount=request.form['amount'],
                    # _ is used as the delimiter; check Paytm docs
                    pay_source='portal_recharge',
                )

            elif request.form['gateway'] == 'razorpay':
                # Get Razorpay form data
                form_data = make_order(
                    order_id=session['portal_order_id'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=\
                    session['portal_customer_data']['contact_no'],
                    customer_email=app.config['RAZORPAY_DEFAULT_MAIL'],
                    amount=request.form['amount'],
                    # list is used for passing data; check Razorpay docs
                    pay_source=['portal', 'recharge'],
                )

                # store Razorpay order id for verification later
                session['razorpay_order_id'] = form_data['order_id']

            return render_template(
                '{}_pay.html'.format(request.form['gateway']),
                form=form_data,
            )


@app.route('/portal/add_plan', methods=['GET', 'POST'])
def add_plan():
    """Route for self-care portal add plan."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        if request.method == 'GET':
            zone_id = \
                CustomerInfo.query.\
                options(FromCache(CACHE)).\
                filter_by(customer_no=session['portal_customer_no']).\
                first().zone_id

            # Get eligible plan codes for the user
            zone_eligible_plan_codes = [
                zone.plan_code_mqs
                for zone in ZoneIDWithPlanCode.query.\
                filter(
                    and_(
                        ZoneIDWithPlanCode.zone_id == zone_id,
                        ZoneIDWithPlanCode.status == 'ACTIVE'
                    )
                ).all()
            ]

            plans = {
                row.plan_code: row
                for row in TariffInfo.query.options(FromCache(CACHE)).all()
            }

            # Get available plans for the user
            # {plan_name: (price, plan_code) }
            available_plan_codes = \
                set(plans.keys()).\
                difference(session['portal_customer_data']['all_plans']).\
                intersection(zone_eligible_plan_codes)

            available_plans = {
                plans[plan_code].plan_name: (
                    plans[plan_code].price,
                    plan_code,
                    plans[plan_code].speed,
                    plans[plan_code].validity,
                    plans[plan_code].plan_type,
                )
                for plan_code in available_plan_codes
            }

            return render_template(
                'add_plan.html',
                available_plans=available_plans,
            )

        elif request.method == 'POST':
            # store amount in session
            session['portal_amount'] = request.form['amount']
            # store selected plan code in session
            session['portal_plan_code'] = request.form['plan_code']
            # generate and store a transaction id
            session['portal_order_id'] = order_no_gen()

            # Check payment gateway
            if request.form['gateway'] == 'paytm':
                # Get Paytm form data
                form_data = initiate_transaction(
                    order_id=session['portal_order_id'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=\
                    session['portal_customer_data']['contact_no'],
                    amount=request.form['amount'],
                    # _ is used as the delimiter; check Paytm docs
                    pay_source='portal_addplan',
                )

            elif request.form['gateway'] == 'razorpay':
                # Get Razorpay form data
                form_data = make_order(
                    order_id=session['portal_order_id'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=\
                    session['portal_customer_data']['contact_no'],
                    customer_email=app.config['RAZORPAY_DEFAULT_MAIL'],
                    amount=request.form['amount'],
                    # list is used for passing data; check Razorpay docs
                    pay_source=['portal', 'addplan'],
                )

                # store Razorpay order id for verification later
                session['razorpay_order_id'] = form_data['order_id']

            return render_template(
                '{}_pay.html'.format(request.form['gateway']),
                form=form_data,
            )


@app.route('/portal/receipt/<order_id>')
def portal_receipt(order_id):
    """Route to transaction receipt."""

    return render_template(
        'portal_receipt.html',
        customer_no=session['portal_customer_no'],
        customer_name=session['portal_customer_data']['name'],
        amount=session['portal_amount'],
        date_and_time=request.args.get('txn_datetime'),
        txn_status=request.args.get('status'),
        txn_no=order_id
    )


@app.route('/portal/docket')
def docket():
    """Route for self-care portal docket."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        tickets = Ticket.query.filter_by(
            customer_no=session['portal_customer_no']
        ).all()

        open_tickets = [ticket for ticket in tickets if ticket.status == 'Open']
        closed_tickets = [
            ticket for ticket in tickets if ticket.status == 'Closed'
        ]

        # save open ticket no in session
        if open_tickets:
            session['portal_open_ticket_no'] = open_tickets[0].ticket_no

        # set if open dockets exist
        return render_template(
            'docket.html',
            tickets=tickets,
            open_tickets=open_tickets,
            closed_tickets=closed_tickets,
        )


@app.route('/portal/new_docket', methods=['GET', 'POST'])
def new_docket():
    """Route for self-care new docket."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        # open ticket exists
        if not session.get('portal_open_ticket_no'):
            form = NewTicketForm()
            form.nature.choices = [
                (row.ticket_nature_code, row.ticket_nature_desc)
                for row in TicketInfo.query.options(FromCache(CACHE)).all()
            ]

            if form.validate_on_submit():
                nature_code = form.nature.data
                # query category from db
                entry = TicketInfo.query.options(FromCache(CACHE)).filter_by(
                    ticket_nature_code=nature_code
                ).first()
                category_code = entry.ticket_category_code
                category_desc = entry.ticket_category_desc
                nature_desc = entry.ticket_nature_desc

                remarks = form.remarks.data

                # Generate ticket in MQS
                register_ticket = RegisterTicket(app)
                register_ticket.request(
                    cust_id=session['portal_customer_no'],
                    category=category_code,
                    description=remarks,
                    nature=nature_code,
                )
                register_ticket.response()

                # check if success
                if register_ticket.error_no == '0':
                    ticket_no = register_ticket.ticket_no

                    # send data to db
                    ticket_data = {
                        'customer_no': session['portal_customer_no'],
                        'ticket_no': ticket_no,
                        'category_desc': category_desc,
                        'nature_desc': nature_desc,
                        'remarks': remarks,
                        'opening_date': datetime.now().astimezone().date(),
                        'opening_time': datetime.now().astimezone().time()
                    }

                    # add new ticket to db async
                    add_new_ticket_to_db(ticket_data)

                    msg = SUCCESSFUL_DOCKET_GEN
                    status = 'success'
                else:
                    msg = UNSUCCESSFUL_DOCKET_GEN
                    status = 'danger'

                flash(msg, status)
                return redirect(url_for('docket'))

            # GET request
            return render_template(
                'new_docket.html',
                form=form,
                allowed=True,
            )

        # has open ticket
        elif session.get('portal_open_ticket_no'):
            return render_template(
                'new_docket.html',
                allowed=False,
            )


@app.route('/portal/close_docket')
def close_docket():
    """Route for self-care close docket."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        # open ticket exists
        if session.get('portal_open_ticket_no'):
            ticket_no = session.get('portal_open_ticket_no')

            # Close ticket in MQS
            close_ticket = CloseTicket(app)
            close_ticket.request(ticket_no)
            close_ticket.response()

            # check if success or closed by non-customer
            if close_ticket.error_no == '0' or close_ticket.error_no == '99070':
                ticket = Ticket.query.filter_by(
                    ticket_no=session['portal_open_ticket_no']
                ).first()
                ticket.status = 'Closed'
                ticket.closing_date = datetime.now().astimezone().date()
                ticket.closing_time = datetime.now().astimezone().time()
                # close ticket in db
                db = current_app.extensions['sqlalchemy'].db
                db.session.add(ticket)
                db.session.commit()

                msg = SUCCESSFUL_DOCKET_CLOSE.format(ticket_no)
                status = 'success'

                # remove data from session variable
                session.pop('portal_open_ticket_no', None)

            else:
                msg = UNSUCCESSFUL_DOCKET_CLOSE.format(ticket_no)
                status = 'danger'

        # no open ticket exists
        elif not session.get('portal_open_ticket_no'):
            msg = NO_DOCKETS
            status = 'danger'

        flash(msg, status)
        return redirect(url_for('docket'))


@app.route('/portal/usage')
def usage():
    """Route for self-care portal usage."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        # Get customer username
        customer_username = CustomerInfo.query.options(FromCache(CACHE)).\
            filter_by(customer_no=session['portal_customer_no']).\
            first().user_name

        # Get start and end dates for usage data
        today = datetime.now().astimezone().date()
        past = today - timedelta(days=90)

        # Get usage data using API call
        usage_details = GetUsageDetails()
        usage_details.request(
            user_name=customer_username,
            start_date=past.strftime("%d%m%Y"),
            end_date=today.strftime("%d%m%Y")
        )
        usage_details.response()

        # Get page, per page and offset parameter names
        page, per_page, offset = get_page_args(
            page_parameter='page',
            per_page_parameter='per_page'
        )

        # Get required entries
        pagination_usage = get_usage(usage_details.usage, offset, per_page)

        pagination = Pagination(
            page=page,
            per_page=per_page,
            total=len(usage_details.usage),
            css_framework='bootstrap4',
            prev_label='&lt',
            next_label='&gt'
        )

        return render_template(
            'usage.html',
            usage_details=pagination_usage,
            page=page,
            per_page=per_page,
            pagination=pagination
        )


@app.route('/portal/transaction_history')
def transaction_history():
    """Route for self-care transaction history."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        # Get page number
        page_num = request.args.get('page', type=int, default=1)

        # Retrieve data from db
        transactions = RechargeEntry.query.filter_by(
            customer_no=session['portal_customer_no']
        ).paginate(per_page=10, page=page_num, error_out=False)

        return render_template(
            'transaction_history.html',
            transactions=transactions,
            page=page_num
        )


@app.route('/portal/wishtalk', methods=['GET'])
def wishtalk():
    """Route for self-care Wishtalk."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        # Get active plans for the user
        # [(plan_code, validity_end_date)]
        active_plans = [
            (plan_code, validity_period.split(' - ')[1])
            for (_, plan_code, validity_period) in
            session['portal_customer_data']['active_plans']
        ]

        # check if there is active plan
        if active_plans:
            # get last active plan
            last_active_plan = active_plans[-1]

            # get softphone limit
            softphone_limit = TariffInfo.query.\
                filter_by(plan_code=last_active_plan[0]).\
                first().softphone

            # current softphone allotment
            current_softphone_allotment = SoftphoneEntry.query.\
                filter(
                    or_(
                        and_(
                            SoftphoneEntry.cust_no == \
                            session['portal_customer_no'],
                            SoftphoneEntry.softphone_status == 'ACTIVE'
                        ),
                        and_(
                            SoftphoneEntry.cust_no == \
                            session['portal_customer_no'],
                            SoftphoneEntry.softphone_status == 'DEACTIVE'
                        )
                    )
                ).all()

            add_softphone_form = AddSoftphoneForm()

        elif not active_plans:
            softphone_limit = None
            current_softphone_allotment = None
            add_softphone_form = None


        return render_template(
            'wishtalk.html',
            no_of_softphone_allowed=softphone_limit,
            no_of_softphone_allotted=\
            len(current_softphone_allotment) if current_softphone_allotment \
            else 0,
            softphone_data=current_softphone_allotment,
            add_softphone_form=add_softphone_form
        )


@app.route('/portal/add_softphone', methods=['POST'])
def wishtalk_add_softphone():
    """Route for self-care portal softphone addition."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # Get active plans for the user
        # [(plan_code, validity_end_date)]
        active_plans = [
            (plan_code, validity_period.split(' - ')[1])
            for (_, plan_code, validity_period) in
            session['portal_customer_data']['active_plans']
        ]
        # get last active plan and expiry
        last_active_plan = active_plans[-1]
        last_active_plan_expiry = datetime.strptime(
            last_active_plan[1], '%d-%m-%Y'
        ).date()
        # get softphone limit
        softphone_limit = TariffInfo.query.\
            filter_by(plan_code=last_active_plan[0]).\
            first().softphone

        # current softphone allotment
        current_softphone_allotment = SoftphoneEntry.query.\
            filter(
                or_(
                    and_(
                        SoftphoneEntry.cust_no == \
                        session['portal_customer_no'],
                        SoftphoneEntry.softphone_status == 'ACTIVE'
                    ),
                    and_(
                        SoftphoneEntry.cust_no == \
                        session['portal_customer_no'],
                        SoftphoneEntry.softphone_status == 'DEACTIVE'
                    )
                )
            ).all()

        add_softphone_form = AddSoftphoneForm()

        if add_softphone_form.validate_on_submit():
            # create session to perform one-step read and write transaction
            db_session = SignallingSession(
                current_app.extensions['sqlalchemy'].db
            )

            # DATABASE OPERATION
            # initiate transaction
            try:
                # get FREE and NORMAL softphone number
                free_softphone_number = db_session.query(SoftphoneNumber).\
                    filter(
                        and_(
                            SoftphoneNumber.softphone_status == 'FREE',
                            SoftphoneNumber.category_type == 'NORMAL'
                        )
                    ).order_by(SoftphoneNumber.id.asc()).first()
                # store the number
                softphone_number = free_softphone_number.softphone_no
                # get the category
                softphone_category = free_softphone_number.category_type
                # allot the number
                free_softphone_number.softphone_status = 'ALLOTTED'
                # commit changes
                db_session.commit()

            # rollback on failure
            except:
                softphone_number = None
                db_session.rollback()

            # close connection (fallback in case of failure)
            finally:
                db_session.close()

            # API CALL
            # successful allotment of softphone number
            if softphone_number:
                # call API for softphone allotment
                success = add_softphone(
                    url=app.config['SOFTPHONE_URL'],
                    softphone_number=softphone_number,
                    password=add_softphone_form.password.data,
                    user_name=add_softphone_form.name.data
                )

                # softphone addition API call successful
                if success:
                    # set mobile number in case of fixed line
                    if not add_softphone_form.mobile_number.data:
                        mobile_no = CustomerInfo.query.filter_by(
                            customer_no=session['portal_customer_no']
                        ).first().mobile_no.strip()

                    else:
                        mobile_no = add_softphone_form.mobile_number.data

                    # generate hash from the raw password
                    hashed_pwd = pbkdf2_sha256.hash(
                        str(add_softphone_form.password.data)
                    )

                    # create data for db entry
                    data = {
                        'customer_no': session['portal_customer_no'],
                        'customer_name': \
                        session['portal_customer_data']['name'],
                        'user_name': add_softphone_form.name.data,
                        'customer_mobile_no': mobile_no,
                        'password_hash': hashed_pwd,
                        'softphone_number': softphone_number,
                        'softphone_os': \
                        add_softphone_form.softphone_platform.data,
                        'create_date': datetime.now().astimezone().date(),
                        'expiry_date': last_active_plan_expiry,
                        'status': 'ACTIVE',
                        'category': softphone_category,
                    }

                    # add softphone allotment to db async
                    add_async_softphone_allotment.delay(data)

                    # set SMS message based on platform
                    if add_softphone_form.softphone_platform.data == 'Android':
                        sms_msg = SUCCESSFUL_SOFTPHONE_SMS_ANDROID.format(
                            softphone_number,
                            add_softphone_form.password.data
                        )
                    elif add_softphone_form.softphone_platform.data == 'iOS':
                        sms_msg = SUCCESSFUL_SOFTPHONE_SMS_IOS.format(
                            softphone_number,
                            add_softphone_form.password.data
                        )
                    elif add_softphone_form.softphone_platform.data == \
                         'Fixed Line':
                        sms_msg = SUCCESSFUL_SOFTPHONE_SMS_FIXED_LINE.format(
                            softphone_number,
                            add_softphone_form.password.data
                        )

                    # send SMS
                    successful = send_sms(
                        app.config['SMS_URL'],
                        {
                            'username': app.config['SMS_USERNAME'],
                            'password': app.config['SMS_PASSWORD'],
                            'from': app.config['SMS_SENDER'],
                            'to': '91{}'.format(mobile_no),
                            'text': sms_msg,
                        }
                    )

                    # SMS sent
                    if successful:
                        text = SUCCESSFUL_SOFTPHONE_ALLOTMENT
                        status = 'success'

                    # SMS not sent
                    elif not successful:
                        text = UNSUCCESSFUL_SOFTPHONE_SMS
                        status = 'danger'

                    flash(text, status)

                # softphone addition API call unsuccessful
                elif not success:
                    flash(UNSUCCESSFUL_SOFTPHONE_ALLOTMENT, 'danger')

            # unsuccessful allotment of softphone number
            elif not softphone_number:
                flash(UNSUCCESSFUL_SOFTPHONE_ALLOTMENT, 'danger')

        return render_template(
            'wishtalk.html',
            no_of_softphone_allowed=softphone_limit,
            no_of_softphone_allotted=\
            len(current_softphone_allotment) if current_softphone_allotment \
            else 0,
            softphone_data=current_softphone_allotment,
            add_softphone_form=add_softphone_form
        )


@app.route('/portal/change_password', methods=['GET', 'POST'])
def change_password():
    """Route for self-care portal password change."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        form = ChangePasswordForm()

        if form.validate_on_submit():
            customer = CustomerLogin.query.filter_by(
                customer_no=session['portal_customer_no']
            ).first()

            # verify old password
            pwd_verified = pbkdf2_sha256.verify(
                str(form.old_password.data),
                customer.password_hash
            )

            # if old password is verified
            if pwd_verified:
                # check if the old and new passwords are same
                if form.old_password.data == form.new_password.data:
                    flash(SET_NEW_PWD, 'danger')
                else:
                    # generate new hashed password and store
                    hashed_pwd = pbkdf2_sha256.hash(str(form.new_password.data))
                    customer.password_hash = hashed_pwd

                    # make synchronous call to save password
                    db = current_app.extensions['sqlalchemy'].db
                    db.session.add(customer)
                    db.session.commit()

                    flash(NEW_PWD_SET, 'success')
            # old password is incorrect
            else:
                flash(INCORRECT_OLD_PWD, 'danger')

            return redirect(url_for('change_password'))

        # GET request
        return render_template(
            'change_password.html',
            form=form,
        )


@app.route('/portal/update_profile', methods=['GET', 'POST'])
def update_profile():
    """Route for self-care portal profile update."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        form = UpdateProfileForm()

        if form.validate_on_submit():
            # Update profile details in MQS
            profile = UpdateProfile(app)
            profile.request(
                cust_id=session['portal_customer_no'],
                first_name=session['portal_customer_data']['first_name'],
                last_name=session['portal_customer_data']['last_name'],
                email=form.new_email_address.data,
                mobile_no=form.new_phone_no.data
            )
            profile.response()

            # verify MQS ModifyCustomer status
            db_status, flash_msg, msg_status = verify_mqs_updateprofile(profile)

            form_data = {
                'customer_no': session['portal_customer_no'],
                'new_phone_no': form.new_phone_no.data,
                'new_email': form.new_email_address.data,
                'status': db_status,
                'request_date': datetime.now().astimezone().date(),
                'request_time': datetime.now().astimezone().time(),
            }

            # add data to db async
            add_profile_update_request_to_db.delay(form_data)

            flash(flash_msg, msg_status)
            return redirect(url_for('update_profile'))

        # GET request
        return render_template(
            'update_profile.html',
            form=form,
        )


@app.route('/portal/update_gst', methods=['GET', 'POST'])
def update_gst():
    """Route for self-care GST information update."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash(LOG_IN_FIRST, 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # keep the session alive
        session.modified = True

        form = UpdateGSTForm()

        if form.validate_on_submit():
            form_data = {
                'customer_no': session['portal_customer_no'],
                'gst_no': form.gst_no.data,
                'request_date': datetime.now().astimezone().date(),
                'request_time': datetime.now().astimezone().time(),
            }

            # add data to db async
            add_gst_update_request_to_db.delay(form_data)

            flash(SUCCESSFUL_GST_UPDATE_REQUEST, 'success')
            return redirect(url_for('update_gst'))

        # GET request
        return render_template(
            'update_gst.html',
            form=form,
        )
