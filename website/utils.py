# -*- coding: utf-8 -*-

"""Define helper functions for the application."""

import csv
import random
import string
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Callable, Dict, Sequence, Tuple

import requests
from flask import flash, redirect, session, url_for
from passlib.totp import generate_secret

from website.messages import (
    LOG_IN_FIRST, SUCCESSFUL_ADDPLAN, SUCCESSFUL_PROFILE_UPDATE,
    SUCCESSFUL_RECHARGE, UNSUCCESSFUL_ADDPLAN, UNSUCCESSFUL_PROFILE_UPDATE,
    UNSUCCESSFUL_RECHARGE)
from website.mqs_api import AddPlan, Recharge, UpdateProfile


def order_no_gen() -> str:
    """Generate random order numbers."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


def send_sms(url: str, data: Dict[str, str]) -> bool:
    """Send SMS to customer."""
    try:
        # avoid slow responses from server by setting a timeout of 5 seconds
        res = requests.get(url, params=data, timeout=10)
        # check if request is successful
        if res.ok:
            success = True
        else:
            success = False
    except ConnectionError as _:
        success = False

    return success


def verify_mqs_topup(topup: Recharge) -> Tuple[str, str, str, str]:
    """Verify the topup status in MQS."""
    # success in MQS
    if topup.error_no == '0':
        db_entry_status = 'SUCCESS'
        status = 'successful'
        msg = SUCCESSFUL_RECHARGE
        msg_stat = 'success'
    # failure in MQS
    else:
        db_entry_status = 'FAILURE'
        status = 'unsuccessful'
        msg = UNSUCCESSFUL_RECHARGE
        msg_stat = 'danger'

    return db_entry_status, status, msg, msg_stat


def verify_mqs_addplan(add_plan: AddPlan) -> Tuple[str, str, str, str]:
    """Verify the add plan status in MQS."""
    # success in MQS
    if add_plan.error_no == '0':
        db_entry_status = 'SUCCESS'
        status = 'successful'
        msg = SUCCESSFUL_ADDPLAN
        msg_stat = 'success'
    # failure in MQS
    else:
        db_entry_status = 'FAILURE'
        status = 'unsuccessful'
        msg = UNSUCCESSFUL_ADDPLAN
        msg_stat = 'danger'

    return db_entry_status, status, msg, msg_stat


def verify_mqs_updateprofile(update_profile: UpdateProfile) -> \
    Tuple[str, str, str]:
    """Verify the update profile status in MQS."""
    # success in MQS
    if update_profile.error_no == '0':
        db_entry_status = 'SUCCESS'
        msg = SUCCESSFUL_PROFILE_UPDATE
        msg_stat = 'success'
    # failure in MQS
    else:
        db_entry_status = 'FAILURE'
        msg = UNSUCCESSFUL_PROFILE_UPDATE
        msg_stat = 'danger'

    return db_entry_status, msg, msg_stat


def generate_otp_secret(filepath: str) -> None:
    """Generates OTP secret key and stores it in filepath."""
    path = Path(filepath)
    # if file exists
    if path.is_file():
        file_exist = True
    else:
        file_exist = False

    with open(filepath, 'a') as csvfile:
        col_names = ['date', 'key']
        writer = csv.DictWriter(csvfile, fieldnames=col_names)

        if not file_exist:
            writer.writeheader()

        writer.writerow({
            'date': datetime.now().strftime("%Y-%m-%d"),
            'key': generate_secret()
        })


def retrieve_otp_secret(filepath: str) -> Dict[str, str]:
    """Retrieves OTP secret key from filepath."""
    with open(filepath, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = [row for row in reader]
        return {
            str(rows[-1].get('date')): str(rows[-1].get('key'))
        }


def get_usage(usage: Sequence, offset: int = 0, per_page: int = 10) -> Sequence:
    """Helper function for retrieving paginated usage information."""
    return usage[offset: offset + per_page]


def login_required(f: Callable) -> Callable:
    """Decorator function to check user login status of self-care portal."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('user_logged_in'):
            flash(LOG_IN_FIRST, 'danger')
            return redirect(url_for('login'))
        # Keep the session alive
        session.modified = True
        return f(*args, **kwargs)
    return decorated_function
