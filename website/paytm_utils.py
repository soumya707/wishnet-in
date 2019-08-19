# -*- coding: utf-8 -*-

"""Define functions for Paytm transactions."""

import json

from flask import url_for
import requests

from website.Checksum import generate_checksum, verify_checksum
from website import app


def initiate_transaction(order_id, cust_id):
    """Generate checksum and form data for making transactions via Paytm."""

    paytm_params = {
        'MID' : app.config['PAYTM_MID'],
        'ORDER_ID' : order_id,
        'CUST_ID' : cust_id,
        'CHANNEL_ID' : app.config['PAYTM_CHANNELID'],
        'WEBSITE' : app.config['PAYTM_WEBSITE'],
        # "MOBILE_NO" : "7777777777",
        # "EMAIL" : "CUSTOMER_EMAIL",
        'INDUSTRY_TYPE_ID' : app.config['PAYTM_INDUSTRYTYPE'],
        'TXN_AMOUNT' : '1.00',
        'CALLBACK_URL' : app.config['PAYTM_CALLBACKURL'],
    }

    # Generate checksum for parameters we have
    checksum = generate_checksum(paytm_params, app.config['PAYTM_MKEY'])
    paytm_params['CHECKSUMHASH'] = str(checksum)

    return paytm_params


def verify_transaction(response_checksum):
    """Verify the response checksum."""

    paytm_params = {
        'MID' : app.config['PAYTM_MID'],
        'ORDER_ID' : order_id,
        'CUST_ID' : cust_id,
        'CHANNEL_ID' : app.config['PAYTM_CHANNELID'],
        'WEBSITE' : app.config['PAYTM_WEBSITE'],
        # "MOBILE_NO" : "7777777777",
        # "EMAIL" : "CUSTOMER_EMAIL",
        'INDUSTRY_TYPE_ID' : app.config['PAYTM_INDUSTRYTYPE'],
        'TXN_AMOUNT' : '1.00',
        'CALLBACK_URL' : app.config['PAYTM_CALLBACKURL'],

    }

    return verify_checksum(
        paytm_params,
        app.config['PAYTM_MKEY'],
        response_checksum,
    )


def verify_final_status(order_id):
    """Verify final status of transaction."""

    # initialize a dictionary
    paytm_params = {
        'MID' : app.config['PAYTM_MID'],
        'ORDER_ID' : order_id,
    }

    # generate checksum
    checksum = generate_checksum(paytm_params, app.config['PAYTM_MKEY'])

    # put generated checksum value in dictionary
    paytmParams['CHECKSUMHASH'] = checksum

    # prepare JSON string for request
    post_data = json.dumps(paytm_params)

    # for Staging
    url = "https://securegw-stage.paytm.in/order/status"

    # for Production
    # url = "https://securegw.paytm.in/order/status"

    response = requests.post(
        url,
        data=post_data,
        headers={"Content-type": "application/json"}
    ).json()
