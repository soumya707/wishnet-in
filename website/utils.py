# -*- coding: utf-8 -*-

"""Define helper functions for the application."""

import csv
import random
import string
from datetime import datetime
from pathlib import Path

import requests
from passlib.totp import generate_secret


def order_no_gen():
    """Generate random order numbers."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


def send_sms(url, data):
    """Send SMS to customer."""
    res = requests.get(url, params=data)
    return res.ok


def verify_mqs_topup(topup):
    """Verify the topup status in MQS."""
    # success in MQS
    if topup.error_no == '0':
        db_entry_status = 'SUCCESS'
        status = 'successful'
        msg = (
            'Payment received and recharge successful. '
            'Kindly await for plan activation.'
            )
        msg_stat = 'success'
    # failure in MQS
    else:
        db_entry_status = 'FAILURE'
        status = 'unsuccessful'
        msg = (
            'Payment received but recharge failed.'
            'We will revert within 24 hours.'
        )
        msg_stat = 'danger'

    return db_entry_status, status, msg, msg_stat


def verify_mqs_addplan(add_plan):
    """Verify the add plan status in MQS."""
    # success in MQS
    if add_plan.error_no == '0':
        db_entry_status = 'SUCCESS'
        status = 'successful'
        msg = (
            'Payment received and plan added. '
            'Kindly await for plan activation.'
            )
        msg_stat = 'success'
    # failure in MQS
    else:
        db_entry_status = 'FAILURE'
        status = 'unsuccessful'
        msg = (
            'Payment received but plan addition failed.'
            'We will revert within 24 hours.'
        )
        msg_stat = 'danger'

    return db_entry_status, status, msg, msg_stat


def verify_mqs_updateprofile(update_profile):
    """Verify the update profile status in MQS."""
    # success in MQS
    if update_profile.error_no == '0':
        db_entry_status = 'SUCCESS'
        msg = (
            'Profile updated successfully! The changes will take effect the '
            'next time you log in.'
        )
        msg_stat = 'success'
    # failure in MQS
    else:
        db_entry_status = 'FAILURE'
        msg = (
            'There was an error while updating your profile. '
            'Please open a ticket or contact us.'
        )
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
