# -*- coding: utf-8 -*-

"""Define the forms to be used."""

import csv
import re

from flask_wtf import FlaskForm
from wtforms import (
    PasswordField, SelectField, StringField, SubmitField, TextAreaField)
from wtforms.validators import (
    DataRequired, Email, IPAddress, Length, Optional, Regexp)


def get_sorted_location(filepath):
    """Returns tuple of city names for use in form."""
    with open(filepath, 'r') as csvfile:
        location_reader = csv.reader(csvfile)
        return sorted([(row[0], row[0]) for row in location_reader])


class RechargeForm(FlaskForm):
    """Class for recharge form."""
    user_id = StringField(
        'User ID',
        validators=[DataRequired()],
        render_kw={'placeholder': 'Customer Number'})
    submit = SubmitField('Insta-Recharge')


class NewConnectionForm(FlaskForm):
    """Class for new connection form."""
    pin_code_msg = 'Invalid postal code'
    phone_no_msg = 'Invalid mobile no.'
    email_msg = 'Invalid e-mail address'

    first_name = StringField('First Name', validators=[DataRequired()])
    middle_name = StringField('Middle Name')
    last_name = StringField('Last Name', validators=[DataRequired()])
    address = StringField('Address', validators=[DataRequired()])
    location = SelectField(
        'Location',
        choices=get_sorted_location('website/location_for_new_connection.csv'),
        validators=[DataRequired()]
    )
    postal_code = StringField(
        'Pin code',
        validators=[
            DataRequired(),
            Regexp(r'^[7]+\d{1,6}$', message=pin_code_msg)
        ]
    )
    phone_no = StringField(
        'Mobile no.',
        validators=[
            DataRequired(),
            Regexp(r'^\d{1,10}$', message=phone_no_msg)
        ]
    )
    email_address = StringField(
        'E-mail',
        validators=[
            DataRequired(),
            Email(message=email_msg)
        ]
    )
    remark = TextAreaField('Remarks', validators=[Length(max=200)])
    submit = SubmitField('Submit')


class GetCustomerNumberForm(FlaskForm):
    """Class for getting customer number."""
    username = StringField(
        'Username',
        render_kw={'placeholder': 'Username'},
        validators=[Optional()]
    )
    ip_address = StringField(
        'IP Address',
        render_kw={'placeholder': 'IP Address'},
        validators=[
            Optional(),
            IPAddress(message='Invalid IP address'),
        ]
    )

    submit = SubmitField('Get')


class AuthenticationForm(FlaskForm):
    """Class for authentication form."""
    customer_no = StringField('Customer Number', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Sign in')


class RegistrationForm(FlaskForm):
    """Class for registration form."""
    customer_no = StringField('Customer Number', validators=[DataRequired()])
    submit = SubmitField('Get OTP')


class ForgotPasswordForm(FlaskForm):
    """Class for forgot password form."""
    customer_no = StringField('Customer Number', validators=[DataRequired()])
    submit = SubmitField('Get OTP')
