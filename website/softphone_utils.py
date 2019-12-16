# -*- coding: utf-8 -*-


"""Utilities for interacting with Softphone service."""


import requests

from website import app


def add_softphone(url, softphone_number, password, user_name):
    """Add softphone number."""

    # prepare data for payload
    data = {
        'source': 'test',
        'function': 'add_phone',
        'user': app.config['SOFTPHONE_USER'],
        'pass': app.config['SOFTPHONE_PWD'],
        'extension': softphone_number,
        'dialplan_number': softphone_number,
        'voicemail_id': softphone_number,
        'phone_login': softphone_number,
        'phone_pass': password,
        'server_ip': app.config['SOFTPHONE_SERVER_IP'],
        'protocol': 'SIP',
        'registration_password': password,
        'phone_full_name': user_name,
        'local_gmt': '-5.00',
        'outbound_cid': softphone_number
    }

    try:
        res = requests.post(url, params=data, timeout=10)
        # check if request is successful
        if res.ok:
            success = True
        else:
            success = False
    except ConnectionError as _:
        success = False

    return success


def update_softphone(url, softphone_number, password, user_name):
    """Update softphone number."""

    # prepare data for payload
    data = {
        'source': 'test',
        'function': 'update_phone',
        'user': app.config['SOFTPHONE_USER'],
        'pass': app.config['SOFTPHONE_PWD'],
        'extension': softphone_number,
        'dialplan_number': softphone_number,
        'voicemail_id': softphone_number,
        'phone_login': softphone_number,
        'phone_pass': password,
        'server_ip': app.config['SOFTPHONE_SERVER_IP'],
        'protocol': 'SIP',
        'registration_password': password,
        'phone_full_name': user_name,
        'local_gmt': '-5.00',
        'outbound_cid': softphone_number
    }

    try:
        res = requests.post(url, params=data, timeout=5)
        # check if request is successful
        if res.ok:
            success = True
        else:
            success = False
    except ConnectionError as _:
        success = False

    return success


def activate_softphone(url, softphone_number, password, user_name):
    """Activate softphone number."""

    # prepare data for payload
    data = {
        'source': 'test',
        'function': 'update_phone',
        'user': app.config['SOFTPHONE_USER'],
        'pass': app.config['SOFTPHONE_PWD'],
        'extension': softphone_number,
        'dialplan_number': softphone_number,
        'voicemail_id': softphone_number,
        'phone_login': softphone_number,
        'phone_pass': password,
        'server_ip': app.config['SOFTPHONE_SERVER_IP'],
        'protocol': 'SIP',
        'registration_password': password,
        'phone_full_name': user_name,
        'local_gmt': '-5.00',
        'outbound_cid': softphone_number,
        'active': 'Y'
    }

    try:
        res = requests.post(url, params=data, timeout=5)
        # check if request is successful
        if res.ok:
            success = True
        else:
            success = False
    except ConnectionError as _:
        success = False

    return success


def deactivate_softphone(url, softphone_number, password, user_name):
    """Deactivate softphone number."""

    # prepare data for payload
    data = {
        'source': 'test',
        'function': 'update_phone',
        'user': app.config['SOFTPHONE_USER'],
        'pass': app.config['SOFTPHONE_PWD'],
        'extension': softphone_number,
        'dialplan_number': softphone_number,
        'voicemail_id': softphone_number,
        'phone_login': softphone_number,
        'phone_pass': password,
        'server_ip': app.config['SOFTPHONE_SERVER_IP'],
        'protocol': 'SIP',
        'registration_password': password,
        'phone_full_name': user_name,
        'local_gmt': '-5.00',
        'outbound_cid': softphone_number,
        'active': 'N'
    }

    try:
        res = requests.post(url, params=data, timeout=5)
        # check if request is successful
        if res.ok:
            success = True
        else:
            success = False
    except ConnectionError as _:
        success = False

    return success
