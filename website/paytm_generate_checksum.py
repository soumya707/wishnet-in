# -*- coding: utf-8 -*-

from website.Checksum import generate_checksum
from website import app


def get_form_data(order_id, cust_id):
    """Generate checksum and form data for making transactions via Paytm."""

    paytm_params = {
        'MID' : app.config['PAYTM_MID'],
        'ORDER_ID' : order_id,
        'CUST_ID' : cust_id,
        'CHANNEL_ID' : app.config['PAYTM_CHANNELID'],
        'WEBSITE' : app.config['PAYTM_WEBSITE'],
        # "MOBILE_NO" : "CUSTOMER_MOBILE_NUMBER",
        # "EMAIL" : "CUSTOMER_EMAIL",
        'INDUSTRY_TYPE_ID' : app.config['PAYTM_INDUSTRYTYPE'],
        'TXN_AMOUNT' : '1.00',
        'CALLBACK_URL' : app.config['PAYTM_CALLBACKURL'],

    }

    # Generate checksum for parameters we have
    checksum = generate_checksum(paytm_params, app.config['PAYTM_MKEY'])
    paytm_params['CHECKSUMHASH'] = str(checksum)

    return paytm_params
