# -*- coding: utf-8 -*-

"""Define functions for Razorpay transactions."""

import razorpay
import requests

from website import app


def make_order(order_id, cust_info, amount):
    """Generate an order from Razorpay."""

    post_data = {
        'amount': amount.replace('.', ''),
        'currency': 'INR',
        'receipt': order_id,
        'payment_capture': '1',
        'notes': {'cust_no': str(cust_info['cust_no'])}
    }

    order_resp = requests.post(
        'https://api.razorpay.com/v1/orders',
        auth=(app.config['RAZORPAY_KEY'], app.config['RAZORPAY_SECRET']),
        json=post_data,
        headers={'Content-Type': 'application/json'}
    ).json()

    razorpay_order_id = order_resp['id']

    razorpay_params = {
        'key_id': app.config['RAZORPAY_KEY'],
        'name': 'Wish Net Pvt. Ltd.',
        'order_id': razorpay_order_id,
        # 'prefill[email]': cust_info.get('email'),
        'prefill[contact]': cust_info.get('contact_no'),
        'callback_url': app.config['RAZORPAY_CALLBACKURL'],
        'cancel_url': app.config['RAZORPAY_CANCELURL'],
    }

    return razorpay_order_id, razorpay_params


def verify_signature(response):
    """Verify payment signature obtained from Razorpay."""

    client = razorpay.Client(auth=(app.config['RAZORPAY_KEY'],
                                   app.config['RAZORPAY_SECRET']))
    return client.utility.verify_payment_signature(response)
