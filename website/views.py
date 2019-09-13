# -*- coding: utf-8 -*-

"""Views for the website."""


import random
import string
from datetime import datetime

from flask import (
    current_app, flash, redirect, render_template, request, session, url_for)
from flask_sqlalchemy_caching import FromCache
from flask_wtf.csrf import CSRFProtect
from passlib.exc import MalformedTokenError, TokenError
from passlib.hash import pbkdf2_sha256
from sqlalchemy import or_

from website import PLANS, TOTPFACTORY, app, CACHE
from website.forms import (
    ForgotPasswordForm, GetCustomerNumberForm, LoginForm, NewConnectionForm,
    OTPVerificationForm, RechargeForm, RegistrationForm, SetPasswordForm,
    UpdateProfileForm)
from website.models import (
    FAQ, BestPlans, CarouselImages, CustomerInfo, CustomerLogin, Downloads,
    JobVacancy, RechargeEntry, RegionalOffices, Services, Ventures)
from website.mqs_api import (
    CloseTicket, ContractsByKey, GetCustomerInfo, Recharge, RegisterTicket)
from website.paytm_utils import (
    initiate_transaction, verify_final_status, verify_transaction)
from website.razorpay_utils import make_order, verify_signature
from website.tasks import (
    add_new_connection_data_to_db, add_recharge_data_to_db,
    send_async_new_connection_mail)
from website.utils import order_no_gen


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
            # Get active plans for the user
            # {plan_name: (price, validity, plan_code)}
            active_plans = {
                PLANS.all_plans[plan_code][0]: (
                    PLANS.all_plans[plan_code][1], validity, plan_code
                )
                for (plan_code, validity) in user_contracts.active_plans
                if plan_code in PLANS.all_plans
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
            mobile_no = customer.mobile_no
            sms_msg = (
                'Please find your Customer Number: {} as requested by '
                'you.\nTeam Wishnet'
            ).format(customer.customer_no)
            #TODO: add SMS API
            flash(
                (
                    'Customer number: {} has been sent to your registered '
                    'mobile number.'
                ).format(customer.customer_no)
                , 'success'
            )
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
                amount=request.form['amount']
            )

        elif request.form['gateway'] == 'razorpay':
            # Get Razorpay form data
            form_data = make_order(
                order_id=order_id,
                customer_no=session['insta_customer_no'],
                customer_mobile_no=session['insta_customer_mobile_no'],
                amount=request.form['amount']
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
        # Paytm
        if gateway == 'paytm':
            # store response data
            recharge_data = {
                'customer_no': session['insta_customer_no'],
                'wishnet_order_id': session['insta_order_id'],
                'payment_gateway': 'Paytm',
                'txn_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            }

            # initial checksum verification
            verified = verify_transaction(request.form)

            # check verification success
            if verified:
                recharge_data.update(txn_order_id=request.form['TXNID'])
                # final status verification
                final_status_code = verify_final_status(
                    session['insta_order_id']
                )

                # check if transaction successful
                if final_status_code == '01':
                    recharge_data.update(
                        txn_amount=request.form['TXNAMOUNT'],
                        txn_datetime=str(request.form['TXNDATE']),
                        txn_status='SUCCESS'
                    )

                    # TopUp in MQS
                    top_up = Recharge(app)
                    top_up.request(
                        session['insta_customer_no'],
                        session['insta_plan_code']
                    )
                    top_up.response()

                    recharge_data['topup_ref_id'] = top_up.ref_no
                    recharge_data['topup_datetime'] = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S.%f"
                    )

                    # success in MQS
                    if top_up.error_no == '0':
                        recharge_data['topup_status'] = 'SUCCESS'
                        status = 'successful'
                        flash(
                            (
                                'Payment received and recharge successful. '
                                'Kindly await for plan activation.'
                            ), 'success'
                        )
                    # failure in MQS
                    else:
                        recharge_data['topup_status'] = 'FAILURE'
                        status = 'unsuccessful'
                        flash(
                            (
                                'Payment received but recharge failed.'
                                'We will revert within 24 hours.'
                            ), 'danger'
                        )
                # Transaction Status failure
                else:
                    recharge_data.update(
                        txn_amount='',
                        txn_status='FAILURE',
                        topup_ref_id='',
                        topup_datetime='',
                        topup_status='',
                    )
                    status = 'unsuccessful'
                    flash(
                        'Payment incomplete! Please check with {}.'.\
                        format(gateway.capitalize()), 'danger'
                    )
            # checksumhash verification failure
            # data tampered during transaction
            elif not verified:
                recharge_data.update(
                    txn_order_id='',
                    txn_amount='',
                    txn_status='CHECKSUM VERIFICATION FAILURE',
                    topup_ref_id='',
                    topup_datetime='',
                    topup_status='',
                )
                status = 'unsuccessful'
                flash('Payment failed! Please try again.', 'danger')

        # Razorpay
        elif gateway == 'razorpay':
            # store response data
            recharge_data = {
                'customer_no': session['insta_customer_no'],
                'wishnet_order_id': session['insta_order_id'],
                'payment_gateway': 'Razorpay',
                'txn_datetime': datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
            }

            verified = verify_signature(request.form)
            # signature verification success
            if verified:
                recharge_data.update(
                    txn_order_id=request.form['razorpay_order_id'],
                    txn_amount=session['insta_amount'],
                    txn_status='SUCCESS',
                )

                # TopUp in MQS
                top_up = Recharge(app)
                top_up.request(
                    session['insta_customer_no'],
                    session['insta_plan_code']
                )
                top_up.response()

                recharge_data['topup_ref_id'] = top_up.ref_no
                recharge_data['topup_datetime'] = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S.%f"
                )

                # success in MQS
                if top_up.error_no == '0':
                    recharge_data['topup_status'] = 'SUCCESS'
                    status = 'successful'
                    flash(
                        (
                            'Payment received and recharge successful. '
                            'Kindly await for plan activation.'
                        ), 'success'
                    )
                # failure in MQS
                else:
                    recharge_data['topup_status'] = 'FAILURE'
                    status = 'unsuccessful'
                    flash(
                        (
                            'Payment received but recharge failed.'
                            'We will revert within 24 hours.'
                        ), 'danger'
                    )

            # signature verification failure
            # data tampered during transaction
            else:
                recharge_data.update(
                    txn_order_id='',
                    txn_amount='',
                    txn_status='SIGNATURE VERIFICATION FAILURE',
                    topup_ref_id='',
                    topup_datetime='',
                    topup_status='',
                )
                status = 'unsuccessful'
                flash('Recharge failed! Please try again.', 'danger')

        # add recharge data to db async
        add_recharge_data_to_db.delay(recharge_data)

        return redirect(
            url_for(
                'receipt',
                order_id=session['insta_order_id'],
                status=status
            )
        )


@app.route('/receipt/<order_id>/<status>')
def receipt(order_id, status):
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
    if session['user_logged_in']:
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
    if session['user_logged_in']:
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
    # user not logged in (invalid access to route)
    elif not session['user_logged_in']:
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
            # TODO: add sms api for sending otp
            # generate OTP
            totp = TOTPFACTORY.new()
            session['otp_data'] = totp.to_dict()

            session['customer_no'] = form.customer_no.data
            redirect_to = 'verify_otp'
            flash(
                'OTP:{} has been sent to your registered mobile number.'.format(
                    totp.generate().token
                ),
                'success'
            )

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
            # TODO: add sms api for sending otp
            # generate OTP
            totp = TotpFactory.new()
            session['otp_data'] = totp.to_dict()

            session['customer_no'] = form.customer_no.data
            redirect_to = 'verify_otp'
            flash(
                'OTP:{} has been sent to your registered mobile number.'.format(
                    totp.generate().token
                ),
                'success'
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
    if not session['user_logged_in']:
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))

    # user logged in
    elif session['user_logged_in']:
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
            # get active plans
            # {plan_name: (price, validity, plan_code) }
            active_plans = {
                PLANS.all_plans[plan_code][0]: (
                    PLANS.all_plans[plan_code][1], validity, plan_code
                )
                for (_, plan_code, validity) in user_data['active_plans']
                if plan_code in PLANS.all_plans
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
    if not session['user_logged_in']:
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session['user_logged_in']:
        if request.method == 'POST':
            # store amount in session
            session['portal_amount'] = request.form['amount']
            # store selected plan code in session
            session['portal_plan_code'] = request.form['plan_code']
            # generate and store a transaction id
            session['portal_order_no'] = order_no_gen()

            # retrieve customer data
            customer_data = session['portal_customer_data']

            # Check payment gateway
            if request.form['gateway'] == 'paytm':
                # Get Paytm form data
                form_data = initiate_transaction(
                    order_id=session['portal_order_no'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=customer_data['contact_no'],
                    amount=session['portal_amount']
                )

            elif request.form['gateway'] == 'razorpay':
                # Get Razorpay form data
                form_data = make_order(
                    order_id=session['portal_order_no'],
                    customer_no=session['portal_customer_no'],
                    customer_mobile_no=customer_data['contact_no'],
                    amount=session['portal_amount']
                )

            return render_template(
                '{}_pay.html'.format(request.form['gateway']),
                form=form_data,
            )

        elif request.method == 'GET':
            # check if session variable exists for inactive plans
            if not session.get('portal_inactive_plans'):
                user_data = session['portal_customer_data']
                # get inactive plans
                # {plan_name: (price, validity, plan_code) }
                inactive_plans = {
                    PLANS.all_plans[plan_code][0]: (
                        PLANS.all_plans[plan_code][1], validity, plan_code
                    )
                    for (_, plan_code, validity) in user_data['inactive_plans']
                    if plan_code in PLANS.all_plans
                }
                # store in session variable
                session['portal_inactive_plans'] = inactive_plans

            return render_template(
                'recharge.html',
                active_plans=session['portal_active_plans'],
                inactive_plans=session['portal_inactive_plans'],
            )


@app.route('/portal/add_plan')
def add_plan():
    """Route for self-care portal add plan."""
    # user not logged in
    if not session['user_logged_in']:
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session['user_logged_in']:
        # check if session variable exists for available plans
        if not session.get('portal_available_plans'):
            user_data = session['portal_customer_data']
            # get available plans
            # {plan_name: (price, plan_code) }
            available_plan_codes = set(PLANS.all_plans.keys()).\
                difference(user_data['all_plans'])
            available_plans = {
                PLANS.all_plans[plan_code][0]: (
                    PLANS.all_plans[plan_code][1], plan_code
                )
                for plan_code in available_plan_codes
            }

        return render_template(
            'add_plan.html',
            available_plans=available_plans,
        )


@app.route('/portal/docket')
def docket():
    """Route for self-care portal docket."""
    # user not logged in
    if not session['user_logged_in']:
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session['user_logged_in']:
        return render_template(
            'docket.html'
        )


@app.route('/portal/usage')
def usage():
    """Route for self-care portal usage."""
    # user not logged in
    if not session['user_logged_in']:
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session['user_logged_in']:
        return render_template(
            'usage.html'
        )


@app.route('/portal/transaction_history')
def transaction_history():
    """Route for self-care transaction history."""
    # user not logged in
    if not session['user_logged_in']:
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session['user_logged_in']:
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
    if not session['user_logged_in']:
        flash('You have not logged in yet.', 'danger')
        return redirect(url_for('login'))
    # user logged in
    elif session['user_logged_in']:
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
