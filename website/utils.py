# -*- coding: utf-8 -*-

"""Define helper functions for the application."""

import csv
import random
import string
from datetime import datetime
from pathlib import Path

from passlib.totp import generate_secret


class AvailablePlans():
    """Define all the available plans."""

    def __init__(self, filepath, **kwds):
        super(AvailablePlans, self).__init__(**kwds)
        self.all_plans = self._get_all_plans_data(filepath)

    def _get_all_plans_data(self, filepath):
        with open(filepath, 'r') as csvfile:
            plan_reader = csv.reader(csvfile)
            # skip header
            next(plan_reader)
            # {plan_code: (plan_name, price)}
            return {row[2]: (row[0], row[3]) for row in plan_reader}


def order_no_gen():
    """Generate random order numbers."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=16))


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
