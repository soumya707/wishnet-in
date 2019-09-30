# -*- coding: utf-8 -*-

"""Views for the website."""


import random
import string
from datetime import datetime, timedelta

from flask import (
    current_app, flash, redirect, render_template, request, session, url_for)
from flask_sqlalchemy_caching import FromCache
from flask_wtf.csrf import CSRFProtect
from passlib.exc import MalformedTokenError, TokenError
from passlib.hash import pbkdf2_sha256
from sqlalchemy import or_

from website import CACHE, TOTPFACTORY, app
from website.forms import *
from website.models import *
from website.mqs_api import *
from website.paytm_utils import (
    initiate_transaction, verify_final_status, verify_transaction)
from website.razorpay_utils import make_order, verify_signature
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

        # Get active plans (reference no. of this API call is passed forward)
        user_contracts = ContractsByKey(app)
        user_contracts.request(user)
        user_contracts.response()

        # user has active plans
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
                for (plan_code, validity_period) in user_contracts.active_plans
                if plan_code in plans
            }

            # Get customer info
            customer = CustomerInfo.query.filter_by(customer_no=user).first()

            session['insta_active_plans'] = active_plans
            session['insta_customer_no'] = customer.customer_no
            session['insta_customer_name'] = customer.customer_name
            session['insta_customer_mobile_no'] = customer.mobile_no
            session['insta_order_id'] = user_contracts.ref_no

            return redirect(
                url_for(
                    'insta_recharge',
                    order_id=session['insta_order_id'],
                )
            )
        # user does not have active plans
        elif not user_contracts.valid_user:
            flash(
                (
                    'There is an issue with insta-recharge for your '
                    'account. Please use self-care or call us.'
                ), 'danger'
            )
            return redirect(
                url_for('index')
            )

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
        if customer is not None and customer.mobile_no is not str():
            # send SMS
            mobile_no = customer.mobile_no
            sms_msg = '{} is your customer number. Team Wishnet.'.format(
                customer.customer_no
            )

            successful = send_sms(
                app.config['SMS_URL'],
                {
                    'username': app.config['SMS_USERNAME'],
                    'password': app.config['SMS_PASSWORD'],
                    'from': app.config['SMS_SENDER'],
                    'to': f'91{mobile_no}',
                    'text': sms_msg,
                }
            )

            if successful:
                text = (
                    'Customer number has been sent to your registered '
                    'mobile number.'
                )
                status = 'success'

            else:
                text = 'There was some problem, please try again.'
                status = 'danger'

            flash(text, status)

        # mobile number not available
        elif customer is not None and customer.mobile_no is str():
            flash(
                (
                    'No registered mobile number found. '
                    'Please get your mobile number registered with us.'
                )
                , 'danger'
            )
        # invalid credentials
        elif customer is None:
            flash(
                (
                    'Couldn\'t retrieve details with the provided '
                    'credentials. Try again with valid credentials or '
                    'contact us.'
                )
                , 'danger'
            )

        return redirect(url_for('get_cust_no'))

    # GET request
    return render_template(
        'customer_no.html',
        form=form
    )


@app.route('/insta_recharge/<order_id>', methods=['GET', 'POST'])
def insta_recharge(order_id):
    """Route for insta-recharge."""
    if request.method == 'POST':
        # store amount in session
        session['insta_amount'] = request.form['amount']
        # store selected plan code in session
        session['insta_plan_code'] = request.form['plan_code']

        # Check payment gateway
        if request.form['gateway'] == 'paytm':
            # Get Paytm form data
            form_data = initiate_transaction(
                order_id=order_id,
                customer_no=session['insta_customer_no'],
                customer_mobile_no=session['insta_customer_mobile_no'],
                amount=request.form['amount'],
                # _ is used as the delimiter; check Paytm docs
                pay_source='insta_recharge',
            )

        elif request.form['gateway'] == 'razorpay':
            # Get Razorpay form data
            form_data = make_order(
                order_id=order_id,
                customer_no=session['insta_customer_no'],
                customer_mobile_no=session['insta_customer_mobile_no'],
                amount=request.form['amount'],
                # list is used for passing data; check Razorpay docs
                pay_source=['insta', 'recharge'],
            )

        return render_template(
            '{}_pay.html'.format(request.form['gateway']),
            form=form_data,
        )

    elif request.method == 'GET':
        return render_template(
            'insta_recharge.html',
            customer_no=session['insta_customer_no'],
            customer_name=session['insta_customer_name'],
            active_plans=session['insta_active_plans'],
        )


@app.route('/verify/<gateway>', methods=['POST'])
@CSRF.exempt
def verify_response(gateway):
    """Route for verifying response for payment."""
    if request.method == 'POST':
        # check payment gateway
        # PAYTM
        if gateway == 'paytm':
            session_var_prefix, txn_type = \
                request.form['MERC_UNQ_REF'].split('_')

            # store response data
            data = {
                'customer_no': session[f'{session_var_prefix}_customer_no'],
                'wishnet_order_id': session[f'{session_var_prefix}_order_id'],
                'payment_gateway': 'Paytm',
                'txn_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
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

                        data['topup_ref_id'] = top_up.ref_no
                        data['topup_datetime'] = datetime.now().\
                            strftime("%Y-%m-%d %H:%M:%S.%f")

                        # verify MQS TopUp status
                        db_entry_status, status, msg, msg_stat = \
                            verify_mqs_topup(top_up)

                        data['topup_status'] = db_entry_status
                        status = status

                    elif txn_type == 'addplan':
                        # AddPlan in MQS
                        add_plan = AddPlan(app)
                        add_plan.request(
                            session[f'{session_var_prefix}_customer_no'],
                            session[f'{session_var_prefix}_plan_code']
                        )
                        add_plan.response()

                        data['addplan_ref_id'] = top_up.ref_no
                        data['addplan_datetime'] = datetime.now().\
                            strftime("%Y-%m-%d %H:%M:%S.%f")

                        # verify MQS AddPlan status
                        db_entry_status, status, msg, msg_stat = \
                            verify_mqs_addplan(add_plan)

                        data['addplan_status'] = db_entry_status
                        status = status

                    flash(msg, msg_stat)

                # Transaction Status failure
                else:
                    data.update(
                        txn_amount='',
                        txn_status='FAILURE',
                        topup_ref_id='',
                        topup_datetime='',
                        topup_status='',
                        addplan_ref_id='',
                        addplan_datetime='',
                        addplan_status='',
                    )
                    status = 'unsuccessful'
                    flash(
                        'Payment incomplete! Please check with {}.'.\
                        format(gateway.capitalize()), 'danger'
                    )
            # checksumhash verification failure
            # data tampered during transaction
            elif not verified:
                data.update(
                    txn_order_id='',
                    txn_amount='',
                    txn_status='CHECKSUM VERIFICATION FAILURE',
                    topup_ref_id='',
                    topup_datetime='',
                    topup_status='',
                    addplan_ref_id='',
                    addplan_datetime='',
                    addplan_status='',
                )
                status = 'unsuccessful'
                flash('Payment failed! Please try again.', 'danger')

        # RAZORPAY
        elif gateway == 'razorpay':
            notes = session['notes']
            session_var_prefix = notes['pay_source']
            txn_type = notes['txn_type']
            # store response data
            recharge_data = {
                'customer_no': session[f'{session_var_prefix}_customer_no'],
                'wishnet_order_id': session[f'{session_var_prefix}_order_id'],
                'payment_gateway': 'Razorpay',
                'txn_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            }

            verified = verify_signature(request.form)
            # signature verification success
            if verified:
                data.update(
                    txn_order_id=request.form['razorpay_order_id'],
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

                    data['topup_ref_id'] = top_up.ref_no
                    data['topup_datetime'] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S.%f"
                    )

                    # verify MQS TopUp status
                    db_entry_status, status, msg, msg_stat = \
                        verify_mqs_topup(top_up)

                    recharge_data['topup_status'] = db_entry_status
                    status = status

                elif txn_type == 'addplan':
                    # AddPlan in MQS
                    add_plan = AddPlan(app)
                    add_plan.request(
                        session[f'{session_var_prefix}_customer_no'],
                        session[f'{session_var_prefix}_plan_code']
                    )
                    add_plan.response()

                    data['addplan_ref_id'] = top_up.ref_no
                    data['addplan_datetime'] = datetime.now().\
                        strftime("%Y-%m-%d %H:%M:%S.%f")

                    # verify MQS AddPlan status
                    db_entry_status, status, msg, msg_stat = \
                        verify_mqs_addplan(add_plan)

                    data['addplan_status'] = db_entry_status
                    status = status

                flash(msg, msg_stat)

            # signature verification failure
            # data tampered during transaction
            else:
                data.update(
                    txn_order_id='',
                    txn_amount='',
                    txn_status='SIGNATURE VERIFICATION FAILURE',
                    topup_ref_id='',
                    topup_datetime='',
                    topup_status='',
                    addplan_ref_id='',
                    addplan_datetime='',
                    addplan_status='',
                )
                status = 'unsuccessful'
                flash('Transaction failed! Please try again.', 'danger')

        # add transaction data to db async
        add_txn_data_to_db.delay(data)

        return redirect(
            url_for(
                f'{session_var_prefix}_receipt',
                order_id=session[f'{session_var_prefix}_order_id'],
                status=status
            )
        )


@app.route('/receipt/<order_id>/<status>')
def insta_receipt(order_id, status):
    """Route to transaction receipt."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return render_template(
        'receipt.html',
        customer_no=session['insta_customer_no'],
        customer_name=session['insta_customer_name'],
        amount=session['insta_amount'],
        date_and_time=current_time,
        txn_status=status,
        txn_no=order_id,
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
                flash(
                    (
                        'Incorrect password for the given customer number. '
                        'Please try again.'
                    ), 'danger'
                )

        # non-registered customer
        elif customer is not None and customer.password_hash is None:
            redirect_to = 'register'
            flash(
                (
                    'You have not registered for the self-care portal. '
                    'Please register before proceeding.'
                ), 'danger'
            )

        # invalid customer
        else:
            redirect_to = 'login'
            flash('Invalid customer number.', 'danger')

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
        flash('You have been successfully logged out.', 'success')
        # revoke session entry
        session['user_logged_in'] = False
        # remove portal customer data storage
        session.pop('portal_customer_no', None)
        session.pop('portal_customer_data', None)
        session.pop('portal_active_plans', None)
        session.pop('portal_inactive_plans', None)
        session.pop('portal_available_plans', None)
        session.pop('portal_order_no', None)
        session.pop('portal_open_ticket_no', None)
        session.pop('portal_username', None)
    # user not logged in (invalid access to route)
    elif not session.get('user_logged_in'):
        flash('You are not logged in yet.', 'danger')

    return redirect(url_for('login'))


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Route for self-care registration."""
    form = RegistrationForm()

    if form.validate_on_submit():
        # get customer info
        customer = CustomerLogin.query.filter_by(
            customer_no=form.customer_no.data
        ).first()

        redirect_to = None

        # valid customer and valid password
        if customer is not None and customer.password_hash is not None:
            redirect_to = 'login'
            flash('You are already registered. Try logging in.', 'info')

        # non-registered customer
        elif customer is not None and customer.password_hash is None:
            # generate OTP
            totp = TOTPFACTORY.new()
            session['otp_data'] = totp.to_dict()
            session['customer_no'] = form.customer_no.data
            redirect_to = 'verify_otp'

            # send SMS
            mobile_no = customer.mobile_no
            sms_msg = (
                '{} is your OTP for self-care registration. Team Wishnet.'
            ).format(totp.generate().token)

            successful = send_sms(
                app.config['SMS_URL'],
                {
                    'username': app.config['SMS_USERNAME'],
                    'password': app.config['SMS_PASSWORD'],
                    'from': app.config['SMS_SENDER'],
                    'to': f'91{mobile_no}',
                    'text': sms_msg,
                }
            )

            if successful:
                text = 'OTP has been sent to your registered mobile number.'
                status = 'success'

            else:
                text = 'There was some problem, please try again.'
                status = 'danger'

            flash(text, status)

        # invalid customer
        else:
            redirect_to = 'register'
            flash('Invalid customer number.', 'danger')

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
            mobile_no = customer.mobile_no
            sms_msg = (
                '{} is your OTP for resetting password. Team Wishnet.'
            ).format(totp.generate().token)

            successful = send_sms(
                app.config['SMS_URL'],
                {
                    'username': app.config['SMS_USERNAME'],
                    'password': app.config['SMS_PASSWORD'],
                    'from': app.config['SMS_SENDER'],
                    'to': f'91{mobile_no}',
                    'text': sms_msg,
                }
            )

            if successful:
                text = 'OTP has been sent to your registered mobile number.'
                status = 'success'

            else:
                text = 'There was some problem, please try again.'
                status = 'danger'

            flash(text, status)

        # non-registered customer
        elif customer is not None and customer.password_hash is None:
            redirect_to = 'register'
            flash(
                (
                    'You have not registered for the self-care portal. '
                    'Please register before proceeding.'
                ), 'danger'
            )

        # invalid customer
        else:
            redirect_to = 'forgot'
            flash('Invalid customer number.', 'danger')

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
            flash('OTP verification failed. Please try again.', 'danger')

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

        flash('Password saved successfully!', 'success')
        return redirect(url_for('login'))

    return render_template(
        'set_password.html',
        form=form
    )


@app.route('/portal', methods=['GET'])
def portal():
    """Route for self-care portal."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))

    # user logged in
    elif session.get('user_logged_in'):
        # check if session variable exists for customer data
        if not session.get('portal_customer_data'):
            # Get customer info
            user_info = GetCustomerInfo(app)
            user_info.request(session['portal_customer_no'])
            user_info.response()
            # add customer data to session for quick access
            session['portal_customer_data'] = user_info.to_dict()

        # check if session variable exists for active plans
        if not session.get('portal_active_plans'):
            user_data = session['portal_customer_data']
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
                for (_, plan_code, validity_period) in user_data['active_plans']
                if plan_code in plans
            }
            # store in session variable
            session['portal_active_plans'] = active_plans

        return render_template(
            'portal.html',
            cust_data=session['portal_customer_data'],
            active_plans=session['portal_active_plans'],
        )


# Portal actions

@app.route('/portal/recharge', methods=['GET', 'POST'])
def recharge():
    """Route for self-care portal recharge."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        if request.method == 'POST':
            # store amount in session
            session['portal_amount'] = request.form['amount']
            # store selected plan code in session
            session['portal_plan_code'] = request.form['plan_code']
            # generate and store a transaction id
            session['portal_order_id'] = order_no_gen()

            # retrieve customer data
            customer_data = session['portal_customer_data']

            # Check payment gateway
            if request.form['gateway'] == 'paytm':
                # Get Paytm form data
                form_data = initiate_transaction(
                    order_id=session['portal_order_id'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=customer_data['contact_no'],
                    amount=request.form['amount'],
                    # _ is used as the delimiter; check Paytm docs
                    pay_source='portal_recharge',
                )

            elif request.form['gateway'] == 'razorpay':
                # Get Razorpay form data
                form_data = make_order(
                    order_id=session['portal_order_id'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=customer_data['contact_no'],
                    amount=session['portal_amount'],
                    # list is used for passing data; check Razorpay docs
                    pay_source=['portal', 'recharge'],
                )

            return render_template(
                '{}_pay.html'.format(request.form['gateway']),
                form=form_data,
            )

        elif request.method == 'GET':
            # check if session variable exists for inactive plans
            if not session.get('portal_inactive_plans'):
                user_data = session['portal_customer_data']
                plans = {
                    row.plan_code: row
                    for row in TariffInfo.query.options(FromCache(CACHE)).all()
                }
                # get inactive plans
                # {plan_name: (price, validity, plan_code) }
                inactive_plans = {
                    plans[plan_code].plan_name: (
                        plans[plan_code].price, validity_period, plan_code
                    )
                    for (_, plan_code, validity_period) in
                    user_data['inactive_plans'] if plan_code in plans
                }
                # store in session variable
                session['portal_inactive_plans'] = inactive_plans

            return render_template(
                'recharge.html',
                active_plans=session['portal_active_plans'],
                inactive_plans=session['portal_inactive_plans'],
            )


@app.route('/portal/add_plan', methods=['GET', 'POST'])
def add_plan():
    """Route for self-care portal add plan."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        if request.method == 'POST':
            # store amount in session
            session['portal_amount'] = request.form['amount']
            # store selected plan code in session
            session['portal_plan_code'] = request.form['plan_code']
            # generate and store a transaction id
            session['portal_order_id'] = order_no_gen()

            # retrieve customer data
            customer_data = session['portal_customer_data']

            # Check payment gateway
            if request.form['gateway'] == 'paytm':
                # Get Paytm form data
                form_data = initiate_transaction(
                    order_id=session['portal_order_id'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=customer_data['contact_no'],
                    amount=request.form['amount'],
                    # _ is used as the delimiter; check Paytm docs
                    pay_source='portal_addplan',
                )

            elif request.form['gateway'] == 'razorpay':
                # Get Razorpay form data
                form_data = make_order(
                    order_id=session['portal_order_id'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=customer_data['contact_no'],
                    amount=session['portal_amount'],
                    # list is used for passing data; check Razorpay docs
                    pay_source=['portal', 'addplan'],
                )

            return render_template(
                '{}_pay.html'.format(request.form['gateway']),
                form=form_data,
            )

        elif request.method == 'GET':
            # check if session variable exists for available plans
            if not session.get('portal_available_plans'):
                user_data = session['portal_customer_data']
                plans = {
                    row.plan_code: row
                    for row in TariffInfo.query.options(FromCache(CACHE)).all()
                }
                # get available plans
                # {plan_name: (price, plan_code) }
                available_plan_codes = set(plans.keys()).\
                    difference(user_data['all_plans'])
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
                # store in session variable
                session['portal_available_plans'] = available_plans

            return render_template(
                'add_plan.html',
                available_plans=session['portal_available_plans'],
            )


@app.route('/portal/receipt/<order_id>/<status>')
def portal_receipt(order_id, status):
    """Route to transaction receipt."""
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cust_data = session['portal_customer_data']

    return render_template(
        'portal_receipt.html',
        customer_no=session['portal_customer_no'],
        customer_name=cust_data['name'],
        amount=session['portal_amount'],
        date_and_time=current_time,
        txn_status=status,
        txn_no=order_id,
    )


@app.route('/portal/docket')
def docket():
    """Route for self-care portal docket."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
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
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
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
                    }
                    add_new_ticket_to_db(ticket_data)

                    msg = 'Docket generated successfully.'
                    status = 'success'
                else:
                    msg = 'Docket could not be generated. Please try again.'
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
                # form=form,
                allowed=False,
            )


@app.route('/portal/close_docket')
def close_docket():
    """Route for self-care close docket."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # open ticket exists
        if session.get('portal_open_ticket_no'):
            ticket_no = session.get('portal_open_ticket_no')

            # Close ticket in MQS
            close_ticket = CloseTicket(app)
            close_ticket.request(ticket_no)
            close_ticket.response()

            # check if success
            if close_ticket.error_no == '0':
                ticket = Ticket.query.filter_by(
                    ticket_no=session['portal_open_ticket_no']
                ).first()
                ticket.status = 'Closed'
                ticket.closing_date = datetime.now().astimezone()
                # close ticket in db
                db = current_app.extensions['sqlalchemy'].db
                db.session.add(ticket)
                db.session.commit()

                msg = 'Docket: {} closed successfully.'.format(ticket_no)
                status = 'success'

                # remove data from session variable
                session.pop('portal_open_ticket_no', None)

            else:
                msg = (
                    'Docket: {} couldn\'t be closed successfully, please try '
                    'again.'
                ).format(ticket_no)
                status = 'danger'

        # no open ticket exists
        elif not session.get('portal_open_ticket_no'):
            msg = 'No open ticket exists.'
            status = 'danger'

        flash(msg, status)
        return redirect(url_for('docket'))


@app.route('/portal/usage')
def usage():
    """Route for self-care portal usage."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # check if session variable exists for customer username
        if not session.get('portal_username'):
            customer = CustomerInfo.query.filter_by(
                customer_no=session['portal_customer_no']
            ).first()
            session['portal_username'] = customer.user_name

        # get current day and 60 days old date
        today = datetime.now().astimezone().date()
        past = today - timedelta(days=60)

        # get usage data using API call
        usage_details = GetUsageDetails()
        usage_details.request(
            user_name=session['portal_username'],
            start_date=past.strftime("%d%m%Y"),
            end_date=today.strftime("%d%m%Y")
        )
        usage_details.response()

        return render_template(
            'usage.html',
            usage_details=usage_details.usage
        )


@app.route('/portal/transaction_history')
def transaction_history():
    """Route for self-care transaction history."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        # retrieve data from db
        transactions = RechargeEntry.query.filter_by(
            customer_no=session['portal_customer_no']
        ).all()
        return render_template(
            'transaction_history.html',
            transactions=transactions,
        )


@app.route('/portal/change_password', methods=['GET', 'POST'])
def change_password():
    """Route for self-care portal password change."""
    # user not logged in
    if not session.get('user_logged_in'):
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session.get('user_logged_in'):
        form = UpdateProfileForm()

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
                    flash(
                        'You can\'t use your old password as the new one.'
                        , 'danger'
                    )
                else:
                    # generate new hashed password and store
                    hashed_pwd = pbkdf2_sha256.hash(str(form.new_password.data))
                    customer.password_hash = hashed_pwd

                    # make synchronous call to save password
                    db = current_app.extensions['sqlalchemy'].db
                    db.session.add(customer)
                    db.session.commit()

                    flash('Password saved successfully!', 'success')
            # old password is incorrect
            else:
                flash(
                    'Old password entered is incorrect, please try again.'
                    , 'danger'
                )

            return redirect(url_for('change_password'))

        # GET request
        return render_template(
            'change_password.html',
            form=form,
        )
