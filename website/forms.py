# -*- coding: utf-8 -*-

"""Define the forms to be used."""


from flask_wtf import FlaskForm
from wtforms import (
    PasswordField, SelectField, StringField, SubmitField, TextAreaField)
from wtforms.validators import (
    Email, EqualTo, InputRequired, IPAddress, Length, Optional, Regexp)


class RechargeForm(FlaskForm):
    """Class for recharge form."""
    user_id = StringField(
        'User ID',
        validators=[InputRequired()],
        render_kw={'placeholder': 'Customer ID'}
    )
    submit = SubmitField('Insta-Recharge')


class NewConnectionForm(FlaskForm):
    """Class for new connection form."""
    first_name = StringField('First Name', validators=[InputRequired()])
    middle_name = StringField('Middle Name')
    last_name = StringField('Last Name', validators=[InputRequired()])
    address = StringField('Address', validators=[InputRequired()])
    location = SelectField('Location', validators=[InputRequired()])
    postal_code = StringField(
        'Pin Code',
        validators=[
            InputRequired(),
            Regexp(r'^[7]+\d{5}$', message='Invalid postal code.')
        ]
    )
    phone_no = StringField(
        'Mobile Number',
        validators=[
            InputRequired(),
            Regexp(r'^\d{10}$', message='Invalid mobile number.')
        ]
    )
    email_address = StringField(
        'Email Address',
        validators=[
            InputRequired(),
            Email(message='Invalid email address.')
        ]
    )
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
    submit = SubmitField('Get Customer ID')


class LoginForm(FlaskForm):
    """Class for authentication form."""
    customer_no = StringField('Customer ID', validators=[InputRequired()])
    password = PasswordField('Password', validators=[InputRequired()])
    submit = SubmitField('Sign in')


class RegistrationForm(FlaskForm):
    """Class for registration form."""
    customer_no = StringField('Customer ID', validators=[InputRequired()])
    submit = SubmitField('Get OTP')


class ForgotPasswordForm(FlaskForm):
    """Class for forgot password form."""
    customer_no = StringField('Customer ID', validators=[InputRequired()])
    submit = SubmitField('Get OTP')


class OTPVerificationForm(FlaskForm):
    """Class for verifying OTP form."""
    otp = StringField('Enter OTP', validators=[InputRequired()])
    submit = SubmitField('Verify OTP')


class SetPasswordForm(FlaskForm):
    """Class for setting new password form."""
    password = PasswordField(
        'New Password',
        validators=[
            InputRequired(),
            EqualTo('confirm', message='Passwords must match.')
        ]
    )
    confirm = PasswordField('Repeat Password')
    submit = SubmitField('Set New Password')


class ChangePasswordForm(FlaskForm):
    """Class for changing password form."""
    old_password = PasswordField(
        'Old Password',
        validators=[InputRequired()]
    )
    new_password = PasswordField(
        'New Password',
        validators=[
            InputRequired(),
            EqualTo('confirm', message='New passwords must match.')
        ]
    )
    confirm = PasswordField(
        'Repeat Password',
        validators=[InputRequired()]
    )
    submit = SubmitField('Update Password')


class UpdateProfileForm(FlaskForm):
    """Class for updating profile form."""
    new_phone_no = StringField(
        'New Mobile Number',
        validators=[
            Optional(),
            Regexp(r'^\d{10}$', message='Invalid mobile number.')
        ]
    )
    new_email_address = StringField(
        'New Email Address',
        validators=[
            Optional(),
            Email(message='Invalid email address.')
        ]
    )
    submit = SubmitField('Update Profile')


class NewTicketForm(FlaskForm):
    """Class for submitting a ticket form."""
    nature = SelectField('Ticket Nature', validators=[InputRequired()])
    remarks = TextAreaField(
        'Remarks',
        validators=[
            Optional(),
            Length(max=200)
        ]
    )
    submit = SubmitField('Submit')


class MobileNumberUpdateRequestForm(FlaskForm):
    """Class for requesting mobile number update form (outside portal)."""
    old_phone_no = StringField(
        'Old Mobile Number',
        validators=[
            Optional(),
            Regexp(r'^\d{10}$', message='Invalid mobile number.')
        ]
    )
    new_phone_no = StringField(
        'New Mobile Number',
        validators=[
            Optional(),
            Regexp(r'^\d{10}$', message='Invalid mobile number.')
        ]
    )
    username_or_ip_address = StringField(
        'Username / IP Address',
        validators=[InputRequired()]
    )
    postal_code = StringField(
        'Pin Code',
        validators=[
            InputRequired(),
            Regexp(r'^[7]+\d{5}$', message='Invalid postal code.')
        ]
    )
    submit = SubmitField('Submit Request')


class EmailAddressUpdateRequestForm(FlaskForm):
    """Class for requesting email address update form (outside portal)."""
    email_address = StringField(
        'Email Address',
        validators=[
            InputRequired(),
            Email(message='Invalid email address.')
        ]
    )
    username_or_ip_address = StringField(
        'Username / IP Address',
        validators=[InputRequired()]
    )
    postal_code = StringField(
        'Pin Code',
        validators=[
            InputRequired(),
            Regexp(r'^[7]+\d{5}$', message='Invalid postal code.')
        ]
    )
    submit = SubmitField('Submit Request')


class UpdateGSTForm(FlaskForm):
    """Class for updating GST information form."""
    gst_no = StringField(
        'GST Number',
        validators=[
            InputRequired(),
            Regexp(r'^[A-Z0-9]{15}$', message='Invalid GSTIN.')
        ]
    )
    submit = SubmitField('Update GSTIN')


class UpdateAadhaarForm(FlaskForm):
    """Class for updating Aadhaar information form."""
    aadhaar = StringField(
        'Aadhaar',
        validators=[
            InputRequired(),
            Regexp(r'^[0-9]{12}$', message='Invalid Aadhaar.')
        ]
    )
    submit = SubmitField('Update Aadhaar')


class AddSoftphoneForm(FlaskForm):
    """Class for adding softphone number form."""
    name = StringField(
        'Name of User',
        validators=[InputRequired()],
    )
    mobile_number = StringField(
        'Mobile Number of User',
        validators=[
            Optional(),
            Regexp(r'^\d{10}$', message='Invalid mobile number.')
        ]
    )
    softphone_platform = SelectField(
        'Softphone Platform',
        validators=[InputRequired()],
        choices=[
            ('Android', 'Android'),
            ('iOS', 'iOS'),
            ('Fixed Line', 'Fixed Line')
        ]
    )
    password = PasswordField(
        'Password',
        validators=[
            InputRequired(),
            EqualTo('confirm_password', message='Passwords must match.'),
            Regexp(
                r'^[a-zA-Z0-9_\-]{1,8}$',
                message='Only alphabets, numbers, - and _ are allowed.'
            ),
            Length(max=8, message='Exceeding maximum length.')
        ],
        render_kw={'placeholder': 'Max. 8 characters'}
    )
    confirm_password = PasswordField(
        'Repeat Password',
        validators=[InputRequired()]
    )
    submit = SubmitField('Add Softphone')
