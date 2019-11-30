# -*- coding: utf-8 -*-

"""Define functions for Razorpay transactions."""

import razorpay

from website import app


def make_order(
        order_id,
        customer_no,
        customer_mobile_no,
        customer_email,
        amount,
        pay_source):
    """Generate an order from Razorpay."""

    post_data = {
        'amount': amount.replace('.', ''),
        'currency': 'INR',
        'receipt': order_id,
        'payment_capture': '1',
        'notes': {
            'customer_no': customer_no,
            'pay_source': pay_source[0],
            'txn_type': pay_source[1],
        }
    }

    client = razorpay.Client(auth=(app.config['RAZORPAY_KEY'],
                                   app.config['RAZORPAY_SECRET']))
    order_resp = client.order.create(data=post_data)

    razorpay_order_id = order_resp['id']

    razorpay_params = {
        'key_id': app.config['RAZORPAY_KEY'],
        'name': 'Wish Net Pvt. Ltd.',
        'order_id': razorpay_order_id,
        'prefill[email]': customer_email,
        'prefill[contact]': customer_mobile_no,
        'notes[customer_no]': customer_no,
        'notes[pay_source]': pay_source[0],
        'notes[txn_type]': pay_source[1],
        'callback_url': app.config['RAZORPAY_CALLBACKURL'],
        'cancel_url': app.config['RAZORPAY_CANCELURL']
    }

    return razorpay_params


def verify_signature(response):
    """Verify payment signature obtained from Razorpay."""

    client = razorpay.Client(auth=(app.config['RAZORPAY_KEY'],
                                   app.config['RAZORPAY_SECRET']))
    client.utility.verify_payment_signature(response)


def get_notes(razorpay_order_id):
    """Receive metadata sent as payload to Razopay."""

    client = razorpay.Client(auth=(app.config['RAZORPAY_KEY'],
                                   app.config['RAZORPAY_SECRET']))
    resp = client.order.fetch(razorpay_order_id)
    notes = resp['notes']

    return notes['customer_no'], notes['pay_source'], notes['txn_type']
