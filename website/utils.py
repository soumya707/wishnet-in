# -*- coding: utf-8 -*-

"""Define helper functions for the application."""

import csv
import random
import string
from datetime import datetime
from pathlib import Path

import requests
from passlib.totp import generate_secret

from website.messages import (
    SUCCESSFUL_ADDPLAN, SUCCESSFUL_PROFILE_UPDATE, SUCCESSFUL_RECHARGE,
    UNSUCCESSFUL_ADDPLAN, UNSUCCESSFUL_PROFILE_UPDATE, UNSUCCESSFUL_RECHARGE)


def order_no_gen():
    """Generate random order numbers."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


def send_sms(url, data):
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


def verify_mqs_topup(topup):
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


def verify_mqs_addplan(add_plan):
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


def verify_mqs_updateprofile(update_profile):
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


def generate_otp_secret(filepath):
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


def retrieve_otp_secret(filepath):
    """Retrieves OTP secret key from filepath."""
    with open(filepath, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = [row for row in reader]
        return {
            str(rows[-1].get('date')): str(rows[-1].get('key'))
        }


def get_usage(usage, offset=0, per_page=10):
    """Helper function for retrieving paginated usage information."""
    return usage[offset: offset + per_page]
