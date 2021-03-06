# -*- coding: utf-8 -*-

"""Views for the website."""


import json
import random
import re
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
from website.mqs_api import *
from website.models import (
    FAQ, AvailableLocations, BestPlans, CarouselImages, CustomerInfo,
    CustomerLogin, Downloads, GSTUpdateRequest, JobVacancy, RechargeEntry,
    RegionalOffices, Services, SoftphoneEntry, SoftphoneNumber, TariffInfo,
    Ticket, TicketInfo, Ventures, Voucher, VoucherEntry, VoucherPackage,
    VoucherProvider, ZoneIDWithPlanCode)
from website.paytm_utils import (
    initiate_transaction, verify_final_status, verify_transaction)
from website.razorpay_utils import get_notes, make_order, verify_signature
from website.softphone_utils import *
from website.utils import *
from website.tasks import (
    add_async_softphone_allotment, add_async_voucher_allotment,
    add_email_address_update_request_to_db, add_gst_update_request_to_db,
    add_mobile_number_update_request_to_db, add_new_connection_data_to_db,
    add_new_ticket_to_db, add_profile_update_request_to_db, add_txn_data_to_db,
    send_async_new_connection_mail, update_profile_in_db)


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
    # POST request for insta-recharge
    if form.validate_on_submit():
        user = form.user_id.data
        # Get customer info
        customer = CustomerInfo.query.filter_by(customer_no=user).first()
        # Customer data available in the db
        if customer is not None:
            # Get active plans (ref no. of this API call is passed forward)
            user_contracts = ContractsByKey(app)
            user_contracts.request(user)
            user_contracts.response()
            # No active plans
            if not user_contracts.active_plans:
                flash(NO_ACTIVE_PLANS, 'danger')
                return redirect(url_for('index'))
            # Get all plans
            plans = {
                row.plan_code: row
                for row in TariffInfo.query.options(FromCache(CACHE)).all()
            }
            # Get eligible active plans for the user
            # {plan_name: (price, plan_end_date, plan_code)}
            active_plans = {
                plans[plan_code].plan_name: (
                    plans[plan_code].price, plan_end_date, plan_code
                )
                for (plan_code, plan_end_date) in
                user_contracts.active_plans if plan_code in plans
            }
            # Active plans sent to insta-recharge
            return redirect(
                url_for(
                    'insta_recharge',
                    order_id=user_contracts.ref_no,
                    customer_no=customer.customer_no,
                    customer_name=customer.customer_name,
                    customer_mobile_no=customer.mobile_number,
                    active_plans=json.dumps(active_plans),
                )
            )
        # user data not available in the db; might be a new user
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
    if request.method == 'POST':
        # retrieve amount for plan code selected
        amount = TariffInfo.query.options(FromCache(CACHE)).\
            filter_by(plan_code=request.form['plan_code']).first_or_404().price
        # store amount in session
        session['insta_amount'] = format(amount * 1.18, '.2f')
        # store customer number in session
        session['insta_customer_no'] = request.form['customer_no']
        # store selected plan code in session
        session['insta_plan_code'] = request.form['plan_code']
        # store order id in session
        session['insta_order_id'] = order_id

        # Check payment gateway
        if request.form['gateway'] == 'paytm':
            form_data = initiate_transaction(
                order_id=order_id,
                customer_no=request.form['customer_no'],
                customer_mobile_no=request.form['customer_mobile_no'],
                amount=session['insta_amount'],
                # _ is used as the delimiter; check paytm_utils
                pay_source='insta_recharge',
            )
        elif request.form['gateway'] == 'razorpay':
            form_data = make_order(
                order_id=order_id,
                customer_no=request.form['customer_no'],
                customer_mobile_no=request.form['customer_mobile_no'],
                customer_email=app.config['RAZORPAY_DEFAULT_MAIL'],
                amount=session['insta_amount'],
                # List is used for passing data; check razorpay_utils
                pay_source=['insta', 'recharge'],
            )
            # Store Razorpay order id for verification later
            session['razorpay_order_id'] = form_data['order_id']

        return render_template(
            '{}_pay.html'.format(request.form['gateway']),
            form=form_data,
        )

    return render_template(
        'insta_recharge.html',
        customer_no=request.args.get('customer_no', None),
        customer_name=request.args.get('customer_name', None),
        customer_mobile_no=request.args.get('customer_mobile_no', None),
        active_plans=json.loads(request.args.get('active_plans', 'null'))
    )


@app.route('/verify/<gateway>', methods=['GET', 'POST'])
@CSRF.exempt
def verify_response(gateway):
    """Route for verifying response for payment."""
    if request.method == 'POST':
        # Check payment gateway
        if gateway == 'paytm':
            session_var_prefix, txn_type = \
                request.form['MERC_UNQ_REF'].split('_')
            # Get zone id for table entry
            zone_id = CustomerInfo.query.\
                options(FromCache(CACHE)).\
                filter_by(
                    customer_no=session[f'{session_var_prefix}_customer_no']
                ).first().zone_id
            # Store response data
            data = {
                'customer_no': session[f'{session_var_prefix}_customer_no'],
                'customer_zone_id': zone_id,
                'wishnet_order_id': session[f'{session_var_prefix}_order_id'],
                'payment_gateway': 'Paytm',
                'txn_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'txn_date': datetime.now().astimezone().date(),
                'txn_time': datetime.now().astimezone().time(),
                'plan_code': session[f'{session_var_prefix}_plan_code'],
            }
            # Initial checksum verification
            verified = verify_transaction(request.form)
            # Check verification success
            if verified:
                data.update(txn_order_id=request.form['TXNID'])
                # Final status verification
                final_status_code = verify_final_status(
                    session[f'{session_var_prefix}_order_id']
                )
                # Check if transaction successful
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
            # Checksum hash verification failure; data tampered
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

        elif gateway == 'razorpay':
            # Verify signature
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
            # Get metadata of order (skipping customer no.)
            _, session_var_prefix, txn_type = get_notes(
                session['razorpay_order_id']
            )
            # Get zone id for table entry
            zone_id = CustomerInfo.query.\
                options(FromCache(CACHE)).\
                filter_by(
                    customer_no=session[f'{session_var_prefix}_customer_no']
                ).first().zone_id
            # Store response data
            data = {
                'customer_no': session[f'{session_var_prefix}_customer_no'],
                'customer_zone_id': zone_id,
                'wishnet_order_id': session[f'{session_var_prefix}_order_id'],
                'payment_gateway': 'Razorpay',
                'txn_order_id': session['razorpay_order_id'],
                'txn_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'txn_date': datetime.now().astimezone().date(),
                'txn_time': datetime.now().astimezone().time(),
                'plan_code': session[f'{session_var_prefix}_plan_code'],
            }
            # Remove Razorpay order id from session storage
            session.pop('razorpay_order_id', None)
            # Signature verification success
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

            # Signature verification failure; data tampered
            elif not verified:
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

        # Add transaction data to db asynchronously
        add_txn_data_to_db.delay(data)

        return redirect(
            url_for(
                f'{session_var_prefix}_receipt',
                order_id=data['wishnet_order_id'],
                status=status,
                txn_datetime=data['txn_datetime'],
                customer_no=data['customer_no']
            )
        )

    # handle Razorpay transaction cancel
    elif request.method == 'GET':
        # Get metadata of order (skipping customer no. and txn type)
        _, session_var_prefix, _ = get_notes(
            session['razorpay_order_id']
        )
        # Get zone id for table entry
        zone_id = CustomerInfo.query.\
            options(FromCache(CACHE)).\
            filter_by(
                customer_no=session[f'{session_var_prefix}_customer_no']
            ).first().zone_id
        # Prepare data to be sent to db
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
            'plan_code': session[f'{session_var_prefix}_plan_code'],
            'topup_ref_id': '',
            'topup_datetime': '',
            'topup_status': '',
            'addplan_ref_id': '',
            'addplan_datetime': '',
            'addplan_status': '',
        }
        # Remove Razorpay order id from session storage
        session.pop('razorpay_order_id', None)

        flash(INCOMPLETE_PAYMENT, 'danger')

        # Add transaction data to db asynchronously
        add_txn_data_to_db.delay(data)

        return redirect(
            url_for(
                f'{session_var_prefix}_receipt',
                order_id=data['wishnet_order_id'],
                status='unsuccessful',
                txn_datetime=data['txn_datetime'],
                customer_no=data['customer_no']
            )
        )


@app.route('/receipt/<order_id>')
def insta_receipt(order_id):
    """Route to transaction receipt."""
    customer_name = CustomerInfo.query.options(FromCache(CACHE)).filter_by(
        customer_no=request.args.get('customer_no')
    ).first_or_404().customer_name

    return render_template(
        'receipt.html',
        customer_no=request.args.get('customer_no'),
        customer_name=customer_name,
        amount=session['insta_amount'],
        date_and_time=request.args.get('txn_datetime'),
        txn_status=request.args.get('status'),
        txn_no=order_id
    )


@app.route('/tariff')
def tariff():
    """Route for tariff."""
    database = current_app.extensions['sqlalchemy'].db

    classes = [cls for cls in database.Model._decl_class_registry.values()
               if isinstance(cls, type) and issubclass(cls, database.Model)]

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
    # POST request for new connection
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
        # Add data to db asynchronously
        add_new_connection_data_to_db.delay(form_data)
        # Send mail asynchronously
        send_async_new_connection_mail.delay(form.email_address.data, query_no)

        flash(SUCCESSFUL_NEW_CONN_REQUEST, 'success')
        return redirect(url_for('new_conn'))
    # GET request
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
    # POST request for login
    if form.validate_on_submit():
        redirect_to = None
        # Get customer login credentials
        customer = CustomerLogin.query.filter_by(
            customer_no=form.customer_no.data
        ).first()
        # Valid customer and valid password
        if customer is not None and customer.password_hash is not None:
            # Verify password
            pwd_verified = pbkdf2_sha256.verify(
                str(form.password.data),
                customer.password_hash
            )
            if pwd_verified:
                redirect_to = 'portal'
                session['user_logged_in'] = True
                session['portal_customer_no'] = customer.customer_no
            else:
                redirect_to = 'login'
                flash(INCORRECT_PWD, 'danger')
        # Non-registered customer
        elif customer is not None and customer.password_hash is None:
            redirect_to = 'register'
            flash(NON_REGISTERED_USER, 'danger')
        # Invalid customer
        else:
            redirect_to = 'login'
            flash(USER_NOT_FOUND_IN_DB, 'danger')

        return redirect(url_for(redirect_to))

    # GET request
    # User logged in
    if session.get('user_logged_in'):
        return redirect(url_for('portal'))
    # User logged out
    return render_template('login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    """Route for self-care logout."""
    # Revoke session entry
    session['user_logged_in'] = False
    # Remove portal customer data storage
    session.pop('portal_customer_no', None)
    session.pop('portal_customer_data', None)
    session.pop('portal_order_id', None)
    session.pop('portal_plan_code', None)
    session.pop('portal_open_ticket_no', None)

    flash(SUCCESSFUL_LOGOUT, 'success')
    return redirect(url_for('login'))


# Helper utilities for self-care portal

@app.route('/get_customer_number', methods=['GET', 'POST'])
def get_cust_no():
    """Route for getting customer number."""
    form = GetCustomerNumberForm()
    # POST request for getting customer number
    if form.validate_on_submit():
        customer = CustomerInfo.query.filter(
            or_(
                CustomerInfo.user_name == form.username.data,
                CustomerInfo.ip_addr == form.ip_address.data
            )
        ).first()
        # Credentials okay and data available
        if customer is not None and customer.mobile_number is not None:
            # Send SMS
            sms_msg = SMS_CUSTOMER_NO.format(customer.customer_no)
            successful_sms = send_sms(
                app.config['SMS_URL'],
                {
                    'username': app.config['SMS_USERNAME'],
                    'password': app.config['SMS_PASSWORD'],
                    'from': app.config['SMS_SENDER'],
                    'to': '91{}'.format(customer.mobile_number),
                    'text': sms_msg,
                }
            )
            # Check whether sms sent successfully
            if successful_sms:
                text = CUSTOMER_NO_SENT
                status = 'success'
            else:
                text = CUSTOMER_NO_NOT_SENT
                status = 'danger'

            flash(text, status)
        # Mobile number not available
        elif customer is not None and customer.mobile_number is None:
            flash(NO_MOBILE_NO, 'danger')
        # Invalid credentials
        elif customer is None:
            flash(INVALID_CUSTOMER, 'danger')

        return redirect(url_for('get_cust_no'))

    # GET request
    return render_template('customer_no.html', form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Route for self-care registration."""
    form = RegistrationForm()
    # POST request for registration
    if form.validate_on_submit():
        redirect_to = None
        # Get customer from login db
        customer = CustomerLogin.query.filter_by(
            customer_no=form.customer_no.data
        ).first()
        # Valid customer and valid password
        if customer is not None and customer.password_hash is not None:
            redirect_to = 'login'
            flash(ALREADY_REGISTERED, 'info')
        # Non-registered customer
        elif customer is not None and customer.password_hash is None:
            # Get customer info
            customer_info = CustomerInfo.query.filter_by(
                customer_no=form.customer_no.data
            ).first()
            # Mobile number exists in db
            if customer_info.mobile_number is not None:
                # Generate OTP
                totp = TOTPFACTORY.new()
                session['otp_data'] = totp.to_dict()
                session['customer_no'] = form.customer_no.data
                # Send SMS
                sms_msg = SMS_REG_OTP.format(totp.generate().token)
                successful_sms = send_sms(
                    app.config['SMS_URL'],
                    {
                        'username': app.config['SMS_USERNAME'],
                        'password': app.config['SMS_PASSWORD'],
                        'from': app.config['SMS_SENDER'],
                        'to': '91{}'.format(customer_info.mobile_number),
                        'text': sms_msg,
                    }
                )
                # OTP sent
                if successful_sms:
                    redirect_to = 'verify_otp'
                    text = OTP_SENT
                    status = 'success'
                # OTP not sent
                else:
                    redirect_to = 'register'
                    text = OTP_NOT_SENT
                    status = 'danger'
                    # Remove OTP and customer data from session
                    session.pop('otp_data', None)
                    session.pop('customer_no', None)

                flash(text, status)
            # Mobile number does not exist in db
            elif customer_info.mobile_number is None:
                redirect_to = 'register'
                flash(NO_MOBILE_NO, 'danger')
        # Invalid customer
        elif customer is None:
            redirect_to = 'register'
            flash(USER_NOT_FOUND_IN_DB, 'danger')

        return redirect(url_for(redirect_to))

    # GET request
    return render_template('register.html', form=form)


@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot():
    """Route for generating new password for self-care."""
    form = ForgotPasswordForm()
    # POST request for resetting password
    if form.validate_on_submit():
        redirect_to = None
        # Get customer login credentials
        customer = CustomerLogin.query.filter_by(
            customer_no=form.customer_no.data
        ).first()
        # Valid customer and valid password
        if customer is not None and customer.password_hash is not None:
            # Generate OTP
            totp = TOTPFACTORY.new()
            session['otp_data'] = totp.to_dict()
            session['customer_no'] = form.customer_no.data
            # Get customer mobile number
            mobile_number = CustomerInfo.query.filter_by(
                customer_no=form.customer_no.data
            ).first().mobile_number
            # Send SMS
            sms_msg = SMS_PWD_RESET_OTP.format(totp.generate().token)
            successful_sms = send_sms(
                app.config['SMS_URL'],
                {
                    'username': app.config['SMS_USERNAME'],
                    'password': app.config['SMS_PASSWORD'],
                    'from': app.config['SMS_SENDER'],
                    'to': '91{}'.format(mobile_number),
                    'text': sms_msg,
                }
            )
            # OTP sent
            if successful_sms:
                redirect_to = 'verify_otp'
                text = OTP_SENT
                status = 'success'
            # OTP not sent
            else:
                redirect_to = 'forgot'
                text = OTP_NOT_SENT
                status = 'danger'
                # Remove OTP and customer data from session
                session.pop('otp_data', None)
                session.pop('customer_no', None)

            flash(text, status)
        # Non-registered customer
        elif customer is not None and customer.password_hash is None:
            redirect_to = 'register'
            flash(NON_REGISTERED_USER, 'danger')
        # Invalid customer
        elif customer is None:
            redirect_to = 'forgot'
            flash(USER_NOT_FOUND_IN_DB, 'danger')

        return redirect(url_for(redirect_to))

    # GET request
    return render_template('forgot_password.html', form=form)


@app.route('/verify_otp', methods=['GET', 'POST'])
def verify_otp():
    """Route for verifying OTP."""
    form = OTPVerificationForm()
    # POST request for verifying OTP
    if form.validate_on_submit():
        redirect_to = None
        otp = form.otp.data
        # Verify OTP
        totp = TOTPFACTORY.from_dict(session['otp_data'])

        try:
            totp.verify(str(otp), totp)
        except (MalformedTokenError, TokenError) as _:
            otp_verified = False
        else:
            otp_verified = True
        # Destroy OTP data
        session.pop('otp_data', None)
        # OTP is correct
        if otp_verified:
            redirect_to = 'set_password'
        # OTP is incorrect
        elif not otp_verified:
            session.pop('customer_no', None)
            redirect_to = 'login'
            flash(OTP_VERIFY_FAILED, 'danger')

        return redirect(url_for(redirect_to))

    # GET request
    return render_template('verify_otp.html', form=form)


@app.route('/set_password', methods=['GET', 'POST'])
def set_password():
    """Route for setting new password for self-care."""
    form = SetPasswordForm()
    # POST request for setting password
    if form.validate_on_submit():
        customer = CustomerLogin.query.filter_by(
            customer_no=session['customer_no']
        ).first()
        # Generate hashed password and store
        customer.password_hash = pbkdf2_sha256.hash(str(form.password.data))
        # Save password in db
        database = current_app.extensions['sqlalchemy'].db
        database.session.commit()
        # Remove customer number from session storage
        session.pop('customer_no', None)

        flash(SUCCESSFUL_PWD_SAVE, 'success')
        return redirect(url_for('login'))

    # GET request
    return render_template('set_password.html', form=form)


@app.route('/update_mobile_number', methods=['GET', 'POST'])
def update_mobile_number():
    """Route for requesting mobile number update."""
    form = MobileNumberUpdateRequestForm()
    # POST request for updating mobile number
    if form.validate_on_submit():
        form_data = {
            'old_phone_no': form.old_phone_no.data,
            'new_phone_no': form.new_phone_no.data,
            'username_or_ip_address': form.username_or_ip_address.data,
            'postal_code': form.postal_code.data,
        }
        # Add data to db asynchronously
        add_mobile_number_update_request_to_db(form_data)

        flash(SUCCESSFUL_MOBILE_NO_UPDATE_REQUEST, 'success')
        return redirect(url_for('update_mobile_number'))

    # GET request
    return render_template('update_mobile_number.html', form=form)


@app.route('/update_email_address', methods=['GET', 'POST'])
def update_email_address():
    """Route for requesting email address update."""
    form = EmailAddressUpdateRequestForm()
    # POST request for updating email address
    if form.validate_on_submit():
        form_data = {
            'email_address': form.email_address.data,
            'username_or_ip_address': form.username_or_ip_address.data,
            'postal_code': form.postal_code.data,
        }
        # Add data to db asynchronously
        add_email_address_update_request_to_db(form_data)

        flash(SUCCESSFUL_EMAIL_ADDRESS_UPDATE_REQUEST, 'success')
        return redirect(url_for('update_email_address'))

    # GET request
    return render_template('update_email_address.html', form=form)


# Self-care portal views

@app.route('/portal/')
@login_required
def portal():
    """Route for self-care portal."""
    # Check if session variable exists for customer data
    if not session.get('portal_customer_data'):
        # Get customer contracts
        user_contracts = GetAllContracts(app)
        user_contracts.request(session['portal_customer_no'])
        user_contracts.response()
        # Add customer data to session for quick access
        session['portal_customer_data'] = user_contracts.to_dict()
    # Get all plans
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
    customer_gst = GSTUpdateRequest.query.\
        filter(
            and_(
                GSTUpdateRequest.customer_no == session['portal_customer_no'],
                GSTUpdateRequest.status == 'REGISTERED'
            )
        ).order_by(GSTUpdateRequest.id.desc()).first()
    # Get customer details
    cust_data_from_db = CustomerInfo.query.filter_by(
        customer_no=session['portal_customer_no']
    ).first()
    # Format installation address
    installation_address = re.sub(
        r',{2,3}',
        r',',
        cust_data_from_db.installation_address
    ) if cust_data_from_db.installation_address else 'NOT FOUND'
    # Format billing address
    billing_address = re.sub(
        r',{2,3}',
        r',',
        cust_data_from_db.billing_address
    ) if cust_data_from_db.billing_address else 'NOT FOUND'
    # Prepare customer data
    customer_data = {
        'name': cust_data_from_db.customer_name,
        'installation_address': installation_address,
        'billing_address': billing_address,
        'mobile_no': cust_data_from_db.mobile_number,
        'email': cust_data_from_db.email_id,
        'partner': cust_data_from_db.zone_name,
        'aadhaar': cust_data_from_db.aadhaar if cust_data_from_db.aadhaar \
        else 'NOT FOUND',
        'gstin': customer_gst.gst_no if customer_gst else 'NOT REGISTERED',
    }

    return render_template(
        'portal.html',
        cust_no=session['portal_customer_no'],
        cust_data=customer_data,
        active_plans=active_plans
    )


@app.route('/portal/recharge', methods=['GET', 'POST'])
@login_required
def recharge():
    """Route for self-care portal recharge."""
    # POST request
    if request.method == 'POST':
        # Retrieve amount for plan code selected
        amount = TariffInfo.query.options(FromCache(CACHE)).\
            filter_by(plan_code=request.form['plan_code']).\
            first_or_404().price
        # Store amount in session
        session['portal_amount'] = format(amount * 1.18, '.2f')
        # Store selected plan code in session
        session['portal_plan_code'] = request.form['plan_code']
        # Generate and store a transaction id
        session['portal_order_id'] = order_no_gen()
        # Get customer mobile number
        mobile_no = CustomerInfo.query.filter_by(
            customer_no=session['portal_customer_no']
        ).first().mobile_number
        # Check payment gateway
        if request.form['gateway'] == 'paytm':
            form_data = initiate_transaction(
                order_id=session['portal_order_id'],
                customer_no=session['portal_customer_no'],
                customer_mobile_no=mobile_no,
                amount=session['portal_amount'],
                # _ is used as the delimiter; check Paytm docs
                pay_source='portal_recharge',
            )
        elif request.form['gateway'] == 'razorpay':
            form_data = make_order(
                order_id=session['portal_order_id'],
                customer_no=session['portal_customer_no'],
                customer_mobile_no=mobile_no,
                customer_email=app.config['RAZORPAY_DEFAULT_MAIL'],
                amount=session['portal_amount'],
                # list is used for passing data; check Razorpay docs
                pay_source=['portal', 'recharge'],
            )
            # Store Razorpay order id for verification later
            session['razorpay_order_id'] = form_data['order_id']

        return render_template(
            '{}_pay.html'.format(request.form['gateway']),
            form=form_data
        )

    # GET request
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
    # {plan_name: (price, validity, plan_code)}
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
        inactive_plans=inactive_plans
    )


@app.route('/portal/add_plan', methods=['GET', 'POST'])
@login_required
def add_plan():
    """Route for self-care portal add plan."""
    # POST request
    if request.method == 'POST':
        # Retrieve amount for plan code selected
        amount = TariffInfo.query.options(FromCache(CACHE)).\
            filter_by(plan_code=request.form['plan_code']).first_or_404().price
        # Store amount in session
        session['portal_amount'] = format(amount * 1.18, '.2f')
        # Store selected plan code in session
        session['portal_plan_code'] = request.form['plan_code']
        # Generate and store a transaction id
        session['portal_order_id'] = order_no_gen()
        # Get customer mobile number
        mobile_no = CustomerInfo.query.filter_by(
            customer_no=session['portal_customer_no']
        ).first().mobile_number
        # Check payment gateway
        if request.form['gateway'] == 'paytm':
            form_data = initiate_transaction(
                order_id=session['portal_order_id'],
                customer_no=session['portal_customer_no'],
                customer_mobile_no=mobile_no,
                amount=session['portal_amount'],
                # _ is used as the delimiter; check Paytm docs
                pay_source='portal_addplan',
            )
        elif request.form['gateway'] == 'razorpay':
            form_data = make_order(
                order_id=session['portal_order_id'],
                customer_no=session['portal_customer_no'],
                customer_mobile_no=mobile_no,
                customer_email=app.config['RAZORPAY_DEFAULT_MAIL'],
                amount=session['portal_amount'],
                # List is used for passing data; check Razorpay docs
                pay_source=['portal', 'addplan'],
            )
            # Store Razorpay order id for verification later
            session['razorpay_order_id'] = form_data['order_id']

        return render_template(
            '{}_pay.html'.format(request.form['gateway']),
            form=form_data
        )

    # GET request
    zone_id = CustomerInfo.query.options(FromCache(CACHE)).\
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
    # Get all plans
    plans = {
        row.plan_code: row
        for row in TariffInfo.query.options(FromCache(CACHE)).all()
    }
    # Get available plan codes for the zone
    available_plan_codes = set(plans.keys()).\
        difference(session['portal_customer_data']['all_plans']).\
        intersection(zone_eligible_plan_codes)
    # Get available plans for the user
    # {plan_name: (price, plan_code)}
    available_plans = {
        plans[plan_code].plan_name: (
            plans[plan_code].price,
            plan_code,
            plans[plan_code].speed,
            plans[plan_code].validity,
            plans[plan_code].softphone,
            plans[plan_code].plan_type,
        )
        for plan_code in available_plan_codes
    }

    return render_template(
        'add_plan.html',
        available_plans=available_plans,
    )


@app.route('/portal/receipt/<order_id>')
@login_required
def portal_receipt(order_id):
    """Route to transaction receipt."""
    customer_name = CustomerInfo.query.options(FromCache(CACHE)).filter_by(
        customer_no=request.args.get('customer_no')
    ).first_or_404().customer_name
    # Get customer contracts
    user_contracts = GetAllContracts(app)
    user_contracts.request(session['portal_customer_no'])
    user_contracts.response()
    # Add customer data to session for quick access
    session['portal_customer_data'] = user_contracts.to_dict()

    return render_template(
        'portal_receipt.html',
        customer_no=request.args.get('customer_no'),
        customer_name=customer_name,
        amount=session['portal_amount'],
        date_and_time=request.args.get('txn_datetime'),
        txn_status=request.args.get('status'),
        txn_no=order_id
    )


@app.route('/portal/docket')
@login_required
def docket():
    """Route for self-care portal docket."""
    # Get tickets for the user
    tickets = Ticket.query.filter_by(
        customer_no=session['portal_customer_no']
    ).all()
    # Filter open tickets
    open_tickets = [ticket for ticket in tickets if ticket.status == 'Open']
    # Filter closed tickets
    closed_tickets = [
        ticket for ticket in tickets if ticket.status == 'Closed'
    ]
    # Save open ticket number in session
    if open_tickets:
        session['portal_open_ticket_no'] = open_tickets[0].ticket_no

    return render_template(
        'docket.html',
        tickets=tickets,
        open_tickets=open_tickets,
        closed_tickets=closed_tickets
    )


@app.route('/portal/docket/new', methods=['GET', 'POST'])
@login_required
def new_docket():
    """Route for self-care new docket."""
    # No open ticket exists
    if not session.get('portal_open_ticket_no'):
        form = NewTicketForm()
        form.nature.choices = [
            (row.ticket_nature_code, row.ticket_nature_desc)
            for row in TicketInfo.query.options(FromCache(CACHE)).all()
        ]
        # POST request for opening ticket
        if form.validate_on_submit():
            nature_code = form.nature.data
            remarks = form.remarks.data
            # Query category from db
            entry = TicketInfo.query.options(FromCache(CACHE)).filter_by(
                ticket_nature_code=nature_code
            ).first()
            category_code = entry.ticket_category_code
            category_desc = entry.ticket_category_desc
            nature_desc = entry.ticket_nature_desc
            # Generate ticket in MQS
            register_ticket = RegisterTicket(app)
            register_ticket.request(
                cust_id=session['portal_customer_no'],
                category=category_code,
                description=remarks,
                nature=nature_code,
            )
            register_ticket.response()
            # Check if RegisterTicket API is successful
            if register_ticket.error_no == '0':
                ticket_no = register_ticket.ticket_no
                # Send data to db
                ticket_data = {
                    'customer_no': session['portal_customer_no'],
                    'ticket_no': ticket_no,
                    'category_desc': category_desc,
                    'nature_desc': nature_desc,
                    'remarks': remarks,
                    'opening_date': datetime.now().astimezone().date(),
                    'opening_time': datetime.now().astimezone().time()
                }
                # Add new ticket to db asynchronously
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
            allowed=True
        )
    # Open ticket exists
    return render_template(
        'new_docket.html',
        allowed=False
    )


@app.route('/portal/docket/close', methods=['POST'])
@login_required
def close_docket():
    """Route for self-care close docket."""
    # Open ticket exists
    if session.get('portal_open_ticket_no'):
        ticket_no = session.get('portal_open_ticket_no')
        # Close ticket in MQS
        close_ticket = CloseTicket(app)
        close_ticket.request(ticket_no)
        close_ticket.response()
        # Check if CloseTicket API is successful or closed internally
        if close_ticket.error_no == '0' or close_ticket.error_no == '99070':
            ticket = Ticket.query.filter_by(
                ticket_no=session['portal_open_ticket_no']
            ).first()
            ticket.status = 'Closed'
            ticket.closing_date = datetime.now().astimezone().date()
            ticket.closing_time = datetime.now().astimezone().time()
            # Close ticket in db
            database = current_app.extensions['sqlalchemy'].db
            database.session.commit()

            msg = SUCCESSFUL_DOCKET_CLOSE.format(ticket_no)
            status = 'success'
            # Remove data from session variable
            session.pop('portal_open_ticket_no', None)
        else:
            msg = UNSUCCESSFUL_DOCKET_CLOSE.format(ticket_no)
            status = 'danger'
    # No open ticket exists
    elif not session.get('portal_open_ticket_no'):
        msg = NO_DOCKETS
        status = 'danger'

    flash(msg, status)
    return redirect(url_for('docket'))


@app.route('/portal/usage')
@login_required
def usage():
    """Route for self-care portal usage."""
    # Get customer username
    customer_username = CustomerInfo.query.options(FromCache(CACHE)).\
        filter_by(customer_no=session['portal_customer_no']).\
        first().user_name
    # Get start and end dates for usage data
    today = datetime.now().astimezone().date()
    past = today - timedelta(days=90)
    # Get usage data using GetUsageDetails API
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
@login_required
def transaction_history():
    """Route for self-care transaction history."""
    # Get page number
    page_num = request.args.get('page', type=int, default=1)
    # Retrieve data from db
    transactions = RechargeEntry.query.filter_by(
        customer_no=session['portal_customer_no']
    ).order_by(RechargeEntry.id.desc()).\
    paginate(per_page=10, page=page_num, error_out=False)

    return render_template(
        'transaction_history.html',
        transactions=transactions,
        page=page_num
    )


@app.route('/portal/wishtalk')
@login_required
def wishtalk():
    """Route for self-care Wishtalk."""
    # Get all plans
    plans = {
        row.plan_code: row
        for row in TariffInfo.query.options(FromCache(CACHE)).all()
    }
    # Get active plans for the user
    # [(plan_code, validity_end_date)]
    active_plans = [
        (plan_code, validity_period.split(' - ')[1])
        for (_, plan_code, validity_period) in
        session['portal_customer_data']['active_plans']
        if plan_code in plans
    ]
    # Active plans exist
    if active_plans:
        # Get last active plan
        last_active_plan = active_plans[-1]
        # Get softphone limit
        softphone_limit = TariffInfo.query.\
            filter_by(plan_code=last_active_plan[0]).\
            first().softphone
        # Current softphone allotment
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
        softphone_allotted = len(current_softphone_allotment)
    # No active plans
    elif not active_plans:
        softphone_limit = None
        current_softphone_allotment = None
        add_softphone_form = None
        softphone_allotted = 0


    return render_template(
        'wishtalk.html',
        no_of_softphone_allowed=softphone_limit,
        no_of_softphone_allotted=softphone_allotted,
        softphone_data=current_softphone_allotment,
        add_softphone_form=add_softphone_form,
    )


@app.route('/portal/wishtalk/add_softphone', methods=['POST'])
@login_required
def wishtalk_add_softphone():
    """Route for self-care portal softphone addition."""
    # Get active plans for the user
    # [(plan_code, validity_end_date)]
    active_plans = [
        (plan_code, validity_period.split(' - ')[1])
        for (_, plan_code, validity_period) in
        session['portal_customer_data']['active_plans']
    ]
    # Get last active plan and expiry
    last_active_plan = active_plans[-1]
    last_active_plan_expiry = datetime.strptime(
        last_active_plan[1], '%d-%b-%y'
    ).date()
    # Get softphone limit
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
    softphone_allotted = len(current_softphone_allotment) \
        if current_softphone_allotment else 0
    # Setup forms
    add_softphone_form = AddSoftphoneForm()
    # POST request for adding softphone
    if add_softphone_form.validate_on_submit():
        # Create session to perform one-step read and write transaction
        db_session = SignallingSession(
            current_app.extensions['sqlalchemy'].db
        )
        # DATABASE OPERATION
        # Initiate transaction
        try:
            # Get FREE and NORMAL softphone number
            free_softphone_number = db_session.query(SoftphoneNumber).\
                filter(
                    and_(
                        SoftphoneNumber.softphone_status == 'FREE',
                        SoftphoneNumber.category_type == 'NORMAL'
                    )
                ).order_by(SoftphoneNumber.id.asc()).first()
            # Store the number
            softphone_number = free_softphone_number.softphone_no
            # Get the category
            softphone_category = free_softphone_number.category_type
            # Allot the number
            free_softphone_number.softphone_status = 'ALLOTTED'
            # Commit changes
            db_session.commit()
        # rollback on failure
        except:
            softphone_number = None
            db_session.rollback()
        # Close connection (fallback in case of failure)
        finally:
            db_session.close()

        # API CALL
        # Successful allotment of softphone number
        if softphone_number:
            # Call API for softphone allotment
            softphone_add_success = add_softphone(
                url=app.config['SOFTPHONE_URL'],
                softphone_number=softphone_number,
                password=add_softphone_form.password.data,
                user_name=add_softphone_form.name.data
            )
            # Softphone addition API call successful
            if softphone_add_success:
                # Set mobile number in case of fixed line
                if not add_softphone_form.mobile_number.data:
                    mobile_no = CustomerInfo.query.filter_by(
                        customer_no=session['portal_customer_no']
                    ).first().mobile_number
                else:
                    mobile_no = add_softphone_form.mobile_number.data
                # Generate hash from the raw password
                hashed_pwd = pbkdf2_sha256.hash(
                    str(add_softphone_form.password.data)
                )
                # Get customer name
                customer_name = CustomerInfo.query.\
                    options(FromCache(CACHE)).\
                    filter_by(customer_no=session['portal_customer_no']).\
                    first().customer_name
                # Create data for db entry
                data = {
                    'customer_no': session['portal_customer_no'],
                    'customer_name': customer_name,
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
                # Add softphone allotment to db asynchronously
                add_async_softphone_allotment.delay(data)
                # Set SMS message based on platform
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
                elif add_softphone_form.softphone_platform.data == 'Fixed Line':
                    sms_msg = SUCCESSFUL_SOFTPHONE_SMS_FIXED_LINE.format(
                        softphone_number,
                        add_softphone_form.password.data
                    )
                # Send SMS
                successful_sms = send_sms(
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
                if successful_sms:
                    text = SUCCESSFUL_SOFTPHONE_ALLOTMENT
                    status = 'success'
                # SMS not sent
                elif not successful_sms:
                    text = UNSUCCESSFUL_SOFTPHONE_SMS
                    status = 'danger'

                flash(text, status)
            # Softphone addition API call unsuccessful
            elif not softphone_add_success:
                flash(UNSUCCESSFUL_SOFTPHONE_ALLOTMENT, 'danger')
        # Unsuccessful allotment of softphone number
        elif not softphone_number:
            # Remove the softphone number allotment
            softphone_no = SoftphoneNumber.query.filter_by(
                softphone_no=softphone_number
            ).first()
            softphone_no.softphone_status = 'FREE'
            # Make synchronous call to change status in db
            database = current_app.extensions['sqlalchemy'].db
            database.session.commit()

            flash(UNSUCCESSFUL_SOFTPHONE_ALLOTMENT, 'danger')

        return redirect(url_for('wishtalk'))

    return render_template(
        'wishtalk.html',
        no_of_softphone_allowed=softphone_limit,
        no_of_softphone_allotted=softphone_allotted,
        softphone_data=current_softphone_allotment,
        add_softphone_form=add_softphone_form,
    )


@app.route('/portal/wish_ott', methods=['GET', 'POST'])
@login_required
def wishott():
    """Route for self-care Wish OTT."""
    # Get all plans
    plans = {
        row.plan_code: row
        for row in TariffInfo.query.options(FromCache(CACHE)).all()
    }
    # Get active plans for the user
    # [(plan_code, validity_end_date)]
    active_plans = [
        (plan_code, validity_period.split(' - ')[0])
        for (_, plan_code, validity_period) in
        session['portal_customer_data']['active_plans']
        if plan_code in plans
    ]

    # POST request for getting voucher
    if request.method == 'POST':
        # Get OTT package code from form
        voucher_package_code = request.form['ott-package']
        # Create session to perform one-step read and write transaction
        db_session = SignallingSession(
            current_app.extensions['sqlalchemy'].db
        )
        # DATABASE OPERATION
        # Initiate transaction
        try:
            # Get ACTIVE voucher from the specific provider
            ott_voucher = db_session.query(Voucher).filter(
                and_(
                    Voucher.ott_pkg_code == voucher_package_code,
                    Voucher.ott_voucher_status == 'ACTIVE',
                    Voucher.ott_voucher_start_dt <= datetime.now().date(),
                    Voucher.ott_voucher_end_dt > datetime.now().date()
                )
            ).order_by(Voucher.id.asc()).first()
            # Store required data
            voucher_provider_code = ott_voucher.ott_provider_code
            voucher_code = ott_voucher.ott_voucher_code
            voucher_end_date = ott_voucher.ott_voucher_end_dt
            # Change status to ALLOTTED
            ott_voucher.ott_voucher_status = 'ALLOTTED'
            # Commit changes
            db_session.commit()
        # Rollback on failure
        except:
            ott_voucher = None
            db_session.rollback()
        # Close connection (fallback in case of failure)
        finally:
            db_session.close()

        # Successful voucher retrieval from database
        if ott_voucher:
            # Get OTT provider info
            provider = VoucherProvider.query.\
                filter_by(ott_provider_code=voucher_provider_code).first()
            # Get OTT package info
            package = VoucherPackage.query.\
                filter_by(ott_pkg_code=voucher_package_code).first()
            # Create data for db entry
            data = {
                'ott_provider_code': voucher_provider_code,
                'ott_provider_name': provider.ott_provider_name,
                'ott_package_code': voucher_package_code,
                'ott_package_name': package.ott_pkg_name,
                'ott_voucher_code': voucher_code,
                'customer_no': session['portal_customer_no'],
                'plan_code': active_plans[-1][0],
                'send_date': datetime.now().astimezone().date(),
                'expiry_date': voucher_end_date,
            }

            # Add voucher allotment data to database asynchronously
            add_async_voucher_allotment.delay(data)
            # Get customer mobile number
            customer_mobile_number = CustomerInfo.query.\
                filter_by(customer_no=session['portal_customer_no']).\
                first().mobile_number
            # Send voucher to mobile number via SMS
            sms_msg = SUCCESSFUL_VOUCHER_SMS.format(
                provider.ott_provider_app_name,
                voucher_code,
                package.ott_pkg_name,
                voucher_end_date
            )
            # Send SMS
            successful_sms = send_sms(
                app.config['SMS_URL'],
                {
                    'username': app.config['SMS_USERNAME'],
                    'password': app.config['SMS_PASSWORD'],
                    'from': app.config['SMS_SENDER'],
                    'to': '91{}'.format(customer_mobile_number),
                    'text': sms_msg,
                }
            )
            # SMS sent
            if successful_sms:
                text = SUCCESSFUL_VOUCHER_ALLOTMENT
                status = 'success'
            # SMS not sent
            elif not successful_sms:
                text = UNSUCCESSFUL_VOUCHER_SMS
                status = 'danger'

            flash(text, status)

        # Unsuccessful voucher retrieval from database
        elif not ott_voucher:
            flash(UNSUCCESSFUL_VOUCHER_ALLOTMENT, 'danger')

        return redirect(url_for('wishott'))

    # GET request
    # Active plans exist
    if active_plans:
        # Get last active plan
        last_active_plan = active_plans[-1]
        # Get tariff for active plan
        plan_tariff = TariffInfo.query.\
            filter_by(plan_code=last_active_plan[0]).first()
        # Get OTT limit
        ott_limit = plan_tariff.ott
        # Get allowed OTT packages
        allowed_packages = plan_tariff.ott_package_codes.split(',')
        # Get latest online transaction
        last_transaction = RechargeEntry.query.\
            filter(
                and_(
                    RechargeEntry.customer_no == session['portal_customer_no'],
                    RechargeEntry.payment_status == 'SUCCESS'
                )
            ).order_by(RechargeEntry.payment_date.desc()).first()
        # Check if latest plan active via online transaction
        if last_transaction:
            # Current OTT allotment
            current_ott_allotment = VoucherEntry.query.\
                filter(
                    and_(
                        VoucherEntry.voucher_send_dt >= \
                        last_transaction.payment_date,
                        VoucherEntry.customer_no == \
                        session['portal_customer_no']
                    )
                ).all()
            ott_allotted = len(current_ott_allotment) \
                if current_ott_allotment else 0
            validity_days_from_today = \
                datetime.now().date() - timedelta(days=plan_tariff.validity)
            allow_voucher = \
                validity_days_from_today <= last_transaction.payment_date
        # No online transaction
        elif not last_transaction:
            current_ott_allotment = None
            ott_allotted = 0
            allow_voucher = False
        # Voucher packages
        packages = VoucherPackage.query.\
            filter_by(ott_pkg_status='ACTIVE').\
            order_by(VoucherPackage.ott_pkg_priority.asc()).all()
        filtered_packages = [
            package for package in packages
            if package.ott_pkg_code in allowed_packages
        ]
    # No active plans
    elif not active_plans:
        ott_limit = None
        current_ott_allotment = None
        ott_allotted = 0
        filtered_packages = None
        allow_voucher = False

    return render_template(
        'wishott.html',
        no_of_ott_allowed=ott_limit,
        no_of_ott_allotted=ott_allotted,
        ott_data=current_ott_allotment,
        ott_packages=filtered_packages,
        allow_voucher=allow_voucher
    )


@app.route('/portal/update_profile')
@login_required
def update_profile():
    """Route for self-care portal profile update."""
    # Setup forms
    update_profile_form = UpdateProfileForm()
    update_password_form = ChangePasswordForm()
    update_gst_form = UpdateGSTForm()
    update_aadhaar_form = UpdateAadhaarForm()

    return render_template(
        'update_profile.html',
        update_profile_form=update_profile_form,
        update_password_form=update_password_form,
        update_gst_form=update_gst_form,
        update_aadhaar_form=update_aadhaar_form
    )


@app.route('/portal/update_contact', methods=['POST'])
@login_required
def update_contact():
    """Route for self-care portal contact update."""
    # Setup forms
    update_profile_form = UpdateProfileForm()
    update_password_form = ChangePasswordForm()
    update_gst_form = UpdateGSTForm()
    update_aadhaar_form = UpdateAadhaarForm()
    # POST request for updating contact information
    if update_profile_form.validate_on_submit():
        # Check for empty inputs
        if not update_profile_form.new_phone_no.data and \
           not update_profile_form.new_email_address.data:
            return redirect(url_for('update_profile'))

        # Update profile details in MQS
        profile = UpdateProfile(app)
        profile.request(
            cust_id=session['portal_customer_no'],
            email=update_profile_form.new_email_address.data,
            mobile_no=update_profile_form.new_phone_no.data
        )
        profile.response()
        # Verify MQS ModifyCustomer status
        db_status, flash_msg, msg_status = verify_mqs_updateprofile(profile)
        # Data for profile update request in db
        form_data = {
            'customer_no': session['portal_customer_no'],
            'new_phone_no': update_profile_form.new_phone_no.data,
            'new_email': update_profile_form.new_email_address.data,
            'status': db_status,
            'request_date': datetime.now().astimezone().date(),
            'request_time': datetime.now().astimezone().time(),
        }
        # Add request to db asynchronously
        add_profile_update_request_to_db.delay(form_data)
        # Only modify in database if request successful
        if db_status == 'SUCCESS':
            # Data for updating profile in db
            update_data = {
                'customer_no': session['portal_customer_no'],
                'email': update_profile_form.new_email_address.data,
                'mobile_no': update_profile_form.new_phone_no.data,
            }
            # Update profile in db asynchronously
            update_profile_in_db.delay(update_data)

        flash(flash_msg, msg_status)
        return redirect(url_for('update_profile'))
    # Form validation error
    return render_template(
        'update_profile.html',
        update_profile_form=update_profile_form,
        update_password_form=update_password_form,
        update_gst_form=update_gst_form,
        update_aadhaar_form=update_aadhaar_form
    )


@app.route('/portal/change_password', methods=['POST'])
@login_required
def change_password():
    """Route for self-care portal password change."""
    # Setup forms
    update_profile_form = UpdateProfileForm()
    update_password_form = ChangePasswordForm()
    update_gst_form = UpdateGSTForm()
    update_aadhaar_form = UpdateAadhaarForm()
    # POST request for changing password
    if update_password_form.validate_on_submit():
        customer = CustomerLogin.query.filter_by(
            customer_no=session['portal_customer_no']
        ).first()
        # Verify old password
        pwd_verified = pbkdf2_sha256.verify(
            str(update_password_form.old_password.data),
            customer.password_hash
        )
        # If old password is verified
        if pwd_verified:
            # Check if the old and new passwords are same
            if update_password_form.old_password.data == \
               update_password_form.new_password.data:
                flash(SET_NEW_PWD, 'danger')
            else:
                # Generate new hashed password and store
                hashed_pwd = pbkdf2_sha256.hash(
                    str(update_password_form.new_password.data)
                )
                customer.password_hash = hashed_pwd
                # Save password in db
                database = current_app.extensions['sqlalchemy'].db
                database.session.commit()

                flash(NEW_PWD_SET, 'success')
        # Old password is incorrect
        else:
            flash(INCORRECT_OLD_PWD, 'danger')

        return redirect(url_for('update_profile'))
    # Form validation error
    return render_template(
        'update_profile.html',
        update_profile_form=update_profile_form,
        update_password_form=update_password_form,
        update_gst_form=update_gst_form,
        update_aadhaar_form=update_aadhaar_form
    )


@app.route('/portal/update_gst', methods=['POST'])
@login_required
def update_gst():
    """Route for self-care GST information update."""
    # Setup forms
    update_profile_form = UpdateProfileForm()
    update_password_form = ChangePasswordForm()
    update_gst_form = UpdateGSTForm()
    update_aadhaar_form = UpdateAadhaarForm()
    # POST request for updating GST
    if update_gst_form.validate_on_submit():
        form_data = {
            'customer_no': session['portal_customer_no'],
            'gst_no': update_gst_form.gst_no.data,
            'request_date': datetime.now().astimezone().date(),
            'request_time': datetime.now().astimezone().time(),
        }
        # Add data to db asynchronously
        add_gst_update_request_to_db.delay(form_data)

        flash(SUCCESSFUL_GST_UPDATE_REQUEST, 'success')
        return redirect(url_for('update_profile'))
    # Form validation error
    return render_template(
        'update_profile.html',
        update_profile_form=update_profile_form,
        update_password_form=update_password_form,
        update_gst_form=update_gst_form,
        update_aadhaar_form=update_aadhaar_form
    )


@app.route('/portal/update_aadhaar', methods=['POST'])
@login_required
def update_aadhaar():
    """Route for self-care Aadhaar information update."""
    # Setup forms
    update_profile_form = UpdateProfileForm()
    update_password_form = ChangePasswordForm()
    update_gst_form = UpdateGSTForm()
    update_aadhaar_form = UpdateAadhaarForm()
    # POST request for updating Aadhaar
    if update_aadhaar_form.validate_on_submit():
        # Get customer information from database
        customer = CustomerInfo.query.filter_by(
            customer_no=session['portal_customer_no']
        ).first()
        # Modify Aadhaar data
        customer.aadhaar = update_aadhaar_form.aadhaar.data
        database = current_app.extensions['sqlalchemy'].db
        database.session.commit()

        flash(SUCCESSFUL_AADHAAR_UPDATE, 'success')
        return redirect(url_for('update_profile'))
    # Form validation error
    return render_template(
        'update_profile.html',
        update_profile_form=update_profile_form,
        update_password_form=update_password_form,
        update_gst_form=update_gst_form,
        update_aadhaar_form=update_aadhaar_form
    )
