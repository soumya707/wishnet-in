# -*- coding: utf-8 -*-

"""Define functions for Paytm transactions."""

import json

import requests
from flask import url_for

from website import app
from website.Checksum import generate_checksum, verify_checksum


def initiate_transaction(order_id, cust_info):
    """Generate checksum and form data for making transactions via Paytm."""

    paytm_params = {
        'MID' : app.config['PAYTM_MID'],
        'ORDER_ID' : order_id,
        'CUST_ID' : cust_info.cust_no,
        'CHANNEL_ID' : app.config['PAYTM_CHANNELID'],
        'WEBSITE' : app.config['PAYTM_WEBSITE'],
        "MOBILE_NO" : cust_info.contact_no,
        "EMAIL" : cust_info.email,
        'INDUSTRY_TYPE_ID' : app.config['PAYTM_INDUSTRYTYPE'],
        'TXN_AMOUNT' : '1.00',
        'CALLBACK_URL' : app.config['PAYTM_CALLBACKURL'],
    }

    # Generate checksum for parameters we have
    checksum = generate_checksum(paytm_params, app.config['PAYTM_MKEY'])
    paytm_params['CHECKSUMHASH'] = str(checksum)

    return paytm_params


def verify_transaction(response):
    """Verify the response."""

    paytm_params = {}
    for key, value in response.items():
        if key == 'CHECKSUMHASH':
            paytm_checksum = value
        else:
            paytm_params[key] = value

    return verify_checksum(
        paytm_params,
        app.config['PAYTM_MKEY'],
        paytm_checksum
    )


def verify_final_status(order_id):
    """Verify final status of transaction."""

    paytm_params = {
        'MID' : app.config['PAYTM_MID'],
        'ORDER_ID' : order_id,
    }

    checksum = generate_checksum(paytm_params, app.config['PAYTM_MKEY'])

    paytm_params['CHECKSUMHASH'] = checksum

    # prepare JSON string for request
    post_data = json.dumps(paytm_params)

    # for Production
    url = "https://securegw.paytm.in/order/status"

    response = requests.post(
        url,
        data=post_data,
        headers={"Content-type": "application/json"}
    ).json()

    response_code_dict = {
        '1': 'Transaction success.',
        '227': ('Your payment has been declined by your bank. Please contact '
                'your bank for any queries. If money has been deducted from '
                'your account, you will receive a refund within 48 hrs.'),
        '235': 'Wallet balance insufficient',
        '295': ('Your payment failed as the UPI ID entered is incorrect. '
                'Please try again by entering a valid VPA or use a different '
                'method to complete the payment.'),
        '334': 'Invalid Order ID.',
        '400': 'Transaction status not confirmed yet.',
        '401': ('Your payment has been declined by your bank. Please contact '
                'your bank for any queries. If money has been deducted from '
                'your account, you will receive a refund within 48 hrs.'),
        '402': ('Looks like the payment is not complete. Please wait while we '
                'confirm the status with your bank.'),
        '810': 'Transaction failed.',
    }

    return response_code_dict.get(response['RESPCODE'])
