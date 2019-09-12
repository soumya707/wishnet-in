# -*- coding: utf-8 -*-

"""Define functions for Razorpay transactions."""

import razorpay
import requests

from website import app


def make_order(order_id, customer_no, customer_mobile_no, amount):
    """Generate an order from Razorpay."""

    post_data = {
        'amount': amount.replace('.', ''),
        'currency': 'INR',
        'receipt': order_id,
        'payment_capture': '1',
        'notes': {'customer_no': customer_no},
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
        'prefill[contact]': customer_mobile_no,
        'callback_url': app.config['RAZORPAY_CALLBACKURL'],
    }

    return razorpay_params


def verify_signature(response):
    """Verify payment signature obtained from Razorpay."""

    client = razorpay.Client(auth=(app.config['RAZORPAY_KEY'],
                                   app.config['RAZORPAY_SECRET']))
    return client.utility.verify_payment_signature(response)
