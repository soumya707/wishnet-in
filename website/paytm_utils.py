# -*- coding: utf-8 -*-

"""Define functions for Paytm transactions."""


from typing import Dict

import requests

from website import app
from website.Checksum import generate_checksum, verify_checksum


def initiate_transaction(
        order_id: str,
        customer_no: str,
        customer_mobile_no: str,
        amount: str,
        pay_source: str) -> Dict[str, str]:
    """Generate checksum and form data for making transactions via Paytm."""
    paytm_params = {
        'MID' : app.config['PAYTM_MID'],
        'ORDER_ID' : order_id,
        'CUST_ID' : customer_no,
        'CHANNEL_ID' : app.config['PAYTM_CHANNELID'],
        'WEBSITE' : app.config['PAYTM_WEBSITE'],
        "MOBILE_NO" : customer_mobile_no,
        'INDUSTRY_TYPE_ID' : app.config['PAYTM_INDUSTRYTYPE'],
        'TXN_AMOUNT' : amount,
        'CALLBACK_URL' : app.config['PAYTM_CALLBACKURL'],
        'MERC_UNQ_REF': pay_source,
    }
    # Generate checksum for parameters we have
    paytm_params['CHECKSUMHASH'] = generate_checksum(
        paytm_params,
        app.config['PAYTM_MKEY']
    )

    return paytm_params


def verify_transaction(response: Dict[str, str]) -> bool:
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


def verify_final_status(order_id: str) -> str:
    """Verify final status of transaction."""
    paytm_params = {
        'MID' : app.config['PAYTM_MID'],
        'ORDER_ID' : order_id,
    }
    paytm_params['CHECKSUMHASH'] = generate_checksum(
        paytm_params,
        app.config['PAYTM_MKEY']
    )
    url = 'https://securegw.paytm.in/order/status'
    response = requests.post(
        url,
        json=paytm_params,
        headers={'Content-type': 'application/json'}
    ).json()

    return response['RESPCODE']
